本目录用于存放各类数据文件：
- raw/      原始数据（如Wind/同花顺导出）
- processed/处理和标准化后的数据
- external/ 外部补充数据（如宏观经济数据等）
- qlib/cn_data/ Qlib量化平台的A股标准数据目录
    （可通过 qlib.run.init --target_dir ./data/qlib/cn_data --region cn 初始化）
- live_trading/       # 实盘交易数据（如成交记录、实盘订单、资金流水等）
- stock_list/         # 自定义股票列表（如自选股、指数成分股名单等）
