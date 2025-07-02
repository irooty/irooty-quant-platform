# IRoot Quant Platform 项目简介

这是一个模块化的 Python 量化交易平台项目结构，适合进行策略研究、数据处理、回测分析以及模型集成。你可以基于该结构快速开展自己的量化研究或实盘部署。

## 项目目录结构

```
quant-platform/
├── data/                       # 数据存储
│   ├── raw/                   # 原始行情或财务数据
│   ├── processed/             # 清洗后的数据
│   └── external/              # 宏观或外部数据
│
├── datasets/                  # 数据加载与预处理模块
│   ├── download.py            # 下载数据逻辑
│   ├── preprocess.py          # 数据清洗与特征工程
│   └── loader.py              # 数据加载类/函数
│
├── strategies/                # 策略模块
│   ├── base_strategy.py       # 策略基类
│   ├── mean_reversion.py      # 均值回归策略
│   └── momentum.py            # 动量策略
│
├── backtest/                  # 回测系统
│   ├── engine.py              # 回测引擎主逻辑
│   ├── metrics.py             # 绩效指标计算
│   └── run_backtest.py        # 回测运行入口
│
├── analysis/                  # 回测结果分析
│   ├── performance.py         # 绩效分析图表
│   ├── risk_analysis.py       # 风险分析逻辑
│   └── report_generator.py    # 报告生成
│
├── models/                    # ML/DL 模型模块
│   ├── model_base.py          # 模型基类
│   ├── xgboost_alpha.py       # XGBoost 股票评分
│   ├── trading.yaml           # 自动交易参数（如股数、策略类型）
│   └── lstm_timing.py         # LSTM 市场择时
│
├── trading/                   # 自动实盘交易模块
│   ├── executor/                   # 交易执行器目录，不同交易接口实现不同执行器
│   │   ├── base_executor.py        # 抽象基类接口
│   │   ├── qmt_executor.py         # 迅投实现
│   │   └── mock_executor.py        # 示例：本地打印模拟下单
│   ├── simple_strategy.py          # 示例策略（未来也可以抽象）
│   └── trader_runner.py            # 统一策略执行调度（加载执行器 + 策略）
│ 
├── config/                    # 配置文件
│   ├── paths.yaml             # 路径配置
│   ├── strategy.yaml          # 策略参数
│   └── backtest.yaml          # 回测参数
│
├── logs/                      # 日志输出目录
│
├── utils/                     # 工具库
│   ├── logger.py              # 日志封装
│   ├── date_utils.py          # 时间工具
│   └── decorators.py          # 装饰器函数
│
├── notebooks/                 # Jupyter 分析笔记本
│   └── exploratory_analysis.ipynb
│
├── scripts/                   # 常用脚本入口
│   ├── fetch_data.py          # 数据更新脚本
│   ├── daily_run.py           # 每日任务调度
│   ├── deploy_bot.py          # 结果推送脚本
│   └── run_trade.py           # 统一交易入口脚本（可以定时调度）
│
├── requirements.txt           # Python 依赖列表
├── main.py                    # 项目主入口
├── .gitignore                 # Git 忽略规则
└── README.md                  # 当前项目说明文件
```

## 使用建议

- 所有路径建议统一通过 `config/paths.yaml` 进行配置；
- 推荐使用虚拟环境（如 `venv` 或 `conda`）管理依赖；
- 各模块遵循单一职责原则，便于测试与维护；
- 可集成 Qlib、Backtrader、Jupyter 等生态工具扩展功能。

欢迎按需修改、扩展和复用本目录结构。

## 🔧 使用说明：基于虚拟环境（venv）

以下为 `irooty-quant-platform` 项目使用步骤，推荐使用 Python 内置的 `venv` 虚拟环境方式管理依赖：

## 环境要求

- **Python 版本**：建议 3.11.x
- 依赖包安装方法见 requirements.txt

### 推荐使用虚拟环境，并指定 Python 3.11 版本：

