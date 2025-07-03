#!/usr/bin/env python
# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Union
import os
from utils.path_utils import get_config_path, load_config

class BaseDownloader(ABC):
    """数据下载器基类
    定义了数据下载的标准接口，所有具体的数据源下载器都应该继承这个类
    并实现其抽象方法
    """
    
    def __init__(
        self,
        config_path: str = None,
        provider: str = None,
        start_date: str = None,
        end_date: str = None,
        convert: bool = False,
        interval: str = '1d',
        stock_codes: list = None
    ):
        """初始化下载器
        
        Args:
            config_path: 配置文件路径，默认为None
            provider: 金融数据提供方名称，用于加载对应的配置
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
            convert: 是否转换为Qlib格式，默认为False
            interval: 数据间隔，支持1min、5min、15min、30min、1h、1d、1w、1m、1q、1y，默认1d表示日数据
            stock_codes: 要下载的股票代码列表，支持list、逗号分隔字符串、或文件路径
        """
        self.provider = provider
        self.start_date = start_date
        self.end_date = end_date
        self.convert = convert
        self.interval = interval
        self.stock_codes = self._parse_stock_codes(stock_codes)
        self.config = self._load_config(config_path, provider)

    @staticmethod
    def _load_config(config_path: Optional[str], provider: str) -> Dict[str, Any]:
        """加载配置文件，合并通用配置和数据源专属配置
        
        配置合并规则：
        1. 以通用配置为基础
        2. 数据源专属配置覆盖通用配置
        3. 如果专属配置未指定data_path，则使用通用配置的data_path/{market_provider}
        
        Args:
            config_path: 配置文件路径
            provider: 金融数据提供方
            
        Returns:
            Dict[str, Any]: 合并后的配置
        """
        if config_path is None:
            # 使用统一配置加载方法
            full_config = load_config('market_provider.yaml')
        else:
            # 如果提供了具体路径，使用path_utils的方法
            config_file = get_config_path(config_path)
            if not os.path.exists(config_file):
                raise FileNotFoundError(f"配置文件不存在: {config_file}")
            full_config = load_config(config_path)
            
        # 1. 获取通用配置
        common_config = full_config.get('common', {})
        
        # 2. 获取数据源专属配置
        provider_config = full_config.get(provider, {}).get('config', {})
        
        # 3. 合并配置（从下到上覆盖）
        config = common_config.copy()  # 以通用配置为基础
        config.update(provider_config)  # 专属配置覆盖通用配置

        # 4. 特殊处理data_path
        if not provider_config.get('data_path'):
            config['data_path'] = os.path.join(common_config.get('data_path', 'data/raw'), provider)
            
        return config

    @staticmethod
    def _parse_stock_codes(stock_codes):
        """
        解析股票代码参数，支持三种输入：
        - list: 直接返回
        - str: 可能是逗号分隔字符串，也可能是文件路径
        - None: 返回 None
        """
        if stock_codes is None:
            return None
        if isinstance(stock_codes, list):
            return stock_codes
        if isinstance(stock_codes, str):
            if os.path.isfile(stock_codes):
                codes = []
                with open(stock_codes, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        # 跳过空行和注释行
                        if not line or line.startswith('#'):
                            continue
                        codes.extend([c.strip() for c in line.split(',') if c.strip()])
                return codes
            else:
                return [c.strip() for c in stock_codes.split(',') if c.strip()]
        raise ValueError('stock_codes参数类型不支持，应为list、逗号分隔字符串或股票代码文件路径')

    @abstractmethod
    def batch_download(self) -> None:
        """批量下载股票数据
        将股票列表分块处理，每块并发下载，避免创建过多任务
        """
        pass

    def get_trade_dates(self, start_date: str, end_date: str) -> set:
        """
        获取指定区间的所有交易日（子类需实现具体逻辑）
        Args:
            start_date: 开始日期
            end_date: 结束日期
        Returns:
            set: 交易日集合（字符串格式YYYY-MM-DD）
        """
        raise NotImplementedError("请在子类中实现 get_trade_dates 方法")

    def incremental_update(self, df_local, target_set, get_local_set_fn, download_missing_fn, merge_fn, split_ranges_fn=None):
        """
        通用增量补齐逻辑：
        1. 计算本地已有集合
        2. 计算缺失集合
        3. 分段下载缺失数据
        4. 合并、去重、返回新数据
        Args:
            df_local: 本地DataFrame
            target_set: 目标集合（如所有交易日、所有年份等，set类型）
            get_local_set_fn: 从本地数据提取集合的函数，返回set
            download_missing_fn: 下载缺失区间的函数，参数为区间（如日期段、年份等），返回DataFrame
            merge_fn: 合并去重函数，参数为DataFrame列表，返回合并后的DataFrame
            split_ranges_fn: 可选，将缺失集合分为连续区间的函数，返回区间列表
        Returns:
            DataFrame: 合并后的新数据（如果没有缺失则返回本地数据，调用方应判断数据是否有变化再保存）
        """
        local_set = get_local_set_fn(df_local) if df_local is not None else set()
        missing = sorted(list(target_set - local_set))
        if not missing:
            return df_local
        # 分段
        if split_ranges_fn:
            ranges = split_ranges_fn(missing)
        else:
            ranges = [(v, v) for v in missing]
        dfs = []
        for rng in ranges:
            df = download_missing_fn(rng)
            if df is not None and not df.empty:
                dfs.append(df)
        if dfs:
            df_new = merge_fn([df_local] + dfs)
            return df_new
        else:
            return df_local