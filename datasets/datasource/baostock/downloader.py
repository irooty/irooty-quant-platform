#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import baostock as bs
import pandas as pd
from datetime import datetime, timedelta
from loguru import logger
import yaml
from pathlib import Path
from utils.path_utils import get_config_path

class BaostockDownloader:
    """Baostock数据下载器"""
    
    def __init__(self, config_path=None):
        """初始化下载器
        
        Args:
            config_path: 配置文件路径，默认为None
        """
        self.bs = bs
        # 登录系统
        self.login()
        self.config = self._load_config(config_path)
        
    def _load_config(self, config_path):
        """加载配置文件"""
        if config_path is None:
            config_path = get_config_path('data_source.yaml')
            
        # 默认配置
        default_config = {
            'data_path': '../data/raw/baostock',
            'start_date': '2010-01-01',
            'end_date': datetime.now().strftime('%Y-%m-%d'),
            'fields': {
                'daily': 'date,code,open,high,low,close,volume,amount,adjustflag,turn,tradestatus,pctChg,peTTM,pbMRQ,psTTM,pcfNcfTTM',
                'dividend': 'date,code,dividPreNoticeDate,dividAgmPumDate,dividPlanAnnounceDate,dividPlanDate,dividRegistDate,dividOperateDate,dividPayDate,dividCashPsBeforeTax,dividCashPsAfterTax,dividStocksPs,dividCashStock,dividReserveToStockPs',
            },
            'stock_list_fields': 'code,code_name,industry,industry_classification'
        }
            
        if not os.path.exists(config_path):
            # 保存默认配置
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, allow_unicode=True)
            config = default_config
        else:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                # 合并默认配置和用户配置
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                    elif isinstance(value, dict) and isinstance(config[key], dict):
                        # 递归合并字典
                        for sub_key, sub_value in value.items():
                            if sub_key not in config[key]:
                                config[key][sub_key] = sub_value
                
        return config

    def login(self):
        """登录系统"""
        lg = self.bs.login()
        if lg.error_code != '0':
            logger.error(f'登录失败: {lg.error_msg}')
            raise Exception(f'Baostock登录失败: {lg.error_msg}')
        logger.info('Baostock登录成功')

    def logout(self):
        """登出系统"""
        self.bs.logout()
        logger.info('Baostock登出成功')

    def download_stock_list(self):
        """下载股票列表"""
        logger.info('开始下载股票列表...')
        stock_rs = self.bs.query_stock_basic()
        stock_df = self._process_result(stock_rs)
        
        # 保存数据
        save_path = os.path.join(self.config['data_path'], 'stock_list')
        os.makedirs(save_path, exist_ok=True)
        file_path = os.path.join(save_path, f'stock_list_{datetime.now().strftime("%Y%m%d")}.csv')
        stock_df.to_csv(file_path, index=False, encoding='utf-8')
        logger.info(f'股票列表已保存至: {file_path}')
        return stock_df

    def download_daily_data(self, stock_code, start_date=None, end_date=None):
        """下载单个股票的日线数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期，格式：YYYY-MM-DD，优先级：参数 > 配置文件 > 默认值
            end_date: 结束日期，格式：YYYY-MM-DD，优先级：参数 > 配置文件 > 当前日期
        """
        # 获取开始日期，优先级：参数 > 配置文件 > 默认值
        start_date = start_date or self.config.get('start_date', '2010-01-01')
        
        # 获取结束日期，优先级：参数 > 配置文件 > 当前日期
        end_date = end_date or self.config.get('end_date') or datetime.now().strftime('%Y-%m-%d')
        
        # 获取字段配置，使用默认值
        fields = self.config.get('fields', {}).get('daily', 'date,code,open,high,low,close,volume,amount,adjustflag,turn,tradestatus,pctChg,peTTM,pbMRQ,psTTM,pcfNcfTTM')
        
        logger.info(f'下载 {stock_code} 的日线数据 ({start_date} to {end_date})')
        rs = self.bs.query_history_k_data_plus(
            code=stock_code,
            fields=fields,
            start_date=start_date,
            end_date=end_date,
            frequency='d',
            adjustflag='3'  # 3: 后复权
        )
        
        df = self._process_result(rs)
        if not df.empty:
            # 保存数据
            save_path = os.path.join(self.config.get('data_path', '../data/raw/baostock'), 'daily', stock_code)
            os.makedirs(save_path, exist_ok=True)
            file_path = os.path.join(save_path, f'{stock_code}_daily.csv')
            df.to_csv(file_path, index=False, encoding='utf-8')
            logger.info(f'日线数据已保存至: {file_path}')
        return df

    def download_dividend_data(self, stock_code, start_date=None, end_date=None):
        """下载分红数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期，格式：YYYY-MM-DD，优先级：参数 > 配置文件 > 默认值
            end_date: 结束日期，格式：YYYY-MM-DD，优先级：参数 > 配置文件 > 当前日期
        """
        # 获取开始日期，优先级：参数 > 配置文件 > 默认值
        start_date = start_date or self.config.get('start_date', '2010-01-01')
        
        # 获取结束日期，优先级：参数 > 配置文件 > 当前日期
        end_date = end_date or self.config.get('end_date') or datetime.now().strftime('%Y-%m-%d')
        
        # 获取字段配置，使用默认值
        fields = self.config.get('fields', {}).get('dividend', 'date,code,dividPreNoticeDate,dividAgmPumDate,dividPlanAnnounceDate,dividPlanDate,dividRegistDate,dividOperateDate,dividPayDate,dividCashPsBeforeTax,dividCashPsAfterTax,dividStocksPs,dividCashStock,dividReserveToStockPs')
        
        logger.info(f'下载 {stock_code} 的分红数据 ({start_date} to {end_date})')
        rs = self.bs.query_dividend_data(
            code=stock_code,
            year=start_date.split('-')[0],
            yearType='report'
        )
        
        df = self._process_result(rs)
        if not df.empty:
            # 保存数据
            save_path = os.path.join(self.config.get('data_path', '../data/raw/baostock'), 'dividend', stock_code)
            os.makedirs(save_path, exist_ok=True)
            file_path = os.path.join(save_path, f'{stock_code}_dividend.csv')
            df.to_csv(file_path, index=False, encoding='utf-8')
            logger.info(f'分红数据已保存至: {file_path}')
        return df

    def _process_result(self, rs):
        """处理查询结果"""
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())
        if data_list:
            df = pd.DataFrame(data_list, columns=rs.fields)
        else:
            df = pd.DataFrame()
        return df

    def batch_download_daily_data(self, stock_codes=None, start_date=None, end_date=None):
        """批量下载日线数据
        
        Args:
            stock_codes: 股票代码列表，如果为None则下载所有股票
            start_date: 开始日期，格式：YYYY-MM-DD，如果为None则使用配置文件中的默认值
            end_date: 结束日期，格式：YYYY-MM-DD，如果为None则使用配置文件中的默认值
        """
        if stock_codes is None:
            # 如果未指定股票代码，则下载所有股票
            stock_df = self.download_stock_list()
            stock_codes = stock_df['code'].tolist()

        total = len(stock_codes)
        for idx, code in enumerate(stock_codes, 1):
            logger.info(f'进度: [{idx}/{total}] 处理: {code}')
            try:
                self.download_daily_data(code, start_date, end_date)
                self.download_dividend_data(code, start_date, end_date)
            except Exception as e:
                logger.error(f'处理 {code} 时出错: {str(e)}') 