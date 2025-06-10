# Wind数据下载使用指南

## 目录
1. [环境准备](#环境准备)
2. [配置说明](#配置说明)
3. [基本使用](#基本使用)
4. [高级功能](#高级功能)
5. [故障排除](#故障排除)
6. [最佳实践](#最佳实践)

## 环境准备

### 1. Wind终端安装
- 确保已安装Wind金融终端
- 确保Wind Python API (WindPy) 已正确安装
- 验证Wind终端可以正常登录

### 2. Python环境
- Python 3.11（推荐）
- 虚拟环境设置：
  ```bash
  # 创建虚拟环境
  python -m venv .venv
  
  # 激活虚拟环境
  # Windows:
  .venv\Scripts\activate
  # Linux/Mac:
  source .venv/bin/activate
  ```
- 必要的依赖包：
  ```
  pandas
  numpy
  WindPy
  pyyaml
  loguru
  ```

## 3. 运行说明

### 3.1 完整数据下载
用于首次下载或重新下载全部数据：

```bash
python scripts/download_wind_data.py --config config/wind_config.yaml
```
查看下载的数据结构：
```bash
python scripts/check_wind_data.py
```

### 3.2 增量数据更新
有两种运行模式：

1. 单次更新：
```bash
python scripts/update_wind_data.py --config config/wind_config.yaml
```

2. 定时更新（后台运行）：
```bash
# Windows (PowerShell):
Start-Process python -ArgumentList "scripts/update_wind_data.py --scheduler --config config/wind_config.yaml" -NoNewWindow

# Linux/Mac:
nohup python scripts/update_wind_data.py --scheduler --config config/wind_config.yaml > wind_update.log 2>&1 &
```

## 4. 数据目录结构

```
data/
├── raw/                    # 原始数据
│   └── wind/
│       ├── stock_list.parquet   # 股票列表
│       └── batch_*.parquet      # 批次数据
├── processed/              # 处理后的数据
│   └── cleaned_data.parquet
└── qlib/                  # Qlib格式数据
    ├── calendars/         # 交易日历
    ├── instruments/       # 标的列表
    └── features/         # 特征数据
```

## 5. 日志查看

日志文件位于 `logs/` 目录下：
- `wind_data_pipeline.log`: 完整下载日志
- `wind_data_update.log`: 增量更新日志
- `wind_data_scheduler.log`: 定时任务日志

## 配置说明

### 1. 基础配置
```yaml
paths:
  data_dir: "data"                # 数据根目录
  raw_dir: "data/raw/wind"        # Wind原始数据目录
  processed_dir: "data/processed" # 处理后的数据目录
  qlib_dir: "data/qlib"          # Qlib数据目录
```

### 2. Wind API配置
```yaml
wind:
  retry_times: 3                 # API调用重试次数
  retry_interval: 60             # 重试间隔（秒）
  batch_size: 50                # 批量下载大小
  timeout: 60                   # API超时时间（秒）
```

### 3. 数据范围配置
```yaml
data:
  start_date: "2023-12-01"      # 历史数据起始日期
  end_date: "2023-12-31"        # 历史数据结束日期
  universe: "A"                 # 股票范围：A-全部A股
  fields:                       # 需要下载的字段
    - "open"                    # 开盘价
    - "high"                    # 最高价
    - "low"                     # 最低价
    - "close"                   # 收盘价
    - "volume"                  # 成交量
```

### 4. 并行处理配置
```yaml
parallel:
  max_workers: 4               # 最大工作线程数
  chunk_size: 1000            # 数据块大小
```

## 基本使用

### 1. 初始化下载器
```python
from datasets.wind import WindDownloader

# 加载配置
with open('config/wind_config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# 创建下载器实例
downloader = WindDownloader(config)
```

### 2. 下载数据
```python
# 完整下载
success = downloader.download_data()

# 增量更新
downloader.download_incremental_data()
```

### 3. 数据文件说明
- `batch_*.parquet`: 批次数据文件
- `all_data.parquet`: 合并后的完整数据
- `failed_downloads.parquet`: 失败记录

## 高级功能

### 1. 自定义下载
```python
# 指定股票和字段下载
stock_list = ['000001.SZ', '000002.SZ']
fields = ['open', 'close']
downloader.download_stock_data(stock_list, fields, '2024-01-01', '2024-01-31')
```

### 2. 断点续传
- 下载器会记录已下载的字段
- 重启后会自动跳过已下载的字段
- 失败记录可用于选择性重试

### 3. 性能调优
- 调整批次大小：
  ```yaml
  wind:
    batch_size: 50  # 根据实际情况调整
  ```
- 调整并行度：
  ```yaml
  parallel:
    max_workers: 4  # 根据CPU核心数调整
  ```

## 故障排除

### 1. 常见错误
- Wind未连接
  ```
  解决：检查Wind终端是否正常登录
  ```
- 数据维度不匹配
  ```
  解决：检查字段配置是否正确
  ```
- 下载超时
  ```
  解决：调整batch_size或增加timeout时间
  ```

### 2. 错误恢复
1. 查看失败记录：
   ```python
   failed_data = pd.read_parquet('data/raw/wind/failed_downloads.parquet')
   ```
2. 针对性重试：
   ```python
   for field, stocks in failed_data.items():
       downloader.download_stock_data(stocks, [field], start_date, end_date)
   ```

## 最佳实践

### 1. 性能优化
- 合理设置批次大小
- 避免过度并行
- 定期清理临时文件

### 2. 数据质量
- 定期验证数据完整性
- 监控失败记录
- 保持数据备份

### 3. 运维建议
- 设置适当的日志级别
- 定期检查磁盘空间
- 监控下载性能

## 更新记录

### v1.0.0 (2024-01)
- 初始版本发布
- 支持多线程并行下载
- 完善的错误处理机制

### v1.1.0 (2024-02)
- 优化批次处理策略
- 添加断点续传功能
- 改进数据验证机制 