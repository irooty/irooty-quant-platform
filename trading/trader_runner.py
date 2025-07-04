# 交易调度模块：根据配置动态加载策略函数和执行器类，统一自动化下单入口

import pandas as pd
from utils.object_loader import ObjectLoader  # 工具类，支持类/函数动态加载
from utils.path_utils import load_config  # 统一配置加载
from utils.logger import setup_logger

logger = setup_logger("trade")

def run():
    """
    自动交易主入口：
    步骤：
        1. 加载交易配置（执行器、策略、参数等）
        2. 动态加载并实例化执行器类
        3. 动态加载策略函数
        4. 读取股票列表，依次判定是否买入并下单
        5. 完成后资源释放
    Returns:
        None
    """
    logger.info("自动交易流程启动")
    try:
        # 1. 加载交易配置
        config = load_config("trading.yaml")
        logger.info("配置加载成功")

        # 2. 动态加载并实例化交易执行器
        executor_cfg = config.get("executor", {})
        ExecutorClass = ObjectLoader.load(
            executor_cfg["module"],
            executor_cfg["class"]
        )
        executor = ExecutorClass()

        # 3. 动态加载策略函数
        strategy_cfg = config.get("strategy", {})
        strategy_func = ObjectLoader.load(
            strategy_cfg["module"],
            strategy_cfg["function"]
        )

        # 4. 读取自选股票列表
        df = pd.read_csv(config["watchlist_path"])
        default_volume = config.get("volume", 100)

        # 5. 遍历股票，应用策略，满足则下单
        for idx, row in df.iterrows():
            stock_code = row["stock_code"]
            volume = row["volume"] if "volume" in row and not pd.isna(row["volume"]) else default_volume
            try:
                if strategy_func(stock_code, executor.get_data_api()):
                    order_id = executor.buy(stock_code, volume)
                    logger.info(f"已买入: {stock_code} 数量: {volume} 订单号: {order_id}")
                else:
                    logger.info(f"未买入: {stock_code}")
            except Exception as e:
                logger.error(f"处理股票 {stock_code} 时出错: {e}")

        # 6. 资源清理
        executor.stop()
        logger.info("自动交易流程结束")
    except Exception as e:
        logger.error(f"自动交易流程异常终止: {e}")