---

### 1. 克隆项目 / 解压

```bash
# 解压 zip 包后进入项目目录
cd irooty-quant-platform
```

---

### 2. 创建虚拟环境

```bash
# 默认使用当前 Python 版本创建虚拟环境（推荐命名为 .venv）
python -m venv .venv
# 指定 Python 3.11 版本
python3.11 -m venv .venv
# 或者（Windows 下用 py 启动器）
py -3.11 -m venv .venv
```

---

### 3. 激活虚拟环境

- Windows:
```bash
.venv\Scripts\activate
```

- macOS / Linux:
```bash
source .venv/bin/activate
```

---

### 4. 安装依赖包

```bash
pip install --upgrade pip
# pip install -r requirements.txt
# pip install .
# 可编辑安装
pip install -e .
```

---

### 5. 下载 Qlib 测试数据（首次运行）

```bash
python -m qlib.run.get_data qlib_data --target_dir ./data/qlib/cn_data --region cn
```

---

### 6. 运行回测示例

```bash
python backtest/run_qlib_backtest.py
```

你将看到包含策略回测绩效指标（如年化收益率、夏普比率等）的输出结果。

---

### 7. 统一的数据获取入口

```
irooty-quant-platform/
├── datasets/                 # 数据集处理模块
│   ├── download.py           # 统一的数据下载接口，定义通用的数据获取流程
│   ├── preprocess.py         # 数据预处理模块，包含数据清洗、特征工程等功能
│   ├── loader.py             # 数据加载模块，提供统一的数据加载接口
│   └── datasource/               # 数据源实现模块
│       ├── __init__.py           # 定义数据源的基类和通用接口
│       ├── baostock/             # Baostock数据源实现
│       │   ├── __init__.py       # Baostock模块初始化
│       │   ├── downloader.py     # Baostock数据下载实现
│       │   └── converter.py      # Baostock数据转换为Qlib格式的实现
│       └── wind/                 # Wind数据源实现
│           ├── __init__.py       # Wind模块初始化
│           ├── downloader.py     # Wind数据下载实现
│           └── converter.py      # Wind数据转换为Qlib格式的实现

├── config/
│   └── data_source.yaml    # 统一的数据源配置
├── scripts/
│   └── fetch_data.py       # 统一的数数据下载入口
```
分层架构设计
- 入口层（fetch_data.py）
    - 仅负责命令行参数解析
    - 将解析后的参数传递给调度层
    - 不包含任何业务逻辑判断
    - 保持简单和纯粹
- 调度层（datasets/download.py）
    - 作为统一的调度中心
    - 根据参数决定使用哪个数据源
    - 决定是否需要数据转换
    - 调用具体的数据源实现
    - 调用具体的数据转换实现
    - 处理数据流程的编排
- 实现层（datasets/datasource/）
    - 包含具体数据源的实现
    - 每个数据源独立实现下载逻辑
    - 每个数据源独立实现转换逻辑
    - 保持实现层的纯粹性


运行数据获取脚本：
```bash
  # 默认下载 2010-01-01至今所有股票数据
  python scripts/fetch_data.py --provider=baostock
  # 下载自定义股票列表
  python scripts/fetch_data.py --provider=baostock --stock-list=sh.600000,sz.000001
  # 下载自定义股票列表
  python scripts/fetch_data.py baostock --stock-codes data/stock_list/custom.txt
  # 下载单只股票指定时间范围内的数据
  python scripts/fetch_data.py --provider=baostock --convert --start-date=2020-01-01 --end-date=2021-01-01 --stock-list=sh.600000
```

---

### 📌 小贴士

- 所有路径和配置参数集中于 `config/` 目录下；
- 可通过 `datasets/init_qlib.py` 切换本地/远程数据；
- 推荐使用 `Jupyter` 打开 `notebooks/` 中的分析文件；
- 安装过程中如有网络问题可使用清华镜像：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```
