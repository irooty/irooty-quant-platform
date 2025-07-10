from xtquant.xtdata import XtDataApi
from xtquant.xttrader import XtTrader
from .base_executor import BaseExecutor
import pandas as pd
from utils.logger import setup_logger

logger = setup_logger("trade")

class QMTExecutor(BaseExecutor):
    """
    QMT交易执行器
    基于xtquant实现，封装了数据获取和交易下单功能
    """
    
    def __init__(self):
        self.data_api = XtDataApi()
        self.data_api.start()
        self.trader = XtTrader()
        self.trader.start()
        logger.info("QMT executor started.")

    def buy(self, stock_code, volume):
        """
        买入股票
        Args:
            stock_code: 股票代码
            volume: 买入数量
        Returns:
            str: 订单号
        """
        order_id = self.trader.place_order(
            stock_code=stock_code,
            price_type=4,
            side=1,
            order_volume=volume,
            position_effect=1
        )
        logger.info(f"[QMT] 买入 {stock_code} {volume} 股，订单ID：{order_id}")
        return order_id

    def get_data_api(self):
        """
        获取数据API对象
        Returns:
            XtDataApi: xtquant数据API对象
        """
        return self.data_api

    def get_klines(self, stock_code: str, period: str = '1d', count: int = None, 
                   start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取K线数据（xtquant实现）
        将xtquant的API差异封装在内部，返回统一的DataFrame格式
        
        Args:
            stock_code: 股票代码
            period: 数据周期 ('1d', '1min', '5min', '15min', '30min', '1h', '1w', '1m', '1q', '1y')
            count: 获取条数
            start_date: 开始日期 (YYYY-MM-DD格式)
            end_date: 结束日期 (YYYY-MM-DD格式)
            
        Returns:
            pd.DataFrame: 统一格式的K线数据
                columns: ['date', 'open', 'close', 'high', 'low', 'volume', 'amount']
                date列: YYYY-MM-DD格式字符串
                numeric列: float类型
                按日期升序排列
        """
        try:
            # 根据参数选择不同的API调用方式
            if count is not None:
                # 按条数获取
                raw_data = self.data_api.get_market_data(stock_code, period, count=count)
            else:
                # 按日期范围获取
                if start_date and end_date:
                    # 转换为xtquant需要的格式
                    start_str = start_date.replace('-', '')
                    end_str = end_date.replace('-', '')
                    raw_data = self.data_api.get_market_data(stock_code, period, 
                                                           start_time=start_str, end_time=end_str)
                else:
                    # 默认获取最近20条数据
                    raw_data = self.data_api.get_market_data(stock_code, period, count=20)
            
            # 转换为DataFrame
            if isinstance(raw_data, dict):
                # 如果是字典格式，提取数据
                df = pd.DataFrame(raw_data)
            elif isinstance(raw_data, list):
                # 如果是列表格式
                df = pd.DataFrame(raw_data)
            else:
                # 其他格式，尝试直接转换
                df = pd.DataFrame(raw_data)
            
            if df.empty:
                logger.warning(f"获取K线数据为空：{stock_code}")
                return pd.DataFrame()
            
            # 统一列名
            column_mapping = {
                'time': 'date',
                'datetime': 'date',
                'open_price': 'open',
                'close_price': 'close',
                'high_price': 'high',
                'low_price': 'low',
                'vol': 'volume',
                'volume': 'volume',
                'amount': 'amount'
            }
            
            for old_col, new_col in column_mapping.items():
                if old_col in df.columns and new_col not in df.columns:
                    df.rename(columns={old_col: new_col}, inplace=True)
            
            # 确保必要的列存在
            required_cols = ['date', 'open', 'close', 'high', 'low', 'volume']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                logger.warning(f"K线数据缺少必要列：{missing_cols}，股票：{stock_code}")
                return pd.DataFrame()
            
            # 数据类型转换
            numeric_cols = ['open', 'close', 'high', 'low', 'volume']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 处理amount列（如果存在）
            if 'amount' in df.columns:
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
            else:
                # 如果没有amount列，根据volume和价格计算
                df['amount'] = df['volume'] * (df['open'] + df['close']) / 2
            
            # 统一date列格式
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            
            # 按日期排序
            df = df.sort_values('date')
            
            # 选择并排序列
            final_cols = ['date', 'open', 'close', 'high', 'low', 'volume', 'amount']
            df = df[final_cols]
            
            logger.info(f"[QMT] 获取K线数据成功：{stock_code} {len(df)}条")
            return df
            
        except Exception as e:
            logger.error(f"获取K线数据失败：{stock_code}，错误：{e}")
            return pd.DataFrame()

    def stop(self):
        """
        停止执行器，释放资源
        """
        self.trader.stop()
        self.data_api.stop()
        logger.info("QMT executor stopped.")
