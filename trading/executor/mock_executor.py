from .base_executor import BaseExecutor
from utils.logger import setup_logger

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

    def stop(self):
        """
        资源清理，关闭模拟执行器
        """
        logger.info("Mock executor stopped.")
