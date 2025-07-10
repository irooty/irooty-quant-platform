# 策略基类

def always_buy(stock_code, data_api):
    """
    始终买入策略：无条件返回True。
    用于测试或需要全部买入的场景。
    Args:
        stock_code (str): 股票代码
        data_api: 数据API对象
    Returns:
        bool: 是否买入（始终为True）
    """
    return True


def never_buy(stock_code, data_api):
    """
    始终不买入策略：无条件返回False。
    用于测试或无需策略下单的场景。
    Args:
        stock_code (str): 股票代码
        data_api: 数据API对象
    Returns:
        bool: 是否买入（始终为False）
    """
    return False