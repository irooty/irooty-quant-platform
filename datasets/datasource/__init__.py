"""
数据源模块
提供统一的数据获取接口和各个数据源的具体实现
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
import pandas as pd
from pathlib import Path

class DataSourceBase(ABC):
    """数据源基类"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化数据源
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        
    @abstractmethod
    def download_stock_list(self) -> pd.DataFrame:
        """下载股票列表
        
        Returns:
            pd.DataFrame: 股票列表数据
        """
        pass
        
    @abstractmethod
    def download_daily_data(self, stock_code: str, start_date: Optional[str] = None, 
                          end_date: Optional[str] = None) -> pd.DataFrame:
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
    def batch_download_daily_data(self, stock_codes: Optional[List[str]] = None) -> None:
        """批量下载日线数据
        
        Args:
            stock_codes: 股票代码列表，如果为None则下载所有股票
        """
        pass

class DataConverterBase(ABC):
    """数据转换器基类"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化转换器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        
    @abstractmethod
    def convert_to_qlib(self, output_dir: str) -> None:
        """转换为Qlib格式并保存
        
        Args:
            output_dir: 输出目录
        """
        pass 