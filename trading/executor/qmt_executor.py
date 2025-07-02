from xtquant.xtdata import XtDataApi
from xtquant.xttrader import XtTrader
from .base_executor import BaseExecutor

class QMTExecutor(BaseExecutor):
    def __init__(self):
        self.data_api = XtDataApi()
        self.data_api.start()
        self.trader = XtTrader()
        self.trader.start()

    def buy(self, stock_code, volume):
        order_id = self.trader.place_order(
            stock_code=stock_code,
            price_type=4,
            side=1,
            order_volume=volume,
            position_effect=1
        )
        print(f"[QMT] 买入 {stock_code} {volume} 股，订单ID：{order_id}")
        return order_id

    def get_data_api(self):
        return self.data_api

    def stop(self):
        self.trader.stop()
        self.data_api.stop()
