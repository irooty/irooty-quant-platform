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
│   └── lstm_timing.py         # LSTM 市场择时
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
│   └── deploy_bot.py          # 结果推送脚本
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
pip install -r requirements.txt
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

### 📌 小贴士

- 所有路径和配置参数集中于 `config/` 目录下；
- 可通过 `datasets/init_qlib.py` 切换本地/远程数据；
- 推荐使用 `Jupyter` 打开 `notebooks/` 中的分析文件；
- 安装过程中如有网络问题可使用清华镜像：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```
