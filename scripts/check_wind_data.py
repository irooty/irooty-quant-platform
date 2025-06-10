"""
用于检查Wind下载的数据内容的工具脚本
"""

import pandas as pd
from pathlib import Path
import sys

def check_stock_list():
    """检查股票列表文件"""
    file_path = Path("data/raw/wind/stock_list.parquet")
    if not file_path.exists():
        print(f"错误：找不到股票列表文件: {file_path}")
        return
    
    df = pd.read_parquet(file_path)
    print("\n=== 股票列表文件信息 ===")
    print(f"文件路径: {file_path}")
    print(f"数据形状: {df.shape}")
    print(f"列名: {df.columns.tolist()}")
    print("\n前5行数据:")
    print(df.head())

def check_batch_data():
    """检查批次数据文件"""
    data_dir = Path("data/raw/wind")
    batch_files = list(data_dir.glob("batch_*.parquet"))
    
    if not batch_files:
        print(f"错误：在 {data_dir} 中找不到批次数据文件")
        return
    
    for file_path in batch_files:
        print(f"\n=== 批次文件信息: {file_path.name} ===")
        df = pd.read_parquet(file_path)
        
        print(f"数据形状: {df.shape}")
        print(f"索引类型: {df.index.dtype}")
        print(f"列名: {df.columns.tolist()}")
        
        # 显示数据基本信息
        print("\n数据基本信息:")
        print(df.info())
        
        # 显示数据示例
        print("\n前3行数据:")
        print(df.head(3))
        
        # 检查是否有多层级列名
        if isinstance(df.columns[0], tuple):
            print("\n多层级列名结构:")
            print(df.columns.levels)
        
        # 显示基本统计信息
        print("\n数值列的基本统计信息:")
        print(df.describe())

def main():
    print("开始检查Wind下载的数据...")
    
    # 检查股票列表
    check_stock_list()
    
    # 检查批次数据
    check_batch_data()

if __name__ == "__main__":
    main() 