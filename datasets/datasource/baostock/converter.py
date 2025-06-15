#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import pandas as pd
import numpy as np
from pathlib import Path
from loguru import logger
import yaml
from datetime import datetime
import pyarrow as pa
import pyarrow.parquet as pq

class BaostockToQlibConverter:
    """将Baostock数据转换为Qlib格式"""
    
    def __init__(self, config_path=None):
        """初始化转换器
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        
    def _load_config(self, config_path):
        """加载配置文件"""
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / 'config' / 'market_provider.yaml'
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _load_stock_list(self):
        """加载股票列表"""
        stock_list_dir = os.path.join(self.config['data_path'], 'stock_list')
        # 获取最新的股票列表文件
        files = os.listdir(stock_list_dir)
        latest_file = sorted(files)[-1]
        file_path = os.path.join(stock_list_dir, latest_file)
        
        return pd.read_csv(file_path)
    
    def _process_daily_data(self, stock_code):
        """处理单个股票的日线数据"""
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
        
    def convert_to_qlib(self, output_dir):
        """转换为Qlib格式并保存
        
        Args:
            output_dir: 输出目录
        """
        logger.info('开始转换数据为Qlib格式...')
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 加载股票列表
        stock_list = self._load_stock_list()
        
        # 处理每个股票的数据
        for idx, row in stock_list.iterrows():
            stock_code = row['code']
            logger.info(f'处理股票 {stock_code} 的数据')
            
            try:
                # 处理日线数据
                daily_data = self._process_daily_data(stock_code)
                if daily_data is None:
                    continue
                
                # 创建股票特定的输出目录
                stock_output_dir = os.path.join(output_dir, stock_code.split('.')[0])
                os.makedirs(stock_output_dir, exist_ok=True)
                
                # 将数据保存为parquet格式
                table = pa.Table.from_pandas(daily_data)
                pq.write_table(table, os.path.join(stock_output_dir, 'data.parquet'))
                
                logger.info(f'成功转换股票 {stock_code} 的数据')
                
            except Exception as e:
                logger.error(f'处理股票 {stock_code} 时出错: {str(e)}')
                continue
        
        logger.info('数据转换完成') 