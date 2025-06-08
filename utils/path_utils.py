import os
import yaml

def get_qlib_data_dir(config_path="config/paths.yaml"):
    """
    读取 Qlib 数据目录配置，并将相对路径转换为绝对路径。
    确保无论当前脚本在哪个目录执行，都能正确定位数据。
    """
    # 获取项目根目录的绝对路径（假定配置文件在项目内）
    project_root = os.path.dirname(os.path.abspath(__file__))
    # 解析配置
    config_abspath = os.path.join(project_root, "..", config_path)  # 脚本可能在子目录
    config_abspath = os.path.abspath(config_abspath)
    with open(config_abspath, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    # 解析配置的目录字段，若未配置则用 ~/.qlib/qlib_data/cn_data 作为默认
    qlib_data_dir = config.get("qlib_data_dir", "~/.qlib/qlib_data/cn_data")
    # 转为绝对路径（相对于项目根目录）
    qlib_data_abspath = os.path.abspath(os.path.join(project_root, "..", qlib_data_dir))
    return qlib_data_abspath

# 使用举例
if __name__ == "__main__":
    print(get_qlib_data_dir())
