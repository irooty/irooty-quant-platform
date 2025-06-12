#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any
from pathlib import Path
from loguru import logger

class DataPreprocessor:
    """数据预处理模块"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化预处理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """数据清洗
        
        Args:
            df: 输入数据
            
        Returns:
            pd.DataFrame: 清洗后的数据
        """
        # 1. 删除重复行
        df = df.drop_duplicates()
        
        # 2. 处理缺失值
        df = self._handle_missing_values(df)
        
        # 3. 异常值处理
        df = self._handle_outliers(df)
        
        return df
    
    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理缺失值
        
        Args:
            df: 输入数据
            
        Returns:
            pd.DataFrame: 处理后的数据
        """
        # 1. 对于数值列，使用中位数填充
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].median())
        
        # 2. 对于分类列，使用众数填充
        categorical_cols = df.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            df[col] = df[col].fillna(df[col].mode()[0])
            
        return df
    
    def _handle_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理异常值
        
        Args:
            df: 输入数据
            
        Returns:
            pd.DataFrame: 处理后的数据
        """
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols:
            # 使用IQR方法处理异常值
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            # 将异常值替换为边界值
            df[col] = df[col].clip(lower=lower_bound, upper=upper_bound)
            
        return df
    
    def feature_engineering(self, df: pd.DataFrame) -> pd.DataFrame:
        """特征工程
        
        Args:
            df: 输入数据
            
        Returns:
            pd.DataFrame: 处理后的数据
        """
        # 1. 技术指标计算
        df = self._calculate_technical_indicators(df)
        
        # 2. 特征标准化
        df = self._standardize_features(df)
        
        return df
    
    def _calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标
        
        Args:
            df: 输入数据
            
        Returns:
            pd.DataFrame: 添加技术指标后的数据
        """
        # 1. 移动平均线
        df['MA5'] = df['close'].rolling(window=5).mean()
        df['MA10'] = df['close'].rolling(window=10).mean()
        df['MA20'] = df['close'].rolling(window=20).mean()
        
        # 2. 相对强弱指标 (RSI)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # 3. MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
        
        return df
    
    def _standardize_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """特征标准化
        
        Args:
            df: 输入数据
            
        Returns:
            pd.DataFrame: 标准化后的数据
        """
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        # 使用Z-Score标准化
        for col in numeric_cols:
            mean = df[col].mean()
            std = df[col].std()
            if std != 0:  # 避免除以0
                df[f'{col}_standardized'] = (df[col] - mean) / std
                
        return df