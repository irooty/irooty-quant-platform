"""
数据清洗模块
负责清洗和预处理Wind下载的原始数据
"""

from pathlib import Path
from typing import Dict, Any, Union, List
import pandas as pd
import numpy as np
from utils.logger import setup_logger
from utils.data_utils import load_parquet, save_parquet, validate_data

class DataCleaner:
    def __init__(self, config: Dict[str, Any]):
        """
        初始化数据清洗器
        
        Args:
            config (Dict[str, Any]): 配置信息
        """
        self.config = config
        self.logger = setup_logger(__name__, config.get('logging', {}))
        
        # 设置数据目录
        self.raw_dir = Path(config['paths']['raw_dir'])
        self.processed_dir = Path(config['paths']['processed_dir'])
        self.processed_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_raw_data(self) -> pd.DataFrame:
        """
        加载原始数据
        
        Returns:
            pd.DataFrame: 合并后的原始数据
        """
        dfs = []
        for file in self.raw_dir.glob('batch_*.parquet'):
            try:
                df = load_parquet(file)
                dfs.append(df)
            except Exception as e:
                self.logger.error(f"加载文件 {file} 失败: {e}")
        
        if not dfs:
            raise ValueError("没有找到原始数据文件")
        
        return pd.concat(dfs, ignore_index=True)
    
    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        处理缺失值
        
        Args:
            df (pd.DataFrame): 输入数据
        
        Returns:
            pd.DataFrame: 处理后的数据
        """
        # 对于交易状态的缺失值，填充为'停牌'
        if 'trade_status' in df.columns:
            df['trade_status'] = df['trade_status'].fillna('停牌')
        
        # 对于停牌日的价格，使用前值填充
        price_cols = ['open', 'high', 'low', 'close']
        for col in price_cols:
            if col in df.columns:
                df[col] = df.groupby('stock_code')[col].fillna(method='ffill')
        
        # 对于成交量和成交额，停牌日填充为0
        volume_cols = ['volume', 'amt']
        for col in volume_cols:
            if col in df.columns:
                df[col] = df[col].fillna(0)
        
        # 对于换手率，停牌日填充为0
        if 'turn' in df.columns:
            df['turn'] = df['turn'].fillna(0)
        
        return df
    
    def _handle_anomalies(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        处理异常值
        
        Args:
            df (pd.DataFrame): 输入数据
        
        Returns:
            pd.DataFrame: 处理后的数据
        """
        # 检查价格是否为负
        price_cols = ['open', 'high', 'low', 'close']
        for col in price_cols:
            if col in df.columns:
                mask = df[col] < 0
                if mask.any():
                    self.logger.warning(f"发现 {mask.sum()} 个负的 {col} 价格，将被设置为NaN")
                    df.loc[mask, col] = np.nan
        
        # 检查成交量和成交额是否为负
        volume_cols = ['volume', 'amt']
        for col in volume_cols:
            if col in df.columns:
                mask = df[col] < 0
                if mask.any():
                    self.logger.warning(f"发现 {mask.sum()} 个负的 {col}，将被设置为0")
                    df.loc[mask, col] = 0
        
        # 检查换手率是否为负或超过100%
        if 'turn' in df.columns:
            mask = (df['turn'] < 0) | (df['turn'] > 100)
            if mask.any():
                self.logger.warning(f"发现 {mask.sum()} 个异常换手率，将被设置为NaN")
                df.loc[mask, 'turn'] = np.nan
        
        return df
    
    def _validate_cleaned_data(self, df: pd.DataFrame) -> bool:
        """
        验证清洗后的数据
        
        Args:
            df (pd.DataFrame): 清洗后的数据
        
        Returns:
            bool: 验证是否通过
        """
        rules = self.config.get('validation', {})
        passed, errors = validate_data(df, rules)
        
        if not passed:
            for error in errors:
                self.logger.warning(f"数据验证警告: {error}")
        
        return passed
    
    def clean_data(self) -> None:
        """清洗数据的主函数"""
        try:
            # 加载原始数据
            self.logger.info("开始加载原始数据")
            df = self._load_raw_data()
            self.logger.info(f"成功加载 {len(df)} 条原始数据")
            
            # 处理缺失值
            self.logger.info("开始处理缺失值")
            df = self._handle_missing_values(df)
            
            # 处理异常值
            self.logger.info("开始处理异常值")
            df = self._handle_anomalies(df)
            
            # 验证数据
            self.logger.info("开始验证数据")
            if self._validate_cleaned_data(df):
                self.logger.info("数据验证通过")
            else:
                self.logger.warning("数据验证未完全通过，但将继续处理")
            
            # 保存清洗后的数据
            save_path = self.processed_dir / 'cleaned_data.parquet'
            save_parquet(df, save_path)
            self.logger.info(f"清洗后的数据已保存到: {save_path}")
            
        except Exception as e:
            self.logger.error(f"数据清洗失败: {e}")
            raise 