"""
Wind数据转换模块
负责将Wind数据转换为Qlib格式
"""

from pathlib import Path
from typing import Dict, Any
import pandas as pd
from utils.logger import setup_logger
import qlib
from qlib.data import D
from qlib.data.dataset import DatasetH
from utils.data_utils import load_parquet
import shutil

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
        
        # 创建必要的目录
        self.qlib_dir.mkdir(parents=True, exist_ok=True)
    
    def convert_to_qlib(self) -> bool:
        """
        将处理后的Wind数据转换为Qlib格式
        
        Returns:
            bool: 转换是否成功
        """
        try:
            # 1. 读取清洗后的数据
            self.logger.info("第1步：读取清洗后的数据")
            processed_file = self.processed_dir / 'cleaned_data.parquet'
            df = load_parquet(processed_file)
            self.logger.info(f"成功加载 {len(df)} 条数据")
            
            # 2. 准备数据
            self.logger.info("第2步：准备数据")
            
            # 重命名列以匹配Qlib要求
            column_mapping = {
                'stock_code': 'instrument',  # instrument 是 Qlib 要求的列名
                'date': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume',
                'amt': 'amount',
                'turn': 'turn',
                'adjfactor': 'factor'
            }
            df = df.rename(columns=column_mapping)
            
            # 确保日期列的类型是datetime
            df['date'] = pd.to_datetime(df['date'])
            
            # 3. 使用 Qlib 的 DatasetH 转换数据
            self.logger.info("第3步：转换数据为Qlib格式")
            
            # 创建必要的目录结构
            features_dir = self.qlib_dir / 'features'
            instruments_dir = self.qlib_dir / 'instruments'
            calendars_dir = self.qlib_dir / 'calendars'
            
            for d in [features_dir, instruments_dir, calendars_dir]:
                d.mkdir(parents=True, exist_ok=True)
            
            # 按股票分组处理数据
            for instrument in df['instrument'].unique():
                stock_dir = features_dir / instrument.lower()
                stock_dir.mkdir(exist_ok=True)
                
                stock_data = df[df['instrument'] == instrument].sort_values('date')
                
                # 保存每个特征
                for field in ['open', 'high', 'low', 'close', 'volume', 'amount', 'turn', 'factor']:
                    if field in stock_data.columns:
                        field_file = stock_dir / f'{field}.day.bin'
                        stock_data[field].to_numpy().tofile(str(field_file))
            
            # 保存股票列表
            instruments = sorted(df['instrument'].unique())
            with open(instruments_dir / 'all.txt', 'w') as f:
                f.write('\n'.join(instruments))
            
            # 保存交易日历
            calendar = sorted(df['date'].unique())
            with open(calendars_dir / 'day.txt', 'w') as f:
                f.write('\n'.join(d.strftime('%Y-%m-%d') for d in calendar))
            
            # 4. 验证数据
            self.logger.info("第4步：验证数据")
            qlib.init(provider_uri=str(self.qlib_dir))
            instruments = D.list_instruments()
            self.logger.info(f"成功加载了 {len(instruments)} 只股票的数据")
            
            return True
            
        except Exception as e:
            self.logger.error(f"数据转换失败: {e}")
            return False 