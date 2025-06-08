import qlib
from qlib.config import REG_CN
from utils.path_utils import get_qlib_data_dir

qlib_data_dir = get_qlib_data_dir()  # 自动获得绝对路径
def init_qlib(local=True):
    """
    初始化 Qlib 数据环境
    :param local: 是否使用本地数据（默认True，本地 ~/.qlib/qlib_data/cn_data 目录）
    """
    if local:
        # 使用本地数据（建议提前用 qlib.run.init 命令初始化好数据）
        qlib.init(provider_uri=qlib_data_dir, region=REG_CN)
        print("Qlib 本地数据已初始化")
    else:
        # 使用远程（比如官方云端，部分功能和速度可能有限制）
        qlib.init()
        print("Qlib 远程初始化完成")
