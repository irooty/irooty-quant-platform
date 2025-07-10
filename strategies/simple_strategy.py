# 简单均线策略
from utils.logger import setup_logger
import pandas as pd

logger = setup_logger("trade")

def should_buy(stock_code, data_api):
    """
    简单均线策略：当前收盘价 > 5日均价即买入
    使用统一的get_klines接口获取DataFrame格式的K线数据
    
    Args:
        stock_code (str): 股票代码
        data_api: 数据API对象（支持get_klines方法）
        
    Returns:
        bool: 是否买入
        
    Note:
        - 策略逻辑：当前收盘价 > 5日均价时买入
        - 数据格式：使用统一的DataFrame格式，包含['date', 'open', 'close', 'high', 'low', 'volume', 'amount']列
        - 兼容性：支持不同数据源（xtquant、baostock、wind等）的统一接口
    """
    if data_api is None:
        logger.info(f"策略判定: {stock_code} mock场景直接买入")
        return True  # mock场景直接返回True
    
    try:
        # 使用统一的get_klines接口获取K线数据
        # 获取最近5个交易日的日线数据
        df = data_api.get_klines(stock_code, period='1d', count=5)
        
        if df.empty or len(df) < 5:
            logger.info(f"策略判定: {stock_code} 数据不足（{len(df)}条），不买入")
            return False
        
        # DataFrame操作：计算5日均价和当前收盘价
        close_prices = df['close'].tolist()
        avg_price = df['close'].mean()  # 使用pandas的mean方法
        current_close = close_prices[-1]  # 最新收盘价
        
        # 策略判断：当前收盘价 > 5日均价
        if current_close > avg_price:
            logger.info(f"策略判定: {stock_code} 收盘价{current_close:.2f} > 5日均价{avg_price:.2f}，买入")
            return True
        else:
            logger.info(f"策略判定: {stock_code} 收盘价{current_close:.2f} <= 5日均价{avg_price:.2f}，不买入")
            return False
            
    except Exception as e:
        logger.error(f"策略判定异常: {stock_code}，错误：{e}")
        return False
