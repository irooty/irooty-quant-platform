#!/usr/bin/env python
# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
import pandas as pd
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
from loguru import logger

class BaseConverter(ABC):
    """数据转换器基类
    定义了将不同数据源的数据转换为Qlib格式的标准接口
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化转换器
        
        Args:
            config_path: 配置文件路径
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
    def _process_daily_data(self, stock_code: str) -> Optional[pd.DataFrame]:
        """处理单个股票的日线数据
        
        Args:
            stock_code: 股票代码
            
        Returns:
            Optional[pd.DataFrame]: 处理后的日线数据
        """
        pass
    
    @abstractmethod
    def _process_financial_data(self, stock_code: str) -> Optional[pd.DataFrame]:
        """处理单个股票的财务数据
        
        Args:
            stock_code: 股票代码
            
        Returns:
            Optional[pd.DataFrame]: 处理后的财务数据
        """
        pass
    
    def _save_to_parquet(self, df: pd.DataFrame, save_path: Path) -> None:
        """保存数据为parquet格式
        
        Args:
            df: 数据DataFrame
            save_path: 保存路径
        """
        try:
            # 创建目录
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 转换为pyarrow table
            table = pa.Table.from_pandas(df)
            
            # 保存为parquet格式
            pq.write_table(table, save_path)
            
            logger.info(f'数据已保存至: {save_path}')
        except Exception as e:
            logger.error(f'保存数据失败: {str(e)}')
    
    def convert_to_qlib(self, output_dir: str) -> None:
        """转换为Qlib格式并保存
        
        Args:
            output_dir: 输出目录
        """
        logger.info('开始转换数据为Qlib格式...')
        
        # 创建输出目录
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 获取股票列表
        stock_list = self._get_stock_list()
        
        # 处理每个股票的数据
        for stock_code in stock_list:
            try:
                # 处理日线数据
                daily_data = self._process_daily_data(stock_code)
                if daily_data is not None:
                    # 创建股票特定的输出目录
                    stock_output_dir = output_path / stock_code.split('.')[0]
                    self._save_to_parquet(daily_data, stock_output_dir / 'data.parquet')
                
                # 处理财务数据
                financial_data = self._process_financial_data(stock_code)
                if financial_data is not None:
                    stock_output_dir = output_path / stock_code.split('.')[0]
                    self._save_to_parquet(financial_data, stock_output_dir / 'financial.parquet')
                
                logger.info(f'成功转换股票 {stock_code} 的数据')
                
            except Exception as e:
                logger.error(f'处理股票 {stock_code} 时出错: {str(e)}')
                continue
        
        logger.info('数据转换完成')
    
    @abstractmethod
    def _get_stock_list(self) -> List[str]:
        """获取股票列表
        
        Returns:
            List[str]: 股票代码列表
        """
        pass 