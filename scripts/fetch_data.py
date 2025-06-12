#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import sys
import subprocess
from utils.path_utils import get_config_path

def parse_args():
    parser = argparse.ArgumentParser(description='数据下载工具')
    parser.add_argument('--config', type=str, default=get_config_path('data_source.yaml'), help='配置文件路径')
    parser.add_argument('--source', type=str, default='baostock', help='数据源 (baostock/wind)')
    parser.add_argument('--start-date', type=str, help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--convert', action='store_true', help='是否转换为Qlib格式')
    parser.add_argument('--output-dir', type=str, help='Qlib格式数据输出目录')
    return parser.parse_args()

def main():
    args = parse_args()
    # 构造命令行参数转发给 download.py
    cmd = [
        sys.executable, 'datasets/download.py',
        '--config', args.config,
        '--source', args.source
    ]
    if args.start_date:
        cmd += ['--start-date', args.start_date]
    if args.end_date:
        cmd += ['--end-date', args.end_date]
    if args.convert:
        cmd.append('--convert')
    if args.output_dir:
        cmd += ['--output-dir', args.output_dir]
    subprocess.run(cmd, check=True)

if __name__ == '__main__':
    main()