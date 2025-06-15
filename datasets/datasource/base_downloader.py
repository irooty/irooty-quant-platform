#!/usr/bin/env python
# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Union
import os
import yaml
from utils.path_utils import get_config_path

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
            stock_codes: 要下载的股票代码列表，默认为None
        """
        self.provider = provider
        self.start_date = start_date
        self.end_date = end_date
        self.convert = convert
        self.interval = interval
        self.stock_codes = stock_codes
        self.config = self._load_config(config_path, provider)

    def _load_config(self, config_path: Optional[str], provider: str) -> Dict[str, Any]:
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
            config_path = get_config_path('market_provider.yaml')

        if not os.path.exists(config_path):
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        # 读取配置文件
        with open(config_path, 'r', encoding='utf-8') as f:
            full_config = yaml.safe_load(f)
            
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
    

    @abstractmethod
    def batch_download(self) -> None:
        """批量下载股票数据
        将股票列表分块处理，每块并发下载，避免创建过多任务
        """
        pass