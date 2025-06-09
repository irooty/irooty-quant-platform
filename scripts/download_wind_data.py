"""
Wind数据下载脚本
用于从Wind金融终端下载股票数据
"""

import argparse
import yaml
from pathlib import Path
from datasets.wind import WindDownloader, DataCleaner, QlibConverter
from utils.logger import setup_logger

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='下载Wind数据并转换为Qlib格式')
    parser.add_argument('--config', type=str, required=True, help='配置文件路径')
    args = parser.parse_args()
    
    # 加载配置
    with open(args.config, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 设置日志
    logger = setup_logger('wind_data_pipeline', config.get('logging', {}))
    logger.info("开始数据处理流程")
    
    try:
        # 1. 下载数据
        logger.info("第1步：下载数据")
        downloader = WindDownloader(config)
        if not downloader.download_data():
            raise ValueError("数据下载失败")
        
        # 2. 清洗数据
        logger.info("第2步：清洗数据")
        cleaner = DataCleaner(config)
        cleaner.clean_data()
        
        # 3. 转换为Qlib格式
        logger.info("第3步：转换为Qlib格式")
        converter = QlibConverter(config)
        converter.convert_to_qlib()
        
        logger.info("数据处理流程完成")
        
    except Exception as e:
        logger.error(f"数据处理流程失败: {e}")
        raise

if __name__ == '__main__':
    main() 