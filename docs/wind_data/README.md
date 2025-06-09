# 万得金融平台数据下载项目文档

## 文档结构

```
docs/wind_data/
├── README.md                     # 本文件
├── data_processing/             # 数据处理相关文档
│   ├── wind_data_pipeline.md    # Wind数据处理流水线文档
│   └── qlib_format.md          # Qlib数据格式说明
├── usage_guide.md              # 使用指南
└── config/                      # 配置相关文档
    └── wind_config_guide.md    # Wind配置指南
```

## 文档说明

### 使用指南
- [使用指南](usage_guide.md)
  - 环境准备和安装说明
  - 配置说明
  - 运行说明
  - 常见问题解答
  - 维护建议

### 数据处理文档
- [Wind数据处理流水线](data_processing/wind_data_pipeline.md)
  - 详细描述了从Wind下载数据到转换为Qlib格式的完整流程
  - 包含系统架构、技术栈、功能模块等详细说明
  - 提供了配置说明和使用指南
  - 基于项目现有目录结构实现

- [Qlib数据格式说明](data_processing/qlib_format.md)
  - 描述了Qlib数据格式的具体要求
  - 包含数据转换的详细说明
  - 提供了数据验证的方法

### 配置文档
- [Wind配置指南](config/wind_config_guide.md)
  - 详细说明了配置文件的各个参数
  - 提供了配置示例和最佳实践
  - 包含常见问题解答

## 文档更新记录

| 日期 | 文档 | 更新内容 | 作者 |
|------|------|----------|------|
| 2025-06-09 | wind_data_pipeline.md | 初始版本 | YangYiYun |
| 2025-06-09 | wind_config.yaml | 初始版本 | YangYiYun |
| 2025-06-09 | wind_data_pipeline.md | 更新系统架构以匹配项目结构 | YangYiYun |
| 2025-06-09 | usage_guide.md | 添加使用指南 | YangYiYun |

## 快速开始

1. 首先阅读 [使用指南](usage_guide.md) 了解如何安装和配置系统
2. 参考 [Wind数据处理流水线](data_processing/wind_data_pipeline.md) 了解系统架构和实现细节
3. 查看 [Wind配置指南](config/wind_config_guide.md) 进行系统配置
4. 按照使用指南中的说明运行系统
5. 遇到问题时查看相应文档中的常见问题章节

## 文档维护

- 文档采用Markdown格式编写
- 代码示例应当清晰且可运行
- 配置示例应当包含详细的注释
- 定期更新文档以反映最新的变更

## 贡献指南

1. 发现文档问题请提交Issue
2. 提交文档更新请创建Pull Request
3. 文档变更请更新文档更新记录
4. 保持文档格式统一和规范

# Wind数据下载模块

## 简介
Wind数据下载模块提供了高效、可靠的方式从Wind金融终端下载股票数据。该模块采用多线程并行处理，支持批量下载，并具有完善的错误处理和数据验证机制。

## 主要特性

1. **高效并行下载**
   - 多线程并行下载不同字段数据
   - 智能批次处理，避免请求过载
   - 优化的数据结构处理

2. **可靠性保证**
   - 完善的错误处理和重试机制
   - 数据完整性验证
   - 失败记录跟踪和保存

3. **灵活配置**
   - 可配置的批次大小
   - 可调节的并行度
   - 可自定义的重试策略

4. **进度管理**
   - 详细的进度日志
   - 断点续传支持
   - 失败任务记录

## 配置说明

```yaml
# Wind API配置
wind:
  retry_times: 3                 # API调用重试次数
  retry_interval: 60             # 重试间隔（秒）
  batch_size: 50                # 批量下载大小
  timeout: 60                   # API超时时间（秒）

# 并行处理配置
parallel:
  max_workers: 4               # 最大工作线程数
  chunk_size: 1000            # 数据块大小
```

## 使用示例

```python
from datasets.wind import WindDownloader

# 初始化下载器
downloader = WindDownloader(config)

# 下载数据
success = downloader.download_data()

# 增量更新
downloader.download_incremental_data()
```

## 数据存储结构

1. **批次数据文件**
   - 位置：`data/raw/wind/batch_*.parquet`
   - 格式：多层索引DataFrame
   - 结构：时间索引，股票代码和字段的多层列索引

2. **合并数据文件**
   - 位置：`data/raw/wind/all_data.parquet`
   - 包含所有批次的完整数据

3. **失败记录**
   - 位置：`data/raw/wind/failed_downloads.parquet`
   - 记录下载失败的字段和股票

## 性能优化

1. **批次处理**
   - 默认批次大小：50只股票
   - 动态调整以平衡效率和稳定性

2. **并行策略**
   - 字段级并行下载
   - 智能任务分配
   - 避免过度并发

3. **错误处理**
   - 随机重试延迟
   - 智能重试策略
   - 详细的错误记录

## 注意事项

1. 确保Wind终端已正确安装并登录
2. 合理配置批次大小和并行度
3. 注意监控失败记录和日志
4. 定期备份重要数据

## 更多信息

详细使用说明请参考 [使用指南](usage_guide.md)。 