"""
数据处理工具模块
提供数据读写和处理的通用功能
"""

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from typing import Union, Optional, Dict, Any

def save_parquet(
    df: pd.DataFrame,
    path: Union[str, Path],
    partition_cols: Optional[list] = None,
    compression: str = 'snappy',
    **kwargs
) -> None:
    """
    保存DataFrame到Parquet文件
    
    Args:
        df (pd.DataFrame): 要保存的数据
        path (Union[str, Path]): 保存路径
        partition_cols (Optional[list], optional): 分区列. Defaults to None.
        compression (str, optional): 压缩方式. Defaults to 'snappy'.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    table = pa.Table.from_pandas(df)
    
    if partition_cols:
        pq.write_to_dataset(
            table,
            path,
            partition_cols=partition_cols,
            compression=compression,
            **kwargs
        )
    else:
        pq.write_table(
            table,
            path,
            compression=compression,
            **kwargs
        )

def load_parquet(
    path: Union[str, Path],
    columns: Optional[list] = None,
    filters: Optional[list] = None,
    **kwargs
) -> pd.DataFrame:
    """
    从Parquet文件加载数据
    
    Args:
        path (Union[str, Path]): 数据路径
        columns (Optional[list], optional): 要读取的列. Defaults to None.
        filters (Optional[list], optional): 过滤条件. Defaults to None.
    
    Returns:
        pd.DataFrame: 加载的数据
    """
    path = Path(path)
    if path.is_dir():
        return pd.read_parquet(path, columns=columns, filters=filters, **kwargs)
    else:
        return pd.read_parquet(path, columns=columns, **kwargs)

def validate_data(
    df: pd.DataFrame,
    rules: Dict[str, Any]
) -> tuple[bool, list]:
    """
    验证数据质量
    
    Args:
        df (pd.DataFrame): 要验证的数据
        rules (Dict[str, Any]): 验证规则
    
    Returns:
        tuple[bool, list]: (是否通过验证, 错误信息列表)
    """
    errors = []
    
    # 检查缺失值
    if rules.get('check_missing', True):
        missing_threshold = rules.get('missing_rate', 0.1)
        missing_rates = df.isnull().mean()
        for col, rate in missing_rates.items():
            if rate > missing_threshold:
                errors.append(f"列 {col} 的缺失率 ({rate:.2%}) 超过阈值 ({missing_threshold:.2%})")
    
    # 检查异常值
    if rules.get('check_anomaly', True):
        price_change_threshold = rules.get('price_change', 0.2)
        volume_change_threshold = rules.get('volume_change', 5.0)
        
        # 检查价格变动
        for col in ['open', 'high', 'low', 'close']:
            if col in df.columns:
                pct_change = df[col].pct_change().abs()
                anomalies = pct_change > price_change_threshold
                if anomalies.any():
                    count = anomalies.sum()
                    errors.append(f"列 {col} 存在 {count} 个价格变动超过 {price_change_threshold:.2%} 的异常值")
        
        # 检查成交量变动
        if 'volume' in df.columns:
            vol_change = df['volume'].pct_change().abs()
            anomalies = vol_change > volume_change_threshold
            if anomalies.any():
                count = anomalies.sum()
                errors.append(f"成交量存在 {count} 个变动超过 {volume_change_threshold:.2f} 倍的异常值")
    
    return len(errors) == 0, errors 