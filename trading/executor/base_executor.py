from abc import ABC, abstractmethod
import pandas as pd
from typing import Optional

class BaseExecutor(ABC):
    """
    交易执行器基类
    定义了统一的交易和数据获取接口
    """
    
    @abstractmethod
    def buy(self, stock_code: str, volume: int) -> str:
        """
        买入股票
        Args:
            stock_code: 股票代码
            volume: 买入数量
        Returns:
            str: 订单号
        """
        pass

    @abstractmethod
    def stop(self):
        """
        停止执行器，释放资源
        """
        pass

    @abstractmethod
    def get_data_api(self):
        """
        获取数据API对象
        Returns:
            数据API对象
        """
        pass

    def get_klines(self, stock_code: str, period: str = '1d', count: Optional[int] = None, 
                   start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        """
        统一的K线数据获取接口（可选实现）。
        子类可根据需要重载本方法。
        默认抛出NotImplementedError。
        
        Args:
            stock_code: 股票代码
            period: 数据周期 ('1d', '1min', '5min', '15min', '30min', '1h', '1w', '1m', '1q', '1y')
            count: 获取条数（与start_date/end_date二选一）
            start_date: 开始日期 (YYYY-MM-DD格式)
            end_date: 结束日期 (YYYY-MM-DD格式)
            
        Returns:
            pd.DataFrame: 统一格式的K线数据
                columns: ['date', 'open', 'close', 'high', 'low', 'volume', 'amount']
                date列: YYYY-MM-DD格式字符串
                numeric列: float类型
                按日期升序排列
                
        Raises:
            NotImplementedError: 默认抛出，子类可根据需要重载
        """
        raise NotImplementedError("该执行器未实现get_klines方法")
