import os
import threading

import baostock as bs
import pandas as pd
from datetime import datetime, timedelta
from loguru import logger
import time
import json
import hashlib  # 用于计算文件哈希值
import backoff  # 用于实现指数退避重试机制
from joblib import Parallel, delayed
from tqdm import tqdm

from typing import List, Dict, Optional, Any
from ..base_downloader import BaseDownloader

class BaostockDownloader(BaseDownloader):
    """Baostock数据下载器
    实现了异步并发下载、请求控制、数据完整性校验等功能
    """

    def __init__(
        self,
        config_path: str = None,
        provider: str = 'baostock',
        start_date: str = None,
        end_date: str = None,
        convert: bool = False,
        interval: str = '1d',
        stock_codes: list = None
    ):
        """初始化下载器

        Args:
            config_path: 配置文件路径，默认为None
            provider: 金融数据提供方名称，用于加载对应的配置，默认为'baostock'
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
            convert: 是否转换为Qlib格式，默认为False
            interval: 数据间隔，支持1min、5min、15min、30min、1h、1d、1w、1m、1q、1y，默认1d表示日数据
            stock_codes: 要下载的股票代码列表，默认为None
        """
        self.bs = bs
        self.last_request_time = 0  # 初始化最后请求时间
        self.min_request_interval = 0.5  # 最小请求间隔（秒）
        self.NORMAL_FLAG = "NORMAL"  # 标记正常下载的股票
        self.lock = threading.Lock() # 初始化一把锁，用于调用Baostock API，因为它不支持多线程
        super().__init__(
            config_path=config_path,
            provider=provider,
            start_date=start_date,
            end_date=end_date,
            convert=convert,
            interval=interval,
            stock_codes=stock_codes
        )
        # 登录系统
        self.login()
        # 初始化股票池列表
        if self.stock_codes is None:
            stock_df = self.download_stock_list()
            self.stock_codes = stock_df['code'].tolist()

    def login(self) -> None:
        """登录系统，支持自动重试
        使用指数退避算法进行重试，避免频繁重试对服务器造成压力
        """
        lg = self.bs.login()
        if lg.error_code != '0':
            logger.error(f'登录失败: {lg.error_msg}')
            raise Exception(f'Baostock登录失败: {lg.error_msg}')
        logger.info('Baostock登录成功')

    def logout(self) -> None:
        """登出系统"""
        self.bs.logout()
        logger.info('Baostock登出成功')

    def _wait_for_rate_limit(self):
        """等待请求频率限制
        确保两次请求之间至少间隔min_request_interval秒
        避免触发服务器限流
        """
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last_request)
        self.last_request_time = time.time()

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def _make_request(self, func, *args, **kwargs):
        """
        封装 Baostock 所有 API 的原子调用（加锁 + 节流 + 重试）

        Args:
            func: baostock API 函数，如 self.bs.query_stock_basic
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            返回 baostock 的原始结果对象（可继续 .next() / .get_row_data()）
        """
        with self.lock:
            self._wait_for_rate_limit()
            return func(*args, **kwargs)

    def _process_result(self, rs):
        """处理查询结果"""
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())
        if data_list:
            df = pd.DataFrame(data_list, columns=rs.fields)
        else:
            df = pd.DataFrame()
        return df
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件哈希值用于校验
        使用MD5算法计算文件哈希，用于验证数据完整性
        """
        if not os.path.exists(file_path):
            return ""
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()

    def _save_with_metadata(self, df: pd.DataFrame, file_path: str, metadata: Dict):
        """保存数据并记录元数据
        同时保存数据和元数据，元数据包含：
        - 文件哈希值
        - 最后更新时间
        - 记录数
        - 字段列表
        用于后续数据验证和增量更新
        """
        # 保存数据
        df.to_csv(file_path, index=False, encoding='utf-8')

        # 保存元数据
        metadata_path = f"{file_path}.meta"
        metadata['file_hash'] = self._calculate_file_hash(file_path)
        metadata['last_update'] = datetime.now().isoformat()

        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    def download_stock_list(self) -> pd.DataFrame:
        """下载股票池列表
        获取所有股票的基本信息
        """
        logger.info('开始下载股票池列表...')
        stock_rs = self._make_request(self.bs.query_stock_basic)
        stock_df = self._process_result(stock_rs)
        logger.info(f'下载股票列表{len(stock_df)}支')

        if not stock_df.empty:
            save_path = os.path.join(self.config['data_path'], 'stock_list')
            os.makedirs(save_path, exist_ok=True)
            file_path = os.path.join(save_path, f'stock_list_{datetime.now().strftime("%Y%m%d")}.csv')

            # 保存元数据
            metadata = {
                'download_date': datetime.now().isoformat(),
                'record_count': len(stock_df),
                'fields': list(stock_df.columns)
            }

            self._save_with_metadata(stock_df, file_path, metadata)
            logger.info(f'股票列表已保存至: {file_path}')

        return stock_df

    def batch_download(self) -> None:
        """批量下载股票数据
                将股票列表分块处理，每块并发下载，避免创建过多任务
        """
        # 将股票列表分成多个批次
        chunk_size = self.config.get('download', {}).get('chunk_size', 1000)
        stock_chunks = [self.stock_codes[i:i + chunk_size] for i in range(0, len(self.stock_codes), chunk_size)]
        total_stocks = len(self.stock_codes)
        logger.info(f'开始下载 {total_stocks} 支股票的日线数据，分 {len(stock_chunks)} 批处理')

        failed_stocks = []  # 记录下载失败的股票代码

        for chunk_idx, chunk in enumerate(stock_chunks, 1):
            logger.info(f"批次 {chunk_idx}/{len(stock_chunks)}")
            self._download_stock_data(chunk, failed_stocks)

        if failed_stocks:
            logger.info(f"下载失败的股票列表: {failed_stocks}")
        else:
            logger.info("所有股票下载成功")

    def _download_stock_data(self, chunk, failed_stocks):
        """
        按批下载股票数据
        :param chunk: 股票列表
        :param failed_stocks: 失败列表
        :return:
        """
        def _download_single_stock(stock_code):
            try:
                self.download_daily_data(stock_code)
                self.download_dividend_data(stock_code)
                return self.NORMAL_FLAG
            except Exception as e:
                logger.error(f"下载 {stock_code} 失败: {e}")
                return stock_code

        # 使用进程池进行并发下载，每个进程都会有自己的登录状态
        # 添加prefer="threads"为线程并发，线程间共享内存空间；不加参数默认则是进程并发，不共享内存
        res = Parallel(n_jobs=self.config.get('download', {}).get('max_workers', 4), prefer="threads")(
            delayed(_download_single_stock)(_stock) for _stock in tqdm(chunk)
        )

        # 使用单线程顺序下载
        # for stock_code in tqdm(chunk):
        #     result = _download_single_stock(stock_code)
        #     if result != self.NORMAL_FLAG:
        #         failed_stocks.append(stock_code)

        logger.info(f"下载失败的股票数量: {len(failed_stocks)}")
        logger.info(f"当前批次股票数量: {len(chunk)}")
        return failed_stocks

    def download_daily_data(self, stock_code: str) -> pd.DataFrame:
        """下载单个股票的日线数据
        实现了增量更新机制：
        1. 检查本地文件是否存在
        2. 检查元数据中的最后更新时间
        3. 如果数据在24小时内更新过，直接返回本地数据
        4. 否则重新下载
        """
        start_date = self.start_date or self.config.get('start_date', '2010-01-01')
        end_date = self.end_date or self.config.get('end_date') or datetime.now().strftime('%Y-%m-%d')
        fields = self.config.get('fields', {}).get('daily')

        # logger.info(f'下载 {stock_code} 的日线数据 ({start_date} to {end_date})')

        # 检查是否需要增量更新
        save_path = os.path.join(self.config.get('data_path', '../data/raw/baostock'), 'daily', stock_code)
        file_path = os.path.join(save_path, f'{stock_code}_daily.csv')
        metadata_path = f"{file_path}.meta"

        if os.path.exists(file_path) and os.path.exists(metadata_path):
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                last_update = datetime.fromisoformat(metadata['last_update'])
                if (datetime.now() - last_update).days < 1:  # 如果数据在24小时内更新过
                    logger.info(f'{stock_code} 日线数据已是最新')
                    return pd.read_csv(file_path)

        rs = self._make_request(
            self.bs.query_history_k_data_plus,
            code=stock_code,
            fields=fields,
            start_date=start_date,
            end_date=end_date,
            frequency='d',
            adjustflag='3'
        )

        df = self._process_result(rs)
        if not df.empty:
            os.makedirs(save_path, exist_ok=True)

            # 保存元数据
            metadata = {
                'stock_code': stock_code,
                'start_date': start_date,
                'end_date': end_date,
                'download_date': datetime.now().isoformat(),
                'record_count': len(df),
                'fields': list(df.columns)
            }

            self._save_with_metadata(df, file_path, metadata)
            # logger.info(f'日线数据已保存至: {file_path}')

        return df

    def download_dividend_data(self, stock_code: str) -> pd.DataFrame:
        """下载分红数据

        Args:
            stock_code: 股票代码

        Returns:
            pd.DataFrame: 分红数据
        """
        start_date = self.start_date or self.config.get('start_date', '2010-01-01')
        end_date = self.end_date or self.config.get('end_date') or datetime.now().strftime('%Y-%m-%d')
        fields = self.config.get('fields', {}).get('dividend')

        # logger.info(f'下载 {stock_code} 的分红数据 ({start_date} to {end_date})')

        # 检查是否需要增量更新
        save_path = os.path.join(self.config.get('data_path', '../data/raw/baostock'), 'dividend', stock_code)
        file_path = os.path.join(save_path, f'{stock_code}_dividend.csv')
        metadata_path = f"{file_path}.meta"

        if os.path.exists(file_path) and os.path.exists(metadata_path):
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                last_update = datetime.fromisoformat(metadata['last_update'])
                if (datetime.now() - last_update).days < 1:  # 如果数据在24小时内更新过
                    logger.info(f'{stock_code} 分红数据已是最新')
                    return pd.read_csv(file_path)

        rs = self._make_request(
            self.bs.query_dividend_data,
            code=stock_code,
            year=start_date.split('-')[0],
            yearType='report'
        )

        df = self._process_result(rs)
        if not df.empty:
            os.makedirs(save_path, exist_ok=True)

            # 保存元数据
            metadata = {
                'stock_code': stock_code,
                'start_date': start_date,
                'end_date': end_date,
                'download_date': datetime.now().isoformat(),
                'record_count': len(df),
                'fields': list(df.columns)
            }

            self._save_with_metadata(df, file_path, metadata)
            # logger.info(f'分红数据已保存至: {file_path}')

        return df