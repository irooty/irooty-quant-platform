import unittest
from pathlib import Path
import yaml
from datasets.wind import WindDownloader

class TestWindDownloader(unittest.TestCase):
    def setUp(self):
        """测试前的准备工作"""
        # 读取配置文件
        config_path = Path("config/wind_config.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        
        # 创建下载器实例
        self.downloader = WindDownloader(self.config)
    
    def test_wind_connection(self):
        """测试Wind API连接"""
        self.assertTrue(self.downloader._check_wind_connection())
    
    def test_stock_list_download(self):
        """测试股票列表下载"""
        stock_list = self.downloader.download_stock_list()
        self.assertIsNotNone(stock_list)
        self.assertGreater(len(stock_list), 0)
    
    def test_stock_data_download(self):
        """测试股票数据下载"""
        # 测试参数
        stock_codes = ["000001.SZ", "000002.SZ"]  # 平安银行、万科A
        start_date = "2023-12-01"
        end_date = "2023-12-31"
        
        # 执行下载
        self.downloader.download_stock_data(
            stock_list=stock_codes,
            start_date=start_date,
            end_date=end_date
        )
        
        # 验证文件是否生成
        expected_file = self.downloader.raw_dir / "batch_1.parquet"
        self.assertTrue(expected_file.exists())

if __name__ == "__main__":
    unittest.main() 