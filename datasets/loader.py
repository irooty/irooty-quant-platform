#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
from loguru import logger
import pyarrow.parquet as pq

class DataLoader:
    """数据加载模块"""
    
    def __init__(self, data_dir: str):
        """初始化加载器
        
        Args:
            data_dir: 数据目录
        """
        self.data_dir = data_dir
        
    def load_stock_data(self, stock_code: str, 
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> pd.DataFrame:
        """加载单个股票的数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
            
        Returns:
            pd.DataFrame: 股票数据
        """
        # 构建数据文件路径
        file_path = os.path.join(self.data_dir, stock_code, 'data.parquet')
        
        if not os.path.exists(file_path):
            logger.warning(f'找不到股票 {stock_code} 的数据文件')
            return pd.DataFrame()
        
        # 读取parquet文件
        df = pq.read_table(file_path).to_pandas()
        
        # 日期过滤
        if start_date:
            df = df[df['datetime'] >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df['datetime'] <= pd.to_datetime(end_date)]
            
        return df
    
    def load_multiple_stocks(self, stock_codes: List[str],
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> Dict[str, pd.DataFrame]:
        """加载多个股票的数据
        
        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
            
        Returns:
            Dict[str, pd.DataFrame]: 股票代码到数据的映射
        """
        result = {}
        for code in stock_codes:
            df = self.load_stock_data(code, start_date, end_date)
            if not df.empty:
                result[code] = df
                
        return result
    
    def create_dataset(self, stock_codes: List[str],
                      features: List[str],
                      target: str,
                      lookback: int = 20,
                      horizon: int = 5,
                      train_ratio: float = 0.8) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """创建用于机器学习的数据集
        
        Args:
            stock_codes: 股票代码列表
            features: 特征列表
            target: 目标变量
            lookback: 历史数据窗口大小
            horizon: 预测周期
            train_ratio: 训练集比例
            
        Returns:
            Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]: 
            (训练特征, 训练标签, 测试特征, 测试标签)
        """
        X, y = [], []
        
        # 加载所有股票数据
        stock_data = self.load_multiple_stocks(stock_codes)
        
        for code, df in stock_data.items():
            if df.empty:
                continue
                
            # 确保所有特征都存在
            if not all(feat in df.columns for feat in features):
                logger.warning(f'股票 {code} 缺少部分特征，跳过')
                continue
                
            # 提取特征和目标
            data = df[features].values
            target_data = df[target].values
            
            # 创建时间窗口样本
            for i in range(len(data) - lookback - horizon + 1):
                X.append(data[i:(i + lookback)])
                y.append(target_data[i + lookback + horizon - 1])
                
        X = np.array(X)
        y = np.array(y)
        
        # 划分训练集和测试集
        train_size = int(len(X) * train_ratio)
        X_train = X[:train_size]
        y_train = y[:train_size]
        X_test = X[train_size:]
        y_test = y[train_size:]
        
        return X_train, y_train, X_test, y_test