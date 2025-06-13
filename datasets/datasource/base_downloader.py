#!/usr/bin/env python
# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Union
import pandas as pd
from datetime import datetime
from loguru import logger

class BaseDownloader(ABC):
    """数据下载器基类
    定义了数据下载的标准接口，所有具体的数据源下载器都应该继承这个类
    并实现其抽象方法
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化下载器
        
        Args:
            config_path: 配置文件路径，默认为None
        """
        self.config = self._load_config(config_path)
        
    @abstractmethod
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """加载配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            Dict[str, Any]: 配置信息字典
        """
        pass
    
    @abstractmethod
    def download_stock_list(self) -> pd.DataFrame:
        """下载股票列表
        
        Returns:
            pd.DataFrame: 股票列表数据，包含股票代码、名称等信息
        """
        pass
    
    @abstractmethod
    def download_daily_data(self, stock_code: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        """下载单个股票的日线数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
            
        Returns:
            pd.DataFrame: 日线数据
        """
        pass
    
    @abstractmethod
    def download_minute_data(self, stock_code: str, start_date: Optional[str] = None, end_date: Optional[str] = None, 
                           frequency: str = '1min') -> pd.DataFrame:
        """下载单个股票的分钟线数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
            frequency: 分钟线频率，可选值：'1min', '5min', '15min', '30min', '60min'
            
        Returns:
            pd.DataFrame: 分钟线数据
        """
        pass
    
    @abstractmethod
    def download_tick_data(self, stock_code: str, trade_date: str) -> pd.DataFrame:
        """下载单个股票的逐笔成交数据
        
        Args:
            stock_code: 股票代码
            trade_date: 交易日期，格式：YYYY-MM-DD
            
        Returns:
            pd.DataFrame: 逐笔成交数据
        """
        pass
    
    @abstractmethod
    def download_level2_data(self, stock_code: str, trade_date: str) -> pd.DataFrame:
        """下载单个股票的Level-2行情数据
        
        Args:
            stock_code: 股票代码
            trade_date: 交易日期，格式：YYYY-MM-DD
            
        Returns:
            pd.DataFrame: Level-2行情数据
        """
        pass
    
    @abstractmethod
    def download_dividend_data(self, stock_code: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        """下载分红数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
            
        Returns:
            pd.DataFrame: 分红数据
        """
        pass
    
    @abstractmethod
    def download_financial_data(self, stock_code: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        """下载财务数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
            
        Returns:
            pd.DataFrame: 财务数据
        """
        pass
    
    @abstractmethod
    async def batch_download_daily_data(self, stock_codes: Optional[List[str]] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> None:
        """异步批量下载日线数据
        
        Args:
            stock_codes: 股票代码列表，如果为None则下载所有股票
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
        """
        pass
    
    @abstractmethod
    async def batch_download_minute_data(self, stock_codes: Optional[List[str]] = None, start_date: Optional[str] = None, 
                                       end_date: Optional[str] = None, frequency: str = '1min') -> None:
        """异步批量下载分钟线数据
        
        Args:
            stock_codes: 股票代码列表，如果为None则下载所有股票
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
            frequency: 分钟线频率，可选值：'1min', '5min', '15min', '30min', '60min'
        """
        pass
    
    @abstractmethod
    async def batch_download_tick_data(self, stock_codes: Optional[List[str]] = None, trade_date: Optional[str] = None) -> None:
        """异步批量下载逐笔成交数据
        
        Args:
            stock_codes: 股票代码列表，如果为None则下载所有股票
            trade_date: 交易日期，格式：YYYY-MM-DD
        """
        pass
    
    @abstractmethod
    async def batch_download_level2_data(self, stock_codes: Optional[List[str]] = None, trade_date: Optional[str] = None) -> None:
        """异步批量下载Level-2行情数据
        
        Args:
            stock_codes: 股票代码列表，如果为None则下载所有股票
            trade_date: 交易日期，格式：YYYY-MM-DD
        """
        pass
    
    def run_batch_download(self, stock_codes: Optional[List[str]] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> None:
        """运行批量下载
        同步方法，用于在同步环境中启动异步下载任务
        
        Args:
            stock_codes: 股票代码列表，如果为None则下载所有股票
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
        """
        import asyncio
        asyncio.run(self.batch_download_daily_data(stock_codes, start_date, end_date)) 