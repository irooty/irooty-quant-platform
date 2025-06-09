# Qlib数据格式说明

## 1. 概述

Qlib数据格式是一种标准化的金融数据存储格式，用于量化投资研究。本文档描述了Wind数据到Qlib格式的转换规范和验证方法。

## 2. 目录结构

```
qlib/
├── calendars/           # 交易日历
│   └── all_calendar.txt # 所有交易日期
├── instruments/         # 标的列表
│   └── all.txt         # 所有股票代码
├── features/           # 特征数据
│   ├── sh600000/      # 按股票代码分目录
│   ├── sh600001/
│   └── ...
└── metadata.json       # 元数据信息
```

## 3. 数据格式说明

### 3.1 交易日历 (calendars)

- 文件格式：文本文件，每行一个日期
- 日期格式：YYYY-MM-DD
- 排序：按日期升序
- 示例：
```
2010-01-04
2010-01-05
2010-01-06
...
```

### 3.2 标的列表 (instruments)

- 文件格式：文本文件，每行一个股票代码
- 代码格式：原始Wind代码
- 排序：按代码字母顺序
- 示例：
```
600000.SH
600001.SH
600002.SH
...
```

### 3.3 特征数据 (features)

每个股票一个目录，目录下包含多个特征文件：

- 目录命名：股票代码（如：sh600000）
- 文件格式：Parquet格式
- 特征文件：
  - `open.parquet`: 开盘价
  - `high.parquet`: 最高价
  - `low.parquet`: 最低价
  - `close.parquet`: 收盘价
  - `volume.parquet`: 成交量
  - `amount.parquet`: 成交额
  - `turn_rate.parquet`: 换手率
  - `is_trading.parquet`: 交易状态
  - `factor.parquet`: 复权因子

每个特征文件的数据格式：
```python
DataFrame(
    columns=['date', 'value'],
    data=[
        ['2010-01-04', 10.5],
        ['2010-01-05', 10.6],
        ...
    ]
)
```

### 3.4 元数据 (metadata.json)

```json
{
    "version": "0.1.0",
    "data_type": "CN_STOCK_A",
    "frequency": "1d",
    "fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "amount",
        "turn_rate",
        "is_trading",
        "factor"
    ],
    "storage_format": "parquet",
    "compression": "snappy"
}
```

## 4. 数据转换规则

### 4.1 Wind字段映射

| Wind字段 | Qlib字段 | 说明 |
|----------|----------|------|
| OPEN | open | 开盘价 |
| HIGH | high | 最高价 |
| LOW | low | 最低价 |
| CLOSE | close | 收盘价 |
| VOLUME | volume | 成交量 |
| AMT | amount | 成交额 |
| TURN | turn_rate | 换手率 |
| TRADE_STATUS | is_trading | 交易状态 |
| FACTOR | factor | 复权因子 |

### 4.2 数据类型转换

- 日期：统一转换为 YYYY-MM-DD 格式
- 价格：保留小数点后4位
- 成交量：整数
- 成交额：保留小数点后2位
- 换手率：保留小数点后4位
- 交易状态：转换为0/1（0表示停牌，1表示正常交易）
- 复权因子：保留小数点后6位

## 5. 数据验证

### 5.1 完整性检查

1. 交易日历验证
```python
def validate_calendar(calendar_file):
    dates = pd.read_csv(calendar_file, header=None)
    # 检查日期连续性
    # 检查日期格式
    # 检查是否按升序排列
```

2. 标的列表验证
```python
def validate_instruments(instruments_file):
    codes = pd.read_csv(instruments_file, header=None)
    # 检查代码格式
    # 检查是否有重复
```

3. 特征数据验证
```python
def validate_features(feature_dir):
    # 检查必要字段是否存在
    # 检查数据类型
    # 检查日期范围
    # 检查缺失值
```

### 5.2 数据质量检查

1. 价格合理性
- 检查负值
- 检查异常涨跌幅
- 检查价格为0的情况

2. 成交量合理性
- 检查负值
- 检查异常成交量
- 检查停牌日成交量

3. 数据一致性
- 检查OHLC价格关系
- 检查成交量和成交额关系
- 检查停牌日数据

## 6. 使用示例

### 6.1 读取数据

```python
import pandas as pd

# 读取交易日历
calendar = pd.read_csv('qlib/calendars/all_calendar.txt', header=None)

# 读取股票列表
instruments = pd.read_csv('qlib/instruments/all.txt', header=None)

# 读取特征数据
stock_code = 'sh600000'
close_prices = pd.read_parquet(f'qlib/features/{stock_code}/close.parquet')
```

### 6.2 数据验证

```python
from utils.data_utils import validate_data

# 验证规则
rules = {
    'check_missing': True,
    'missing_rate': 0.1,
    'check_anomaly': True,
    'price_change': 0.2,
    'volume_change': 5.0
}

# 验证数据
passed, errors = validate_data(df, rules)
```

## 7. 注意事项

1. 数据完整性
   - 确保所有必要字段都存在
   - 检查数据的时间范围是否完整
   - 验证停牌日的数据处理是否正确

2. 数据一致性
   - 保持所有特征的日期对齐
   - 确保价格之间的关系合理
   - 验证成交量和成交额的对应关系

3. 性能优化
   - 使用Parquet格式存储以提高读取效率
   - 按股票分目录存储以便于并行处理
   - 合理使用数据压缩 