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

def get_data_source(config: Dict[str, Any], source: str) -> Dict[str, Any]:
    """获取数据源配置"""
    if source not in config:
        raise ValueError(f"不支持的数据源: {source}")
    return config[source]

def import_class(module_path: str, class_name: str) -> Any:
    """动态导入类"""
    module = __import__(module_path, fromlist=[class_name])
    return getattr(module, class_name)

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='数据下载调度器')
    parser.add_argument('--config', type=str, default=get_config_path('data_source.yaml'), help='配置文件路径')
    parser.add_argument('--source', type=str, required=True, help='数据源 (baostock/wind)')
    parser.add_argument('--start-date', type=str, help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--convert', action='store_true', help='是否转换为Qlib格式')
    parser.add_argument('--output-dir', type=str, help='Qlib格式数据输出目录')
    return parser.parse_args()

def main():
    """主函数"""
    # 解析参数
    args = parse_args()
    
    # 加载配置
    config = load_config(args.config)
    source_config = get_data_source(config, args.source)
    
    try:
        # 初始化下载器
        downloader_class = import_class(
            source_config['downloader']['module'],
            source_config['downloader']['class']
        )
        downloader = downloader_class(args.config)
        
        # 下载数据
        logger.info(f"开始从 {args.source} 下载数据...")
        downloader.batch_download_daily_data(
            start_date=args.start_date,
            end_date=args.end_date
        )
        logger.info("数据下载完成")
        
        # 如果需要转换
        if args.convert:
            # 初始化转换器
            converter_class = import_class(
                source_config['converter']['module'],
                source_config['converter']['class']
            )
            converter = converter_class(args.config)
            
            # 转换数据
            logger.info("开始转换数据...")
            converter.convert(output_dir=args.output_dir)
            logger.info("数据转换完成")
            
    except Exception as e:
        logger.error(f"处理失败: {str(e)}")
        raise

if __name__ == '__main__':
    main()