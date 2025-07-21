#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BaseDownloader: 通用数据下载器基类
- 统一参数管理
- 配置加载
- 股票池管理
- 请求频率控制与重试
- 文件哈希与元数据
- 状态管理（断点续传）
- 通用DataFrame保存/加载
子类只需实现具体数据源的API调用逻辑。
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Union
import os
import json
import hashlib
import pandas as pd
import time
from datetime import datetime
import backoff
from utils.path_utils import get_config_path, load_config
from utils.logger import setup_logger
logger = setup_logger("base_downloader")

class BaseDownloader(ABC):
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
        """
        初始化通用参数，加载配置
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
        # 请求频率控制
        self.last_request_time = 0  # 初始化最后请求时间
        self.min_request_interval = self.config.get('download', {}).get('min_request_interval', 0.5)  # 最小请求间隔（秒），可在子类覆盖

        # 优化：统一计算start_date、end_date
        self.start_date = self.start_date or self.config.get('start_date', '2010-01-01')
        self.end_date = self.end_date or self.config.get('end_date') or datetime.now().strftime('%Y-%m-%d')

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

    def _wait_for_rate_limit(self):
        """
        控制请求频率，避免被限流
        """
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last_request)
        self.last_request_time = time.time()

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def _make_request(self, func, *args, **kwargs):
        """
        封装重试和频率控制的请求调用
        """
        self._wait_for_rate_limit()
        return func(*args, **kwargs)

    # ================= 文件哈希与元数据 =================
    @staticmethod
    def _calculate_file_hash(file_path: str) -> str:
        """
        计算文件哈希值（MD5），用于数据完整性校验
        """
        if not os.path.exists(file_path):
            return ""
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()

    def _save_with_metadata(self, df: pd.DataFrame, file_path: str, metadata: Dict):
        """
            保存数据文件及其元数据（如哈希、更新时间、字段等）
        """
        df.to_csv(file_path, index=False, encoding='utf-8')
        metadata_path = f"{file_path}.meta"
        metadata['file_hash'] = self._calculate_file_hash(file_path)
        metadata['last_update'] = datetime.now().isoformat()
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    # ================= 通用DataFrame操作 =================
    @staticmethod
    def save_dataframe(df, file_path):
        """
        保存DataFrame为csv
        """
        df.to_csv(file_path, index=False, encoding='utf-8')

    @staticmethod
    def load_dataframe(file_path):
        """
        加载csv为DataFrame
        """
        if os.path.exists(file_path):
            return pd.read_csv(file_path)
        return pd.DataFrame()

    @staticmethod
    def incremental_update(df_local, target_set, get_local_set_fn, download_missing_fn, merge_fn, split_ranges_fn=None):
        import time
        # 1. 计算本地已有集合
        t0 = time.time()
        local_set = get_local_set_fn(df_local) if df_local is not None else set()
        t1 = time.time()
        logger.info(f"[incremental_update] get_local_set_fn耗时: {t1 - t0:.3f}秒")

        # 2. 计算缺失集合
        missing = sorted(list(target_set - local_set))
        if not missing:
            return df_local

        # 3. 分段
        if split_ranges_fn:
            t2 = time.time()
            ranges = split_ranges_fn(missing)
            t3 = time.time()
            logger.info(f"[incremental_update] split_ranges_fn耗时: {t3 - t2:.3f}秒")
        else:
            ranges = [(v, v) for v in missing]

        # 4. 下载缺失数据
        dfs = []
        for rng in ranges:
            t4 = time.time()
            df = download_missing_fn(rng)
            t5 = time.time()
            logger.info(f"[incremental_update] download_missing_fn({rng})耗时: {t5 - t4:.3f}秒")
            if df is not None and not df.empty:
                dfs.append(df)

        # 5. 合并去重
        if dfs:
            t6 = time.time()
            df_new = merge_fn([df_local] + dfs)
            t7 = time.time()
            logger.info(f"[incremental_update] merge_fn耗时: {t7 - t6:.3f}秒")
            return df_new
        else:
            return df_local

    def _status_file(self):
        return os.path.join(self.config.get('data_path', f'../data/raw/{self.provider}'), 'download_status.json')

    def load_status(self):
        status_file = self._status_file()
        if os.path.exists(status_file):
            with open(status_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save_status(self, status):
        status_file = self._status_file()
        os.makedirs(os.path.dirname(status_file), exist_ok=True)
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump(status, f, ensure_ascii=False, indent=2)

    def update_status(self, stock_code, data_type, status_info):
        status = self.load_status()
        if stock_code not in status:
            status[stock_code] = {}
        status[stock_code][data_type] = status_info
        self.save_status(status)

    def is_data_downloaded(self, stock_code, data_type):
        status = self.load_status()
        return (
            stock_code in status and
            data_type in status[stock_code] and
            status[stock_code][data_type].get('status') == 'done'
        )

    def is_daily_data_up_to_date(self, stock_code, target_start=None, target_end=None):
        if target_start is None:
            target_start = self.start_date
        if target_end is None:
            target_end = self.end_date
        status = self.load_status()
        info = status.get(stock_code, {}).get('daily', {})
        if info.get('status') != 'done':
            return False
        return info.get('start_date') <= target_start and info.get('end_date') >= target_end

    def is_dividend_data_up_to_date(self, stock_code, target_years=None):
        if target_years is None:
            target_years = self.all_years
        status = self.load_status()
        info = status.get(stock_code, {}).get('dividend', {})
        if info.get('status') != 'done':
            return False
        if info.get('has_dividend') == False:
            return True
        return set(info.get('years', [])) >= set(target_years)

    def batch_download(self) -> None:
        from tqdm import tqdm
        import time
        chunk_size = self.config.get('download', {}).get('chunk_size', 1000)
        total_stocks = len(self.stock_codes)
        logger.info(f'开始处理 {total_stocks} 支股票的数据...')

        status = self.load_status()
        use_status = bool(status)
        to_download = set()

        if use_status:
            for stock_code in tqdm(self.stock_codes, desc="检查进度", total=total_stocks):
                need_download = False
                if not self.is_daily_data_up_to_date(stock_code):
                    need_download = True
                if not self.is_dividend_data_up_to_date(stock_code):
                    need_download = True
                if need_download:
                    to_download.add(stock_code)
        else:
            to_download = set(self.stock_codes)

        if not to_download:
            logger.info("所有股票数据均为最新，无需下载。")
            return
        failed_stocks = []
        num_batches = (total_stocks + chunk_size - 1) // chunk_size
        for batch_idx, i in enumerate(range(0, total_stocks, chunk_size), 1):
            chunk = self.stock_codes[i:i + chunk_size]
            logger.info(f"正在处理第{batch_idx}批/共{num_batches}批，每批{len(chunk)}只股票")
            self._download_stock_data(chunk, failed_stocks, to_download)
        if failed_stocks:
            logger.info(f"下载失败的股票列表: {failed_stocks}")
        else:
            logger.info("所有股票下载成功")

    def _download_stock_data(self, chunk, failed_stocks, to_download_set):
        from tqdm import tqdm
        import time
        skipped = 0
        for stock_code in tqdm(chunk, desc="下载进度", total=len(chunk)):
            if stock_code in to_download_set:
                daily_ok = self.download_daily_data(stock_code)
                if daily_ok is not None:
                    self.update_status(stock_code, 'daily', {
                        'status': 'done',
                        'start_date': self.start_date,
                        'end_date': self.end_date,
                        'last_update': datetime.now().strftime('%Y-%m-%d'),
                    })
                dividend_ok = self.download_dividend_data(stock_code)
                if daily_ok is None or dividend_ok is None:
                    failed_stocks.append(stock_code)
            else:
                skipped += 1
                time.sleep(0.02) # 避免时间太短不更新进度条
        logger.info(f"本批次跳过已最新股票数量: {skipped}")
        logger.info(f"下载失败的股票数量: {len(failed_stocks)}")
        return failed_stocks