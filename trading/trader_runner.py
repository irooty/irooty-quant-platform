# 交易调度模块：根据配置动态加载策略函数和执行器类，统一自动化下单入口

import pandas as pd
import yaml
from utils.object_loader import ObjectLoader  # 工具类，支持类/函数动态加载

def run():
    """
    自动交易主入口：
    1. 加载交易配置（执行器、策略、参数等）
    2. 动态加载并实例化执行器类
    3. 动态加载策略函数
    4. 读取股票列表，依次判定是否买入并下单
    5. 完成后资源释放
    """
    # 加载配置
    with open("config/trading.yaml", "r") as f:
        config = yaml.safe_load(f)

    # 动态加载并实例化交易执行器
    executor_cfg = config.get("executor", {})
    ExecutorClass = ObjectLoader.load(
        executor_cfg["module"],
        executor_cfg["class"]
    )
    executor = ExecutorClass()

    # 动态加载策略函数
    strategy_cfg = config.get("strategy", {})
    strategy_func = ObjectLoader.load(
        strategy_cfg["module"],
        strategy_cfg["function"]
    )

    # 读取自选股票列表
    df = pd.read_csv(config["watchlist_path"])
    volume = config.get("volume", 100)

    # 遍历股票，应用策略，满足则下单
    for stock_code in df["stock_code"]:
        if strategy_func(stock_code, executor.get_data_api()):
            executor.buy(stock_code, volume)

    # 资源清理
    executor.stop()
