# 简单均线策略
def should_buy(stock_code, data_api):
    """
    当前收盘价 > 5日均价即买入
    """
    if data_api is None:
        return True  # mock场景直接返回True
    kline = data_api.get_market_data(stock_code, '1d', count=5)
    if not kline or len(kline) < 5:
        return False
    close_prices = [x['close'] for x in kline]
    avg_price = sum(close_prices) / len(close_prices)
    return close_prices[-1] > avg_price
