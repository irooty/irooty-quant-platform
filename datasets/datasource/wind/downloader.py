"""
Wind数据下载模块
负责从Wind金融终端下载股票数据
"""

import time
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, Set
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from WindPy import w
from utils.logger import setup_logger
from utils.data_utils import save_parquet

class WindDownloader:
    def __init__(self, config: Dict[str, Any]):
        """
        初始化Wind数据下载器
        
        Args:
            config (Dict[str, Any]): 配置信息
        """
        self.config = config
        self.logger = setup_logger(__name__, config.get('logging', {}))
        self._init_wind()
        
        # 创建数据目录
        self.raw_dir = Path(config['paths']['raw_dir'])
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        
        # 下载配置
        self.batch_size = config['wind'].get('batch_size', 50)  # 默认每批50只股票
        self.retry_times = config['wind'].get('retry_times', 3)
        self.retry_interval = config['wind'].get('retry_interval', 60)
        self.max_workers = config['parallel'].get('max_workers', 4)
        self.max_batch_workers = min(self.max_workers, 2)  # 批次并行数限制
        
        # 数据配置
        self.fields = config['data']['fields']
        self.start_date = config['data']['start_date']
        self.end_date = config['data']['end_date']
        self.universe = config['data'].get('universe', 'A')
        
        # 下载进度跟踪
        self.downloaded_fields: Set[str] = set()
        self.failed_downloads: Dict[str, List[str]] = {}  # 记录失败的下载
    
    def _init_wind(self) -> None:
        """初始化Wind接口"""
        try:
            w.start()
            self.logger.info("Wind API 初始化成功")
        except Exception as e:
            self.logger.error(f"Wind API 初始化失败: {e}")
            raise
    
    def _check_wind_connection(self) -> bool:
        """检查Wind连接状态"""
        try:
            return w.isconnected()
        except Exception:
            return False
    
    def download_stock_list(self) -> List[str]:
        """
        下载股票列表
        
        Returns:
            List[str]: 股票代码列表
        """
        self.logger.info("开始下载股票列表")
        
        try:
            # 根据配置的股票范围获取股票列表
            if self.universe == 'A':
                # 获取A股股票列表
                data = w.wset("sectorconstituent", "date=20240130;sectorid=a001010100000000")
            else:
                self.logger.error(f"不支持的股票范围: {self.universe}")
                return []
            
            if data.ErrorCode != 0:
                self.logger.error(f"获取股票列表失败: {data.ErrorCode}")
                return []
            
            # Wind返回的数据结构：data.Data[1]是股票代码列表
            stock_list = list(data.Data[1])  # 股票代码在第二列
            
            # 如果配置了最大股票数量限制
            max_stocks = self.config['data'].get('max_stocks', 0)
            if max_stocks > 0:
                self.logger.info(f"限制下载股票数量为: {max_stocks}")
                # 为了保证每次获取的都是相同的股票，这里先排序
                stock_list.sort()
                stock_list = stock_list[:max_stocks]
            
            self.logger.info(f"成功获取 {len(stock_list)} 只股票")
            
            # 保存股票列表
            df = pd.DataFrame({'stock_code': stock_list})
            save_path = self.raw_dir / 'stock_list.parquet'
            save_parquet(df, save_path)
            self.logger.info(f"股票列表已保存到: {save_path}")
            
            return stock_list
            
        except Exception as e:
            self.logger.error(f"下载股票列表失败: {e}")
            return []
    
    def download_data(self) -> bool:
        """
        下载所有数据的主入口
        
        Returns:
            bool: 下载是否成功
        """
        try:
            # 1. 获取股票列表
            stock_list = self.download_stock_list()
            if not stock_list:
                raise ValueError("获取股票列表失败")
            
            # 2. 下载股票数据
            self.logger.info(f"开始下载数据: {len(self.fields)} 个字段, 日期范围: {self.start_date} - {self.end_date}")
            self.download_stock_data(stock_list, self.fields, self.start_date, self.end_date)
            
            return True
            
        except Exception as e:
            self.logger.error(f"数据下载失败: {e}")
            return False

    def _download_field_with_retry(self, stock_codes: List[str], field: str, 
                                 start_date: str, end_date: str) -> Tuple[str, pd.DataFrame]:
        """
        下载单个字段的多个股票数据，带重试机制
        
        Args:
            stock_codes (List[str]): 股票代码列表
            field (str): 字段名
            start_date (str): 开始日期
            end_date (str): 结束日期
            
        Returns:
            Tuple[str, pd.DataFrame]: (字段名, 数据DataFrame)
        """
        last_error = None
        for retry in range(self.retry_times):
            try:
                # 添加随机延迟，避免并发请求过多
                if retry > 0:
                    delay = np.random.uniform(1, self.retry_interval)
                    time.sleep(delay)
                
                data = w.wsd(stock_codes, field, start_date, end_date)
                if data.ErrorCode != 0:
                    raise Exception(f"ErrorCode: {data.ErrorCode}")
                
                # 验证数据完整性
                if not data.Data or not data.Times or not data.Codes:
                    raise Exception("数据结构不完整")
                
                # Wind API返回的数据结构处理
                values = []
                for stock_data in data.Data:
                    values.append(stock_data)
                
                # 转换为DataFrame并验证
                df = pd.DataFrame(values).T
                df.index = data.Times
                df.columns = data.Codes
                
                # 验证数据维度
                expected_shape = (len(data.Times), len(stock_codes))
                if df.shape != expected_shape:
                    raise Exception(f"数据维度不匹配: 期望 {expected_shape}, 实际 {df.shape}")
                
                self.logger.debug(f"字段 {field} 数据形状: {df.shape}")
                return field, df
                
            except Exception as e:
                last_error = e
                if retry < self.retry_times - 1:
                    self.logger.warning(f"下载字段 {field} 失败 (重试 {retry + 1}/{self.retry_times}): {e}")
                else:
                    self.logger.error(f"下载字段 {field} 最终失败: {e}")
                    # 记录失败信息
                    if field not in self.failed_downloads:
                        self.failed_downloads[field] = []
                    self.failed_downloads[field].extend(stock_codes)
        
        return field, pd.DataFrame()
    
    def _process_batch(self, batch_stocks: List[str], fields: List[str],
                      start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """
        处理一个批次的股票数据下载
        
        Args:
            batch_stocks (List[str]): 批次股票列表
            fields (List[str]): 字段列表
            start_date (str): 开始日期
            end_date (str): 结束日期
            
        Returns:
            Dict[str, pd.DataFrame]: 字段到数据框的映射
        """
        field_dfs = {}
        
        # 并行下载每个字段的数据
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 创建下载任务
            future_to_field = {
                executor.submit(
                    self._download_field_with_retry, 
                    batch_stocks, 
                    field, 
                    start_date, 
                    end_date
                ): field
                for field in fields if field not in self.downloaded_fields
            }
            
            # 处理完成的任务
            for future in as_completed(future_to_field):
                field = future_to_field[future]
                try:
                    field, df = future.result()
                    if not df.empty:
                        field_dfs[field] = df
                        self.downloaded_fields.add(field)
                except Exception as e:
                    self.logger.error(f"处理字段 {field} 失败: {e}")
        
        return field_dfs
    
    def download_stock_data(self, stock_list: List[str], fields: List[str],
                          start_date: str, end_date: str) -> None:
        """
        并行下载股票数据
        
        Args:
            stock_list (List[str]): 股票代码列表
            fields (List[str]): 字段列表
            start_date (str): 开始日期
            end_date (str): 结束日期
        """
        if not self._check_wind_connection():
            self.logger.error("Wind未连接")
            return
        
        self.logger.info(f"开始下载数据: {len(stock_list)} 只股票, {len(fields)} 个字段")
        
        # 重置下载状态
        self.downloaded_fields.clear()
        self.failed_downloads.clear()
        
        # 按批次处理股票
        batch_results = []
        for i in range(0, len(stock_list), self.batch_size):
            batch_stocks = stock_list[i:i + self.batch_size]
            self.logger.info(f"处理第 {i//self.batch_size + 1} 批次: {len(batch_stocks)} 只股票")
            
            # 处理当前批次
            field_dfs = self._process_batch(batch_stocks, fields, start_date, end_date)
            
            # 检查是否有成功下载的数据
            if not field_dfs:
                self.logger.error(f"批次 {i//self.batch_size + 1} 没有成功下载的数据")
                continue
            
            try:
                # 合并数据并保存
                batch_df = pd.concat(field_dfs.values(), axis=1, keys=field_dfs.keys())
                save_path = self.raw_dir / f"batch_{i//self.batch_size + 1}.parquet"
                save_parquet(batch_df, save_path)
                self.logger.info(f"批次 {i//self.batch_size + 1} 数据已保存到: {save_path}")
                batch_results.append(batch_df)
            except Exception as e:
                self.logger.error(f"保存批次 {i//self.batch_size + 1} 失败: {e}")
        
        # 处理失败的下载
        if self.failed_downloads:
            self.logger.warning("以下字段的部分股票数据下载失败:")
            for field, stocks in self.failed_downloads.items():
                self.logger.warning(f"{field}: {len(stocks)} 只股票")
            
            # 保存失败记录
            failed_path = self.raw_dir / "failed_downloads.parquet"
            pd.DataFrame(self.failed_downloads).to_parquet(failed_path)
            self.logger.info(f"失败记录已保存到: {failed_path}")
        
        # 合并所有批次数据（可选）
        if batch_results and len(batch_results) > 1:
            try:
                all_data = pd.concat(batch_results)
                save_path = self.raw_dir / "all_data.parquet"
                save_parquet(all_data, save_path)
                self.logger.info(f"所有数据已合并保存到: {save_path}")
            except Exception as e:
                self.logger.error(f"合并所有数据失败: {e}")
    
    def download_incremental_data(self, start_date: Optional[str] = None) -> None:
        """
        下载增量数据
        
        Args:
            start_date (Optional[str]): 增量数据起始日期，如果不指定则使用配置中的日期
        """
        if start_date is None:
            start_date = self.start_date
            
        end_date = time.strftime("%Y-%m-%d")
        
        # 获取最新的股票列表
        stock_list = self.download_stock_list()
        if stock_list:
            self.download_stock_data(stock_list, self.fields, start_date, end_date) 