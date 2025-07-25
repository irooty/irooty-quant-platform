# coding:utf-8
import time, datetime, sys
from xtquant import xtdata
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from xtquant import xtconstant
from .base_executor import BaseExecutor
import pandas as pd
from utils.logger import setup_logger

logger = setup_logger("trade")

class MyXtQuantTraderCallback(XtQuantTraderCallback):
    """
    自定义XtQuantTrader回调类。
    用于处理交易相关的异步事件（如委托、成交、报错等），便于调试和日志追踪。
    """
    def on_disconnected(self):
        """连接断开回调"""
        print(datetime.datetime.now(), '连接断开回调')
    def on_stock_order(self, order):
        """委托回报推送回调"""
        print(datetime.datetime.now(), '委托回调 投资备注', order.order_remark)
    def on_stock_trade(self, trade):
        """成交变动推送回调"""
        print(datetime.datetime.now(), '成交回调', trade.order_remark, f"委托方向(48买 49卖) {trade.offset_flag} 成交价格 {trade.traded_price} 成交数量 {trade.traded_volume}")
    def on_order_error(self, order_error):
        """委托失败推送回调"""
        print(f"委托报错回调 {order_error.order_remark} {order_error.error_msg}")
    def on_cancel_error(self, cancel_error):
        """撤单失败推送回调"""
        print(datetime.datetime.now(), sys._getframe().f_code.co_name)
    def on_order_stock_async_response(self, response):
        """异步下单回报推送回调"""
        print(f"异步委托回调 投资备注: {response.order_remark}")
    def on_cancel_order_stock_async_response(self, response):
        """异步撤单回报推送回调"""
        print(datetime.datetime.now(), sys._getframe().f_code.co_name)
    def on_account_status(self, status):
        """账号状态变动回调"""
        print(datetime.datetime.now(), sys._getframe().f_code.co_name)

class QMTExecutor(BaseExecutor):
    """
    QMT交易执行器（xtquant原生下单实现）
    封装了xtquant的交易对象初始化、行情获取、资金查询、下单等自动化流程。
    用于自动化批量下单、策略交易等场景。
    """
    def __init__(self):
        """
        初始化QMTExecutor：
        1. 指定QMT客户端路径、账号、session_id（建议后续通过配置传入）
        2. 创建XtQuantTrader对象，注册回调，启动线程，连接交易服务器
        3. 创建证券账号对象并订阅，确保后续可正常下单
        """
        # TODO: 路径、账号建议后续通过配置传入
        self.path = r'D:\software\迅投极速交易终端睿智融科版\userdata'  # QMT客户端userdata路径
        self.account_id = '2031065'  # 资金账号
        self.session_id = int(time.time())  # session_id需唯一
        self.xt_trader = XtQuantTrader(self.path, self.session_id)
        self.callback = MyXtQuantTraderCallback()
        self.xt_trader.register_callback(self.callback)
        self.xt_trader.start()
        connect_result = self.xt_trader.connect()
        logger.info(f"建立交易连接，返回0表示连接成功: {connect_result}")
        self.acc = StockAccount(self.account_id, 'STOCK')
        subscribe_result = self.xt_trader.subscribe(self.acc)
        logger.info(f"对交易回调进行订阅，返回0表示订阅成功: {subscribe_result}")

    def buy(self, stock_code, volume):
        """
        买入股票（自动获取行情和资金，按100股整数倍下单）
        Args:
            stock_code (str): 股票代码（如 '600000.SH'）
            volume (int/float): 期望买入股数（会根据资金和100股整数倍自动调整）
        Returns:
            str: 异步下单返回的订单ID（如资金不足则返回None）
        """
        # 获取最新行情
        full_tick = xtdata.get_full_tick([stock_code])
        current_price = full_tick[stock_code]['lastPrice']
        # 获取资金
        account_info = self.xt_trader.query_stock_asset(self.acc)
        available_cash = account_info.m_dCash
        # 计算买入金额和股数（按资金和100股整数倍自动调整）
        buy_amount = min(volume * current_price, available_cash)
        buy_vol = int(buy_amount / current_price / 100) * 100
        if buy_vol <= 0:
            logger.warning(f"可用资金不足，无法买入: {stock_code}")
            return None
        # 下单（异步委托，限价单，投资备注为strategy_name+股票代码）
        order_id = self.xt_trader.order_stock_async(
            self.acc, stock_code, xtconstant.STOCK_BUY, buy_vol, xtconstant.FIX_PRICE, current_price,
            'strategy_name', stock_code
        )
        logger.info(f"[QMT] 买入 {stock_code} {buy_vol} 股，订单ID：{order_id}")
        return order_id

    def get_data_api(self):
        """
        获取行情数据API（直接返回xtdata模块）
        Returns:
            xtdata: xtquant行情数据API
        """
        return xtdata

    def stop(self):
        """
        停止执行器，释放交易对象资源
        """
        self.xt_trader.stop()
        logger.info("QMT executor stopped.")
