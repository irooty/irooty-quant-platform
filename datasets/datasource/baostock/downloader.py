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
        self.min_request_interval = 0.1  # 最小请求间隔（秒）
        self.NORMAL_FLAG = "NORMAL"  # 标记正常下载的股票
        # self.lock = threading.Lock() # 初始化一把锁，用于调用Baostock API，因为它不支持多线程
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

        # 优化：统一计算start_date、end_date
        self.start_date = self.start_date or self.config.get('start_date', '2010-01-01')
        self.end_date = self.end_date or self.config.get('end_date') or datetime.now().strftime('%Y-%m-%d')

        # 优化：一次性获取所有交易日
        self.trade_dates = self.get_trade_dates(self.start_date, self.end_date)
        # 优化：一次性计算所有年份集合
        self.all_years = set(str(y) for y in range(int(self.start_date[:4]), int(self.end_date[:4]) + 1))

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
        """发送请求，支持自动重试和频率限制
        使用指数退避算法进行重试，避免频繁重试对服务器造成压力
        """
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

    def _status_file(self):
        """返回元数据文件路径"""
        return os.path.join(self.config.get('data_path', '../data/raw/baostock'), 'download_status.json')

    def load_status(self):
        """加载下载元数据"""
        status_file = self._status_file()
        if os.path.exists(status_file):
            with open(status_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save_status(self, status):
        """保存下载元数据"""
        status_file = self._status_file()
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump(status, f, ensure_ascii=False, indent=2)

    def update_status(self, stock_code, data_type, status_info):
        """更新某只股票某类数据的下载状态"""
        status = self.load_status()
        if stock_code not in status:
            status[stock_code] = {}
        status[stock_code][data_type] = status_info
        self.save_status(status)

    def is_data_downloaded(self, stock_code, data_type):
        """判断某只股票某类数据是否已下载（done）"""
        status = self.load_status()
        return (
            stock_code in status and
            data_type in status[stock_code] and
            status[stock_code][data_type].get('status') == 'done'
        )

    def is_daily_data_up_to_date(self, stock_code, target_start=None, target_end=None):
        """判断某只股票的日线数据是否覆盖目标区间"""
        if target_start is None:
            target_start = self.start_date
        if target_end is None:
            target_end = self.end_date
        status = self.load_status()
        info = status.get(stock_code, {}).get('daily', {})
        if info.get('status') != 'done':
            return False
        # 判断区间是否覆盖
        return info.get('start_date') <= target_start and info.get('end_date') >= target_end

    def is_dividend_data_up_to_date(self, stock_code, target_years=None):
        """判断某只股票的分红数据是否覆盖目标年份"""
        if target_years is None:
            target_years = self.all_years
        status = self.load_status()
        info = status.get(stock_code, {}).get('dividend', {})
        if info.get('status') != 'done':
            return False
        # 如果确实无分红数据，认为已是最新
        if info.get('has_dividend') == False:
            return True
        # 有分红数据时，检查年份覆盖
        return set(info.get('years', [])) >= set(target_years)

    def batch_download(self) -> None:
        """
        批量下载股票数据，分两步：
        1. 只依赖download_status.json元数据判断哪些股票需要下载。
        2. 下载阶段进度条总数为所有股票数，只有在待下载列表里的股票才实际下载。
        """
        chunk_size = self.config.get('download', {}).get('chunk_size', 1000)
        total_stocks = len(self.stock_codes)
        logger.info(f'开始处理 {total_stocks} 支股票的数据...')

        status = self.load_status()
        use_status = bool(status)
        to_download = set()

        if use_status:
            # 检查阶段进度条
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
        """
        按批下载股票数据，进度条总数为本批次所有股票数，只有在待下载列表里的才实际下载。
        下载完成后及时更新元数据的区间信息。
        """
        skipped = 0
        for stock_code in tqdm(chunk, desc="下载进度", total=len(chunk)):
            if stock_code in to_download_set:
                # 下载日线数据
                daily_ok = self.download_daily_data(stock_code)
                if daily_ok is not None:
                    self.update_status(stock_code, 'daily', {
                        'status': 'done',
                        'start_date': self.start_date,
                        'end_date': self.end_date,
                        'last_update': datetime.now().strftime('%Y-%m-%d'),
                    })
                # 下载分红数据（元数据更新由download_dividend_data自己处理）
                dividend_ok = self.download_dividend_data(stock_code)
                if daily_ok is None or dividend_ok is None:
                    failed_stocks.append(stock_code)
            else:
                skipped += 1
                time.sleep(0.02)  # 微小延迟，让进度条有流动感
        logger.info(f"本批次跳过已最新股票数量: {skipped}")
        logger.info(f"下载失败的股票数量: {len(failed_stocks)}")
        return failed_stocks

    def get_trade_dates(self, start_date: str, end_date: str) -> set:
        """
        获取指定区间的所有交易日（YYYY-MM-DD字符串集合）
        """
        rs = self._make_request(
            self.bs.query_trade_dates,
            start_date=start_date,
            end_date=end_date
        )
        df = self._process_result(rs)
        if not df.empty:
            return set(df[df['is_trading_day'] == '1']['calendar_date'])
        return set()

    def download_daily_data(self, stock_code: str) -> pd.DataFrame:
        """下载单个股票的日线数据，按交易日增量补齐"""

        fields = self.config.get('fields', {}).get('daily')

        save_path = os.path.join(self.config.get('data_path', '../data/raw/baostock'), 'daily', stock_code)
        file_path = os.path.join(save_path, f'{stock_code}_daily.csv')
        metadata_path = f"{file_path}.meta"

        # 1. 获取目标区间的所有交易日（用缓存）
        trade_dates = self.trade_dates

        # 2. 读取本地数据
        if os.path.exists(file_path):
            df_local = pd.read_csv(file_path)
            if df_local.empty or 'date' not in df_local.columns:
                df_local = pd.DataFrame()
        else:
            df_local = pd.DataFrame()

        # 3. 定义辅助函数
        def get_local_dates(df):
            """ 提取已有数据中的交易日集合（格式化为 YYYY-MM-DD）"""
            if df is None or df.empty or 'date' not in df.columns:
                return set()
            return set(pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d'))

        def split_into_ranges(dates):
            """ 将缺失交易日划分为连续区间段（例如：[(2024-01-01, 2024-01-03), (2024-01-05, 2024-01-05)]） """
            if not dates:
                return []
            from datetime import datetime, timedelta
            dates = [datetime.strptime(d, '%Y-%m-%d') for d in dates]
            dates.sort()
            ranges = []
            start = dates[0]
            end = dates[0]
            for d in dates[1:]:
                if (d - end).days == 1:
                    end = d
                else:
                    ranges.append((start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')))
                    start = end = d
            ranges.append((start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')))
            return ranges

        def download_missing(rng):
            """从 Baostock 下载指定区间的数据"""
            rs = self._make_request(
                self.bs.query_history_k_data_plus,
                code=stock_code,
                fields=fields,
                start_date=rng[0],
                end_date=rng[1],
                frequency='d',
                adjustflag='3'
            )
            return self._process_result(rs)

        def merge_dfs(dfs):
            """合并多个 DataFrame，按日期去重、排序"""
            df_new = pd.concat([df for df in dfs if df is not None and not df.empty], ignore_index=True)
            if 'date' in df_new.columns:
                df_new['date'] = pd.to_datetime(df_new['date']).dt.strftime('%Y-%m-%d')
                df_new = df_new.drop_duplicates(subset=['date']).sort_values('date')
            else:
                df_new = df_new.drop_duplicates().sort_index()
            return df_new

        # 4. 增量补齐
        df_new = self.incremental_update(
            df_local,
            trade_dates,
            get_local_dates,
            download_missing,
            merge_dfs,
            split_ranges_fn=split_into_ranges
        )

        # 5. 保存数据并更新元数据
        if not df_new.empty:
            os.makedirs(save_path, exist_ok=True)
            metadata = {
                'stock_code': stock_code,
                'start_date': self.start_date,
                'end_date': self.end_date,
                'download_date': datetime.now().isoformat(),
                'record_count': len(df_new),
                'fields': list(df_new.columns)
            }
            self._save_with_metadata(df_new, file_path, metadata)
            return df_new
        else:
            return df_local

    def download_dividend_data(self, stock_code: str) -> pd.DataFrame:
        """下载分红数据，按年份增量补齐"""

        fields = self.config.get('fields', {}).get('dividend')

        save_path = os.path.join(self.config.get('data_path', '../data/raw/baostock'), 'dividend', stock_code)
        file_path = os.path.join(save_path, f'{stock_code}_dividend.csv')
        metadata_path = f"{file_path}.meta"

        # 1. 计算目标年份集合（用缓存）
        all_years = self.all_years

        # 2. 读取本地数据
        if os.path.exists(file_path):
            df_local = pd.read_csv(file_path)
            if df_local.empty:
                df_local = pd.DataFrame()
        else:
            df_local = pd.DataFrame()

        # 3. 定义辅助函数
        def get_local_years(df):
            if df is None or df.empty:
                return set()
            if 'year' in df.columns:
                return set(df['year'].astype(str))
            elif 'dividend_year' in df.columns:
                return set(df['dividend_year'].astype(str))
            elif 'report_date' in df.columns:
                return set(df['report_date'].astype(str).str[:4])
            else:
                return set()

        def download_missing_year(rng):
            year = rng[0]
            rs = self._make_request(
                self.bs.query_dividend_data,
                code=stock_code,
                year=year,
                yearType='report'
            )
            return self._process_result(rs)

        def merge_dfs(dfs):
            df_new = pd.concat([df for df in dfs if df is not None and not df.empty], ignore_index=True)
            if 'dividend_year' in df_new.columns:
                df_new['year'] = df_new['dividend_year']
            elif 'year' not in df_new.columns and 'report_date' in df_new.columns:
                df_new['year'] = df_new['report_date'].astype(str).str[:4]
            df_new = df_new.drop_duplicates().sort_values('year')
            return df_new

        # 4. 增量补齐
        df_new = self.incremental_update(
            df_local,
            all_years,
            get_local_years,
            download_missing_year,
            merge_dfs
        )

        # 5. 保存数据并更新元数据
        if not df_new.empty:
            os.makedirs(save_path, exist_ok=True)
            metadata = {
                'stock_code': stock_code,
                'start_date': self.start_date,
                'end_date': self.end_date,
                'download_date': datetime.now().isoformat(),
                'record_count': len(df_new),
                'fields': list(df_new.columns)
            }
            self._save_with_metadata(df_new, file_path, metadata)
            # 有分红数据
            self.update_status(stock_code, 'dividend', {
                'status': 'done',
                'years': list(self.all_years),
                'has_dividend': True,
                'last_update': datetime.now().strftime('%Y-%m-%d'),
            })
            return df_new
        else:
            # 无分红数据
            self.update_status(stock_code, 'dividend', {
                'status': 'done',
                'years': list(self.all_years),
                'has_dividend': False,
                'last_update': datetime.now().strftime('%Y-%m-%d'),
            })
            return df_local