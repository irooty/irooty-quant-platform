from .base_executor import BaseExecutor
from utils.logger import setup_logger
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

logger = setup_logger("trade")

class MockExecutor(BaseExecutor):
    """
    模拟交易执行器，实现BaseExecutor接口
    用于测试和开发环境，不实际下单
    """
    def __init__(self):
        logger.info("Mock executor started.")

    def buy(self, stock_code, volume):
        """
        模拟买入操作
        Args:
            stock_code (str): 股票代码
            volume (int): 买入数量
        Returns:
            str: 模拟订单号
        """
        logger.info(f"[MOCK] 模拟买入：{stock_code} 数量：{volume}")
        return "mock_order_id"

    def get_data_api(self):
        """
        获取数据API（mock场景返回None或假数据）
        Returns:
            None
        """
        return None  # 可扩展为读取本地假数据

    def get_klines(self, stock_code: str, period: str = '1d', count: int = None, 
                   start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        模拟K线数据获取
        生成模拟的K线数据用于策略测试
        
        Args:
            stock_code: 股票代码
            period: 数据周期
            count: 获取条数
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            pd.DataFrame: 模拟的K线数据
        """
        # 生成模拟数据
        if count is None:
            count = 20  # 默认生成20条数据
            
        # 生成日期序列
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=count)
        dates = pd.date_range(start=start_dt, end=end_dt, freq='D')
        
        # 生成模拟价格数据（随机游走）
        np.random.seed(hash(stock_code) % 1000)  # 根据股票代码生成固定种子
        base_price = 10.0 + np.random.random() * 20  # 基础价格10-30元
        price_changes = np.random.normal(0, 0.02, count)  # 每日价格变化
        prices = [base_price]
        
        for change in price_changes[1:]:
            new_price = prices[-1] * (1 + change)
            prices.append(max(new_price, 0.1))  # 确保价格不为负
        
        # 生成OHLC数据
        data = []
        for i, date in enumerate(dates):
            price = prices[i]
            # 生成当日OHLC
            daily_change = np.random.normal(0, 0.01)
            open_price = price * (1 + daily_change)
            close_price = price
            high_price = max(open_price, close_price) * (1 + abs(np.random.normal(0, 0.005)))
            low_price = min(open_price, close_price) * (1 - abs(np.random.normal(0, 0.005)))
            volume = int(np.random.uniform(100000, 1000000))
            amount = volume * (open_price + close_price) / 2
            
            data.append({
                'date': date.strftime('%Y-%m-%d'),
                'open': round(open_price, 2),
                'close': round(close_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'volume': volume,
                'amount': round(amount, 2)
            })
        
        df = pd.DataFrame(data)
        logger.info(f"[MOCK] 生成模拟K线数据：{stock_code} {len(df)}条")
        return df

    def stop(self):
        """
        资源清理，关闭模拟执行器
        """
        logger.info("Mock executor stopped.")
