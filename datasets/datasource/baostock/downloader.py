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

    @staticmethod
    def _process_result(rs):
        """处理查询结果"""
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())
        if data_list:
            df = pd.DataFrame(data_list, columns=rs.fields)
        else:
            df = pd.DataFrame()
        return df

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

    def get_trade_dates(self, start_date: str, end_date: str) -> set:
        """
        获取指定区间的所有交易日（子类需实现具体逻辑）
        Args:
            start_date: 开始日期
            end_date: 结束日期
        Returns:
            set: 交易日集合（字符串格式YYYY-MM-DD）
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
            # 确保year列存在
            if 'dividend_year' in df_new.columns:
                df_new['year'] = df_new['dividend_year']
            elif 'year' not in df_new.columns and 'report_date' in df_new.columns:
                df_new['year'] = df_new['report_date'].astype(str).str[:4]

            # 安全排序：如果year列存在则按year排序，否则按索引排序
            if 'year' in df_new.columns:
                df_new = df_new.drop_duplicates().sort_values('year')
            else:
                df_new = df_new.drop_duplicates().sort_index()
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