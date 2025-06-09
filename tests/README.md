# 测试运行指南

本文档介绍如何运行项目中的测试用例。

## 1. 使用 unittest

### 运行所有测试
```bash
# 在项目根目录下运行
python -m unittest discover tests

# 或者指定测试目录
python -m unittest discover -s tests -p "test_*.py"
```

### 运行特定测试文件
```bash
# 运行特定的测试文件
python -m unittest tests/test_wind_downloader.py

# 使用点号语法
python -m unittest tests.test_wind_downloader
```

### 运行特定测试类
```bash
# 运行特定测试类中的所有测试
python -m unittest tests.test_wind_downloader.TestWindDownloader
```

### 运行特定测试方法
```bash
# 运行特定的测试方法
python -m unittest tests.test_wind_downloader.TestWindDownloader.test_batch_download
```

### 详细输出模式
```bash
# 使用 -v 参数获取详细输出
python -m unittest -v tests/test_wind_downloader.py
```

## 2. 使用 pytest（推荐）

首先安装 pytest：
```bash
pip install pytest
```

### 运行所有测试
```bash
# 在项目根目录下运行
pytest tests/

# 详细模式
pytest -v tests/
```

### 运行特定测试文件
```bash
# 运行特定文件
pytest tests/test_wind_downloader.py

# 详细模式
pytest -v tests/test_wind_downloader.py
```

### 运行特定测试类或方法
```bash
# 运行特定测试类
pytest tests/test_wind_downloader.py::TestWindDownloader

# 运行特定测试方法
pytest tests/test_wind_downloader.py::TestWindDownloader::test_batch_download
```

### 使用关键字过滤测试
```bash
# 运行名称中包含 "batch" 的测试
pytest -k "batch" tests/

# 运行名称中包含 "download" 但不包含 "batch" 的测试
pytest -k "download and not batch" tests/
```

### 生成测试报告
```bash
# 生成 HTML 报告（需要安装 pytest-html）
pip install pytest-html
pytest --html=report.html tests/

# 生成覆盖率报告（需要安装 pytest-cov）
pip install pytest-cov
pytest --cov=datasets tests/
pytest --cov=datasets --cov-report=html tests/
```

### 并行运行测试
```bash
# 安装 pytest-xdist
pip install pytest-xdist

# 使用多个 CPU 核心运行测试
pytest -n auto tests/
```

## 3. 调试测试

### 使用 VS Code 调试
1. 打开测试文件
2. 设置断点
3. 按 F5 或使用调试面板运行测试

### 使用 pdb 调试
```bash
# 在失败时进入调试器
python -m pytest tests/test_wind_downloader.py --pdb

# 在第一个失败时进入调试器并退出
python -m pytest tests/test_wind_downloader.py -x --pdb
```

## 4. 持续集成 (CI) 测试

在 CI 环境中运行测试时推荐的命令：
```bash
# 生成 XML 格式的测试报告
pytest --junitxml=test-results.xml tests/

# 同时生成覆盖率报告
pytest --cov=datasets --cov-report=xml --junitxml=test-results.xml tests/
```

## 5. 最佳实践

1. 经常运行测试
2. 保持测试独立性
3. 使用有意义的测试名称
4. 添加适当的测试文档
5. 定期检查测试覆盖率
6. 及时修复失败的测试 