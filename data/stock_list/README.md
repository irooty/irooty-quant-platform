# 股票列表文件

本目录存放常用的股票代码列表文件，用于数据下载、回测等场景。

## 文件说明

### 沪深300成分股 (hs300.txt)
- 沪深300指数成分股列表
- 包含300只A股股票代码
- 格式：每行一个股票代码，如 `sh.600000`

### 中证500成分股 (zz500.txt)
- 中证500指数成分股列表
- 包含500只A股股票代码
- 格式：每行一个股票代码

### 上证50成分股 (sz50.txt)
- 上证50指数成分股列表
- 包含50只A股股票代码
- 格式：每行一个股票代码

### 创业板指成分股 (cyb.txt)
- 创业板指成分股列表
- 包含创业板主要股票代码
- 格式：每行一个股票代码

### 自定义股票列表 (custom.txt)
- 用户自定义的股票代码列表
- 格式：每行一个股票代码，或逗号分隔

## 使用方法

### 命令行下载
```bash
# 下载沪深300成分股数据
python scripts/fetch_data.py baostock --stock_codes data/stock_list/hs300.txt

# 下载自定义股票列表
python scripts/fetch_data.py baostock --stock_codes data/stock_list/custom.txt
```

### Python代码调用
```python
from datasets.datasource.baostock.downloader import BaostockDownloader

# 使用沪深300成分股列表
downloader = BaostockDownloader(
    provider='baostock',
    stock_codes='data/stock_list/hs300.txt'
)
downloader.batch_download()
```

## 文件格式

- 支持每行一个股票代码
- 支持逗号分隔的格式
- 股票代码格式：`sh.600000`（上海）、`sz.000001`（深圳）
- 支持空行和注释（以#开头）

## 注意事项

- 股票代码需要与数据源格式保持一致
- 建议定期更新成分股列表以保持时效性
- 自定义列表请确保股票代码格式正确 