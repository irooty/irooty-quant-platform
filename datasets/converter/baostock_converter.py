#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import pandas as pd
from pathlib import Path
from datetime import datetime
from loguru import logger
from typing import Optional, Dict, Any, List
from utils.path_utils import load_config
from .base_converter import BaseConverter

class BaostockConverter(BaseConverter):
    """Baostock数据转换器
    将Baostock数据转换为Qlib格式
    """
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """加载配置文件"""
        if config_path is None:
            return load_config("market_provider.yaml")
        else:
            # 如果提供了具体路径，使用path_utils的方法
            from utils.path_utils import get_config_path
            config_file = get_config_path(config_path)
            with open(config_file, 'r', encoding='utf-8') as f:
                import yaml
                return yaml.safe_load(f)
    
    def _get_stock_list(self) -> List[str]:
        """获取股票列表"""
        stock_list_dir = os.path.join(self.config['data_path'], 'stock_list')
        # 获取最新的股票列表文件
        files = os.listdir(stock_list_dir)
        latest_file = sorted(files)[-1]
        file_path = os.path.join(stock_list_dir, latest_file)
        
        df = pd.read_csv(file_path)
        return df['code'].tolist()
    
    def _process_daily_data(self, stock_code: str) -> Optional[pd.DataFrame]:
        """处理单个股票的日线数据
        
        Args:
            stock_code: 股票代码
            
        Returns:
            Optional[pd.DataFrame]: 处理后的日线数据
        """
        file_path = os.path.join(self.config['data_path'], 'daily', stock_code, f'{stock_code}_daily.csv')
        if not os.path.exists(file_path):
            logger.warning(f'找不到股票 {stock_code} 的日线数据文件')
            return None
            
        df = pd.read_csv(file_path)
        
        # 转换日期格式
        df['date'] = pd.to_datetime(df['date'])
        
        # 重命名列以符合Qlib格式
        rename_dict = {
            'date': 'datetime',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume',
            'amount': 'amount',
            'turn': 'turn',
            'pctChg': 'ret',
            'peTTM': 'pe',
            'pbMRQ': 'pb',
            'psTTM': 'ps',
            'pcfNcfTTM': 'pcf'
        }
        
        df = df.rename(columns=rename_dict)
        
        # 选择需要的列
        columns = ['datetime', 'open', 'high', 'low', 'close', 'volume', 'amount', 'turn', 'ret', 'pe', 'pb', 'ps', 'pcf']
        df = df[columns]
        
        # 将数值列转换为float类型
        numeric_columns = columns[1:]
        df[numeric_columns] = df[numeric_columns].astype(float)
        
        return df
    
    def _process_financial_data(self, stock_code: str) -> Optional[pd.DataFrame]:
        """处理单个股票的财务数据
        
        Args:
            stock_code: 股票代码
            
        Returns:
            Optional[pd.DataFrame]: 处理后的财务数据
        """
        file_path = os.path.join(self.config['data_path'], 'financial', stock_code, f'{stock_code}_financial.csv')
        if not os.path.exists(file_path):
            logger.warning(f'找不到股票 {stock_code} 的财务数据文件')
            return None
            
        df = pd.read_csv(file_path)
        
        # 转换日期格式
        df['date'] = pd.to_datetime(df['date'])
        
        # 重命名列以符合Qlib格式
        rename_dict = {
            'date': 'datetime',
            'roe': 'roe',
            'roa': 'roa',
            'grossProfitMargin': 'gross_profit_margin',
            'netProfitMargin': 'net_profit_margin',
            'debtToEquity': 'debt_to_equity',
            'currentRatio': 'current_ratio',
            'quickRatio': 'quick_ratio',
            'inventoryTurnover': 'inventory_turnover',
            'assetTurnover': 'asset_turnover',
            'operatingProfitMargin': 'operating_profit_margin'
        }
        
        df = df.rename(columns=rename_dict)
        
        # 选择需要的列
        columns = ['datetime', 'roe', 'roa', 'gross_profit_margin', 'net_profit_margin',
                  'debt_to_equity', 'current_ratio', 'quick_ratio', 'inventory_turnover',
                  'asset_turnover', 'operating_profit_margin']
        df = df[columns]
        
        # 将数值列转换为float类型
        numeric_columns = columns[1:]
        df[numeric_columns] = df[numeric_columns].astype(float)
        
        return df 