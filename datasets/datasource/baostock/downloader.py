#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import baostock as bs
import pandas as pd
from datetime import datetime, timedelta
from loguru import logger
import yaml
from utils.path_utils import get_config_path
# 异步支持库
import asyncio  # 用于实现异步并发
import time
import backoff  # 用于实现指数退避重试机制
import hashlib  # 用于计算文件哈希值
import json
from typing import List, Dict, Optional, Any
from ..base_downloader import BaseDownloader
from tqdm import tqdm  # 添加tqdm导入

class BaostockDownloader(BaseDownloader):
    """Baostock数据下载器
    实现了异步并发下载、请求控制、数据完整性校验等功能
    """
    def __init__(self, config_path=None):
        """初始化下载器
        
        Args:
            config_path: 配置文件路径，默认为None
        """
        self.bs = bs
        self.last_request_time = 0  # 初始化最后请求时间
        self.min_request_interval = 0.5  # 最小请求间隔（秒）
        super().__init__(config_path)
        # 登录系统
        self.login()
        
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """加载配置文件，合并通用配置和Baostock专属配置
        
        配置合并规则：
        1. 以通用配置为基础
        2. Baostock专属配置覆盖通用配置
        3. 如果专属配置未指定data_path，则使用通用配置的data_path/baostock
        """
        if config_path is None:
            config_path = get_config_path('data_source.yaml')

        if not os.path.exists(config_path):
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        # 读取配置文件
        with open(config_path, 'r', encoding='utf-8') as f:
            full_config = yaml.safe_load(f)
            
        # 1. 获取通用配置
        common_config = full_config.get('common', {})
        
        # 2. 获取Baostock专属配置
        baostock_config = full_config.get('baostock', {}).get('config', {})
        
        # 3. 合并配置（从下到上覆盖）
        config = common_config.copy()  # 以通用配置为基础
        config.update(baostock_config)  # 专属配置覆盖通用配置
        
        # 4. 特殊处理data_path
        if not baostock_config.get('data_path'):
            config['data_path'] = os.path.join(common_config.get('data_path', 'data/raw'), 'baostock')
            
        return config

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
        """下载股票列表
        获取所有股票的基本信息
        """
        logger.info('开始下载股票列表...')
        stock_rs = self._make_request(self.bs.query_stock_basic)
        stock_df = self._process_result(stock_rs)
        
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

    def download_daily_data(self, stock_code: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        """下载单个股票的日线数据
        实现了增量更新机制：
        1. 检查本地文件是否存在
        2. 检查元数据中的最后更新时间
        3. 如果数据在24小时内更新过，直接返回本地数据
        4. 否则重新下载
        """
        start_date = start_date or self.config.get('start_date', '2010-01-01')
        end_date = end_date or self.config.get('end_date') or datetime.now().strftime('%Y-%m-%d')
        fields = self.config.get('fields', {}).get('daily')
        
        logger.info(f'下载 {stock_code} 的日线数据 ({start_date} to {end_date})')
        
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
            logger.info(f'日线数据已保存至: {file_path}')
            
        return df

    async def _download_stock_data(self, stock_code: str, start_date: Optional[str] = None, end_date: Optional[str] = None):
        """异步下载单个股票的数据
        使用async/await语法实现非阻塞IO，提高并发性能
        """
        try:
            daily_df = self.download_daily_data(stock_code, start_date, end_date)
            dividend_df = self.download_dividend_data(stock_code, start_date, end_date)
            return stock_code, daily_df, dividend_df
        except Exception as e:
            logger.error(f'处理 {stock_code} 时出错: {str(e)}')
            return stock_code, None, None

    async def batch_download_daily_data(self, stock_codes: Optional[List[str]] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> None:
        """异步批量下载日线数据
        将股票列表分块处理，每块并发下载，避免创建过多任务
        
        Args:
            stock_codes: 股票代码列表，如果为None则下载所有股票
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
        """
        if stock_codes is None:
            stock_df = self.download_stock_list()
            stock_codes = stock_df['code'].tolist()

        # 将股票列表分成多个批次
        chunk_size = self.config.get('download', {}).get('chunk_size', 1000)
        stock_chunks = [stock_codes[i:i + chunk_size] for i in range(0, len(stock_codes), chunk_size)]
        
        total_stocks = len(stock_codes)
        logger.info(f'开始下载 {total_stocks} 只股票的日线数据，分 {len(stock_chunks)} 批处理')
        
        # 创建总体进度条
        with tqdm(total=total_stocks, desc="总体进度", position=0) as pbar:
            for chunk_idx, chunk in enumerate(stock_chunks, 1):
                # 创建批次进度条
                with tqdm(total=len(chunk), desc=f"批次 {chunk_idx}/{len(stock_chunks)}", position=1, leave=False) as chunk_pbar:
                    # 创建任务列表
                    tasks = []
                    for code in chunk:
                        task = asyncio.create_task(self._download_stock_data(code, start_date, end_date))
                        tasks.append(task)
                    
                    # 等待所有任务完成
                    results = await asyncio.gather(*tasks)
                    
                    # 处理结果
                    success_count = 0
                    for _, daily_df, _ in results:
                        if daily_df is not None:
                            success_count += 1
                        chunk_pbar.update(1)
                        pbar.update(1)
                    
                    # 更新批次进度条描述
                    chunk_pbar.set_description(f"批次 {chunk_idx}/{len(stock_chunks)} (成功: {success_count}/{len(chunk)})")
        
        logger.info(f'所有批次处理完成，共处理 {total_stocks} 只股票')

    def run_batch_download(self, stock_codes: Optional[List[str]] = None, start_date: Optional[str] = None, end_date: Optional[str] = None):
        """运行批量下载
        同步方法，用于在同步环境中启动异步下载任务
        
        Args:
            stock_codes: 股票代码列表，如果为None则下载所有股票
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
        """
        asyncio.run(self.batch_download_daily_data(stock_codes, start_date, end_date))

    def download_dividend_data(self, stock_code: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        """下载分红数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
            
        Returns:
            pd.DataFrame: 分红数据
        """
        start_date = start_date or self.config.get('start_date', '2010-01-01')
        end_date = end_date or self.config.get('end_date') or datetime.now().strftime('%Y-%m-%d')
        fields = self.config.get('fields', {}).get('dividend')
        
        logger.info(f'下载 {stock_code} 的分红数据 ({start_date} to {end_date})')
        rs = self._make_request(
            self.bs.query_dividend_data,
            code=stock_code,
            year=start_date.split('-')[0],
            yearType='report'
        )
        
        df = self._process_result(rs)
        if not df.empty:
            save_path = os.path.join(self.config.get('data_path', '../data/raw/baostock'), 'dividend', stock_code)
            os.makedirs(save_path, exist_ok=True)
            file_path = os.path.join(save_path, f'{stock_code}_dividend.csv')
            
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
            logger.info(f'分红数据已保存至: {file_path}')
            
        return df

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

    ''' TODO 以下这些方法需要后期实现 '''
    def download_minute_data(self, stock_code: str, start_date: Optional[str] = None, end_date: Optional[str] = None,
                             frequency: str = '1min') -> pd.DataFrame:
        pass

    def download_tick_data(self, stock_code: str, trade_date: str) -> pd.DataFrame:
        pass

    def download_level2_data(self, stock_code: str, trade_date: str) -> pd.DataFrame:
        pass

    def download_financial_data(self, stock_code: str, start_date: Optional[str] = None,
                                end_date: Optional[str] = None) -> pd.DataFrame:
        pass

    async def batch_download_minute_data(self, stock_codes: Optional[List[str]] = None,
                                         start_date: Optional[str] = None, end_date: Optional[str] = None,
                                         frequency: str = '1min') -> None:
        pass

    async def batch_download_tick_data(self, stock_codes: Optional[List[str]] = None,
                                       trade_date: Optional[str] = None) -> None:
        pass

    async def batch_download_level2_data(self, stock_codes: Optional[List[str]] = None,
                                         trade_date: Optional[str] = None) -> None:
        pass