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

class DownloadDispatcher:
    """
    DownloadDispatcher 负责 interval 类型到具体下载方法的注册与分发。

    用法示例：
        # 在子类文件顶部定义 register 别名
        register = BaseDownloader.download_dispatcher.register

        # 在子类中用装饰器注册方法
        @register('1d')
        def download_daily_data(self, stock_code):
            ...

    主流程调用：
        self.download_dispatcher.download(self, stock_code, interval)
    """
    def __init__(self):
        self.download_methods = {}
    def register(self, interval):
        def decorator(func):
            self.download_methods[interval] = func.__name__
            return func
        return decorator
    def download(self, instance, stock_code, interval, *args, **kwargs):
        method_name = self.download_methods.get(interval)
        if method_name is None:
            msg = (
                f"未找到 interval '{interval}' 的下载方法。\n"
                f"请在你的Downloader子类中实现并用@register('{interval}')装饰器注册，如：\n"
                f"    @register('{interval}')\n    def download_{interval}_data(self, stock_code): ..."
            )
            logger.warning(msg)
            raise NotImplementedError(msg)
        method = getattr(instance, method_name)
        return method(stock_code, *args, **kwargs)

class CompletenessChecker:
    """
    CompletenessChecker 负责 interval/data_type 到完整性检查方法的注册与分发。

    用法示例：
        # 在子类文件顶部定义 checker_register 别名
        checker_register = BaseDownloader.completeness_checker.register

        # 在子类中用装饰器注册方法
        @checker_register('1d')
        def check_1d_complete(self, stock_code, **kwargs):
            ...

    主流程调用：
        self.completeness_checker.is_complete(self, stock_code, data_type, **kwargs)
    """
    def __init__(self):
        self.checkers = {}
    def register(self, data_type):
        def decorator(func):
            self.checkers[data_type] = func.__name__
            return func
        return decorator
    def is_complete(self, instance, stock_code, data_type, **kwargs):
        method_name = self.checkers.get(data_type)
        if method_name is not None:
            method = getattr(instance, method_name)
            return method(stock_code, **kwargs)
        msg = (
            f"未找到数据类型 '{data_type}' 的完整性检查方法。\n"
            f"请在你的Downloader子类中实现并用@checker_register('{data_type}')装饰器注册，如：\n"
            f"    @checker_register('{data_type}')\n    def check_{data_type}_complete(self, stock_code, **kwargs): ..."
        )
        logger.warning(msg)
        raise NotImplementedError(msg)

class StepTimer:
    def __init__(self, enable=False, prefix=""):
        self.enable = enable
        self.prefix = prefix
        self.last = time.time()
    def step(self, name):
        if not self.enable:
            return
        now = time.time()
        print(f"[TIMER] {self.prefix}{name} 耗时: {now - self.last:.3f} 秒")
        self.last = now

class BaseDownloader(ABC):
    download_dispatcher = DownloadDispatcher()  # 类属性，供装饰器注册
    completeness_checker = CompletenessChecker()  # 类属性，供装饰器注册

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
        # 新增：从配置文件读取计时开关
        self.enable_timing = self.config.get('download', {}).get('enable_timing', False)

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

    def incremental_download(
        self,
        stock_code,
        target_set,
        get_local_set_fn,
        download_missing_fn,
        merge_fn,
        save_path,
        file_path,
        metadata_fn,
        status_type=None
    ):
        """
        通用的增量下载流程，适用于日线、分红、分钟线等多种类型。
        只发起一次API请求，直接请求缺失区间的最小值到最大值。
        """
        timer = StepTimer(enable=getattr(self, 'enable_timing', False), prefix="incremental_download: ")
        # 1. 读取本地数据
        if os.path.exists(file_path):
            df_local = pd.read_csv(file_path)
            if df_local.empty:
                df_local = pd.DataFrame()
        else:
            df_local = pd.DataFrame()
        timer.step("读取本地数据")

        # 2. 计算本地已有集合
        local_set = get_local_set_fn(df_local) if df_local is not None else set()
        timer.step("计算本地已有集合")
        missing = sorted(list(target_set - local_set))
        timer.step("计算缺失")
        if not missing:
            return df_local

        # 3. 整块下载
        start_date, end_date = min(missing), max(missing)
        # print(f"[TIMER] incremental_download: 整块下载区间: ({start_date}, {end_date})")
        df = download_missing_fn((start_date, end_date))
        timer.step("下载缺失数据")

        # 4. 合并去重
        if df is not None and not df.empty:
            df_new = merge_fn([df_local, df])
        else:
            df_new = df_local
        timer.step("合并去重")

        # 5. 保存数据和元数据
        if not df_new.empty:
            os.makedirs(save_path, exist_ok=True)
            metadata = metadata_fn(df_new)
            self._save_with_metadata(df_new, file_path, metadata)
            # 6. 更新状态
            if status_type:
                self.update_status(stock_code, status_type, {
                    'status': 'done',
                    'start_date': getattr(self, 'start_date', None),
                    'end_date': getattr(self, 'end_date', None),
                    'last_update': datetime.now().strftime('%Y-%m-%d'),
                })
            timer.step("保存数据和元数据")
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

    def is_data_complete(self, stock_code, data_type, **kwargs):
        return self.completeness_checker.is_complete(self, stock_code, data_type, **kwargs)

    def batch_download(self) -> None:
        from tqdm import tqdm
        import time
        chunk_size = self.config.get('download', {}).get('chunk_size', 1000)
        total_stocks = len(self.stock_codes)
        logger.info(f'开始处理 {total_stocks} 支股票的数据...')

        status = self.load_status()
        use_status = bool(status)
        to_download = set()
        interval = self.interval

        # 只判断当前 interval 类型的数据是否需要下载
        for stock_code in tqdm(self.stock_codes, desc="检查进度", total=total_stocks):
            if not self.is_data_complete(stock_code, interval):
                to_download.add(stock_code)

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
        interval = self.interval
        for stock_code in tqdm(chunk, desc="下载进度", total=len(chunk)):
            if stock_code in to_download_set:
                try:
                    self.download_dispatcher.download(self, stock_code, interval)
                except NotImplementedError as e:
                    logger.warning(str(e))
                    failed_stocks.append(stock_code)
            else:
                skipped += 1
                time.sleep(0.02) # 避免时间太短不更新进度条
        logger.info(f"本批次跳过已最新股票数量: {skipped}")
        logger.info(f"下载失败的股票数量: {len(failed_stocks)}")
        return failed_stocks

    @staticmethod
    def verify_completeness(file_path, target_set, get_local_set_fn, desc=""):
        import os
        if not os.path.exists(file_path):
            logger.warning(f"{desc}文件不存在: {file_path}")
            return []
        df = pd.read_csv(file_path)
        local_set = get_local_set_fn(df)
        missing = sorted(list(target_set - local_set))
        if missing:
            logger.warning(f"{desc}缺失{len(missing)}项: {missing[:10]} ...")
        else:
            logger.info(f"{desc}完整性校验通过，无缺失。")
        return missing