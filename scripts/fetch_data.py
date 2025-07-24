#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import fire
from utils.path_utils import get_config_path

def main(
    provider,  # 金融数据提供方，如 baostock
    config: str = get_config_path('market_provider.yaml'),  # 配置文件路径
    start_date: str = None,  # 开始日期，格式：YYYY-MM-DD
    end_date: str = None,    # 结束日期，格式：YYYY-MM-DD
    convert: bool = False,   # 是否转换为Qlib格式
    stock_codes: str = None,  # 要下载的股票列表，支持逗号分隔字符串或文件路径（如.txt，每行一个或逗号分隔）
    interval: str = '1d'     # 数据类型，支持1min、5min、15min、30min、1h、1d、1w、1m、1q、1y、dividend，默认1d表示日数据
):
    """
    股票数据下载工具

    参数说明:
      --provider     金融数据提供方（如 baostock）【必填】
      --config       配置文件路径，默认 market_provider.yaml
      --start-date   开始日期，格式：YYYY-MM-DD
      --end-date     结束日期，格式：YYYY-MM-DD
      --convert      是否转换为Qlib格式，布尔值
      --stock-codes  要下载的股票列表，支持逗号分隔字符串（如 sh.600000,sz.000001），
                     或文件路径（如 codes.txt，每行一个或逗号分隔）
      --interval     数据类型，支持1min、5min、15min、30min、1h、1d、1w、1m、1q、1y、dividend，默认1d表示日数据
    """
    # 添加项目根目录到Python路径
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)

    # 构造命令行参数转发给 download.py
    cmd = [
        sys.executable, 'datasets/download.py',
        '--config', config,
        '--provider', provider
    ]
    if start_date:
        cmd += ['--start-date', start_date]
    if end_date:
        cmd += ['--end-date', end_date]
    if convert:
        cmd.append('--convert')
    if stock_codes:
        cmd += ['--stock-codes', stock_codes]
    if interval:
        cmd += ['--interval', interval]
    
    import subprocess
    subprocess.run(cmd, check=True)

if __name__ == '__main__':
    fire.Fire(main)