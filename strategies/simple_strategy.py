# 简单均线策略
from utils.logger import setup_logger
logger = setup_logger("trade")

def should_buy(stock_code, data_api):
    """
    简单均线策略：
    当前收盘价 > 5日均价即买入
    Args:
        stock_code (str): 股票代码
        data_api: 数据API对象
    Returns:
        bool: 是否买入
    """
    if data_api is None:
        logger.info(f"策略判定: {stock_code} mock场景直接买入")
        return True  # mock场景直接返回True
    kline = data_api.get_market_data(stock_code, '1d', count=5)
    if not kline or len(kline) < 5:
        logger.info(f"策略判定: {stock_code} 数据不足，不买入")
        return False
    close_prices = [x['close'] for x in kline]
    avg_price = sum(close_prices) / len(close_prices)
    if close_prices[-1] > avg_price:
        logger.info(f"策略判定: {stock_code} 收盘价{close_prices[-1]} > 5日均价{avg_price:.2f}，买入")
        return True
    else:
        logger.info(f"策略判定: {stock_code} 收盘价{close_prices[-1]} <= 5日均价{avg_price:.2f}，不买入")
        return False
