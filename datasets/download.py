#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from utils.path_utils import get_config_path

logger = logging.getLogger(__name__)

def load_config(config_path: str) -> Dict[str, Any]:
    """加载配置文件"""
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    with open(config_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def get_market_provider(config: Dict[str, Any], provider: str) -> Dict[str, Any]:
    """金融数据提供方"""
    if provider not in config:
        raise ValueError(f"不支持的数据提供方: {provider}")
    return config[provider]

def import_class(module_path: str, class_name: str) -> Any:
    """动态导入类"""
    module = __import__(module_path, fromlist=[class_name])
    return getattr(module, class_name)

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='数据下载调度器')
    parser.add_argument('--config', type=str, default=get_config_path('market_provider.yaml'), help='配置文件路径')
    parser.add_argument('--provider', type=str, required=True, help='金融数据提供方 (baostock/wind)')
    parser.add_argument('--start-date', type=str, help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--convert', action='store_true', help='是否转换为Qlib格式')
    parser.add_argument('--stock-codes', type=str, help='要下载的股票列表，支持逗号分隔字符串（如 sh.600000,sz.000001）或文件路径（如 codes.txt，每行一个或逗号分隔）')
    parser.add_argument('--interval', type=str, default='1d', help='数据间隔，支持1min、5min、15min、30min、1h、1d、1w、1m、1q、1y，默认1d表示日数据')
    return parser.parse_args()

def main():
    """主函数"""
    # 解析参数
    args = parse_args()
    
    # 加载配置
    config = load_config(args.config)
    provider_config = get_market_provider(config, args.provider)
    
    try:
        # 初始化下载器
        downloader_class = import_class(
            provider_config['downloader']['module'],
            provider_config['downloader']['class']
        )
        downloader = downloader_class(
            args.config,
            provider=args.provider,
            start_date=args.start_date,
            end_date=args.end_date,
            convert=args.convert,
            interval=args.interval,
            stock_codes=args.stock_codes
        )
        
        # 下载数据
        logger.info(f"开始从 {args.provider} 下载数据...")
        downloader.batch_download()
        logger.info("数据下载完成")
        
        # 如果需要转换
        if args.convert:
            # 初始化转换器
            converter_class = import_class(
                provider_config['converter']['module'],
                provider_config['converter']['class']
            )
            converter = converter_class(args.config)
            
            # 转换数据
            logger.info("开始转换数据...")
            converter.convert()
            logger.info("数据转换完成")
            
    except Exception as e:
        logger.error(f"处理失败: {str(e)}")
        raise

if __name__ == '__main__':
    main()