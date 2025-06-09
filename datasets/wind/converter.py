"""
Qlib格式转换模块
负责将清洗后的数据转换为Qlib格式
"""

import json
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
import numpy as np
from utils.logger import setup_logger
from utils.data_utils import load_parquet, save_parquet

class QlibConverter:
    def __init__(self, config: Dict[str, Any]):
        """
        初始化Qlib格式转换器
        
        Args:
            config (Dict[str, Any]): 配置信息
        """
        self.config = config
        self.logger = setup_logger(__name__, config.get('logging', {}))
        
        # 设置数据目录
        self.processed_dir = Path(config['paths']['processed_dir'])
        self.qlib_dir = Path(config['paths']['qlib_dir'])
        self.qlib_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建Qlib目录结构
        (self.qlib_dir / 'calendars').mkdir(exist_ok=True)
        (self.qlib_dir / 'instruments').mkdir(exist_ok=True)
        (self.qlib_dir / 'features').mkdir(exist_ok=True)
    
    def _prepare_calendar(self, df: pd.DataFrame) -> None:
        """
        准备交易日历
        
        Args:
            df (pd.DataFrame): 输入数据
        """
        # 获取所有交易日期
        calendar = pd.to_datetime(df['date'].unique()).sort_values()
        
        # 保存为txt文件
        calendar_file = self.qlib_dir / 'calendars' / 'all_calendar.txt'
        calendar.strftime('%Y-%m-%d').to_series().to_csv(
            calendar_file,
            index=False,
            header=False
        )
        self.logger.info(f"交易日历已保存到: {calendar_file}")
    
    def _prepare_instruments(self, df: pd.DataFrame) -> None:
        """
        准备标的列表
        
        Args:
            df (pd.DataFrame): 输入数据
        """
        # 获取所有股票代码
        instruments = df['stock_code'].unique()
        
        # 保存为txt文件
        instruments_file = self.qlib_dir / 'instruments' / 'all.txt'
        pd.Series(instruments).to_csv(
            instruments_file,
            index=False,
            header=False
        )
        self.logger.info(f"标的列表已保存到: {instruments_file}")
    
    def _prepare_features(self, df: pd.DataFrame) -> None:
        """
        准备特征数据
        
        Args:
            df (pd.DataFrame): 输入数据
        """
        # Qlib特征映射
        feature_mapping = {
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume',
            'amt': 'amount',
            'turn': 'turn_rate',
            'trade_status': 'is_trading',
            'factor': 'factor'
        }
        
        # 转换交易状态为数值
        if 'trade_status' in df.columns:
            df['is_trading'] = (df['trade_status'] != '停牌').astype(int)
        
        # 重命名列
        df = df.rename(columns=feature_mapping)
        
        # 按股票和日期分组保存
        for stock_code in df['stock_code'].unique():
            stock_data = df[df['stock_code'] == stock_code].sort_values('date')
            
            # 创建股票特征目录
            stock_dir = self.qlib_dir / 'features' / stock_code
            stock_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存每个特征
            for feature in feature_mapping.values():
                if feature in stock_data.columns:
                    feature_file = stock_dir / f"{feature}.{self.config['storage']['format']}"
                    feature_data = stock_data[['date', feature]]
                    save_parquet(feature_data, feature_file)
            
            self.logger.info(f"股票 {stock_code} 的特征数据已保存")
    
    def _create_metadata(self) -> None:
        """创建元数据文件"""
        metadata = {
            'version': '0.1.0',
            'data_type': 'CN_STOCK_A',
            'frequency': '1d',
            'fields': [
                'open', 'high', 'low', 'close',
                'volume', 'amount', 'turn_rate',
                'is_trading', 'factor'
            ],
            'storage_format': self.config['storage']['format'],
            'compression': self.config['storage']['compression']
        }
        
        metadata_file = self.qlib_dir / 'metadata.json'
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"元数据已保存到: {metadata_file}")
    
    def convert_to_qlib(self) -> None:
        """转换为Qlib格式的主函数"""
        try:
            # 加载清洗后的数据
            self.logger.info("开始加载清洗后的数据")
            df = load_parquet(self.processed_dir / 'cleaned_data.parquet')
            self.logger.info(f"成功加载 {len(df)} 条数据")
            
            # 准备交易日历
            self.logger.info("开始准备交易日历")
            self._prepare_calendar(df)
            
            # 准备标的列表
            self.logger.info("开始准备标的列表")
            self._prepare_instruments(df)
            
            # 准备特征数据
            self.logger.info("开始准备特征数据")
            self._prepare_features(df)
            
            # 创建元数据
            self.logger.info("开始创建元数据")
            self._create_metadata()
            
            self.logger.info("数据转换完成")
            
        except Exception as e:
            self.logger.error(f"数据转换失败: {e}")
            raise 