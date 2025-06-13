#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import argparse
from datetime import datetime
from loguru import logger

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.path_utils import get_config_path
from datasets.datasource.baostock.downloader import BaostockDownloader

def parse_args():
    parser = argparse.ArgumentParser(description='下载股票数据')
    parser.add_argument('--source', type=str, required=True, help='数据源，如：baostock')
    parser.add_argument('--start-date', type=str, help='开始日期，格式：YYYY-MM-DD')
    parser.add_argument('--end-date', type=str, help='结束日期，格式：YYYY-MM-DD')
    return parser.parse_args()

def main():
    args = parse_args()
    
    if args.source.lower() == 'baostock':
        downloader = BaostockDownloader()
        downloader.run_batch_download(
            start_date=args.start_date,
            end_date=args.end_date
        )
    else:
        logger.error(f'不支持的数据源: {args.source}')

if __name__ == '__main__':
    main()