from .base_executor import BaseExecutor

class MockExecutor(BaseExecutor):
    def __init__(self):
        print("Mock executor started.")

    def buy(self, stock_code, volume):
        print(f"[MOCK] 模拟买入：{stock_code} 数量：{volume}")
        return "mock_order_id"

    def get_data_api(self):
        return None  # 可扩展为读取本地假数据

    def stop(self):
        print("Mock executor stopped.")
