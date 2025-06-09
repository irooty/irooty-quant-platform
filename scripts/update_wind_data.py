"""
Wind数据增量更新脚本
用于增量更新Wind股票数据
"""

import argparse
import yaml
import time
from datetime import datetime, timedelta
from pathlib import Path
from datasets.wind import WindDownloader, DataCleaner, QlibConverter
from utils.logger import setup_logger
from utils.data_utils import load_parquet

def get_last_update_date(processed_dir: Path) -> str:
    """
    获取最后更新日期
    
    Args:
        processed_dir (Path): 处理后数据目录
    
    Returns:
        str: 最后更新日期，格式：YYYY-MM-DD
    """
    try:
        df = load_parquet(processed_dir / 'cleaned_data.parquet')
        return df['date'].max().strftime('%Y-%m-%d')
    except Exception:
        return None

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='增量更新Wind数据')
    parser.add_argument('--config', type=str, required=True, help='配置文件路径')
    args = parser.parse_args()
    
    # 加载配置
    with open(args.config, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 设置日志
    logger = setup_logger('wind_data_update', config.get('logging', {}))
    logger.info("开始增量更新流程")
    
    try:
        # 检查是否需要更新
        if not config['incremental']['enabled']:
            logger.info("增量更新未启用")
            return
        
        # 获取最后更新日期
        processed_dir = Path(config['paths']['processed_dir'])
        last_update = get_last_update_date(processed_dir)
        if not last_update:
            logger.error("无法获取最后更新日期")
            return
        
        # 计算更新起始日期（前一个交易日，以确保数据完整性）
        start_date = (datetime.strptime(last_update, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # 1. 下载增量数据
        logger.info(f"开始下载增量数据，起始日期: {start_date}")
        downloader = WindDownloader(config)
        stock_list = downloader.download_stock_list()
        if stock_list:
            downloader.download_incremental_data(stock_list, start_date)
        else:
            raise ValueError("获取股票列表失败")
        
        # 2. 清洗数据
        logger.info("清洗增量数据")
        cleaner = DataCleaner(config)
        cleaner.clean_data()
        
        # 3. 转换为Qlib格式
        logger.info("转换增量数据为Qlib格式")
        converter = QlibConverter(config)
        converter.convert_to_qlib()
        
        logger.info("增量更新完成")
        
    except Exception as e:
        logger.error(f"增量更新失败: {e}")
        raise

def run_scheduled_update():
    """运行定时更新"""
    parser = argparse.ArgumentParser(description='定时运行增量更新')
    parser.add_argument('--config', type=str, required=True, help='配置文件路径')
    args = parser.parse_args()
    
    # 加载配置
    with open(args.config, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    logger = setup_logger('wind_data_scheduler', config.get('logging', {}))
    
    while True:
        now = datetime.now()
        update_time = datetime.strptime(config['incremental']['update_time'], '%H:%M').time()
        
        # 如果是周末且未启用周末检查，则跳过
        if now.weekday() >= 5 and not config['incremental']['weekend_check']:
            logger.info("周末不更新")
            time.sleep(3600)  # 休眠1小时
            continue
        
        # 如果到达更新时间，执行更新
        if now.time().hour == update_time.hour and now.time().minute == update_time.minute:
            logger.info("开始定时更新")
            try:
                main()
            except Exception as e:
                logger.error(f"定时更新失败: {e}")
            
            # 更新后休眠到下一分钟
            time.sleep(60)
        else:
            # 否则休眠一分钟
            time.sleep(60)

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--scheduler':
        # 移除--scheduler参数
        sys.argv.pop(1)
        run_scheduled_update()
    else:
        main() 