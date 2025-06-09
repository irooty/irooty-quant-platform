"""
测试 Wind w.wsd 接口
"""

import unittest
from WindPy import w
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class TestWindWSD(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """测试类初始化时运行一次"""
        w.start()
    
    def setUp(self):
        """每个测试方法运行前执行"""
        self.stock_code = "000001.SZ"  # 平安银行
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # 通用测试参数
        self.test_stocks = ["000001.SZ", "000002.SZ"]  # 平安银行、万科A
        self.test_fields = ["open", "high", "low", "close", "volume"]
    
    def test_single_stock_single_field(self):
        """测试单个股票单个字段"""
        # 获取收盘价
        data = w.wsd(self.stock_code, "close", self.yesterday, self.today)
        
        # 验证结果
        self.assertEqual(data.ErrorCode, 0)
        self.assertIsNotNone(data.Data)
        self.assertEqual(len(data.Codes), 1)
        self.assertEqual(data.Codes[0], self.stock_code)
        
        # 转换为DataFrame查看数据
        if data.ErrorCode == 0:
            df = pd.DataFrame(data.Data[0], 
                            index=data.Times,
                            columns=["close"])
            print("\n单个股票收盘价数据:")
            print(df)
    
    def test_single_stock_multiple_fields(self):
        """测试单个股票多个字段"""
        data = w.wsd(self.stock_code, self.test_fields, self.yesterday, self.today)
        
        # 验证结果
        self.assertEqual(data.ErrorCode, 0)
        self.assertEqual(len(data.Fields), len(self.test_fields))
        
        # 转换为DataFrame查看数据
        if data.ErrorCode == 0:
            # 将数据重组为正确的形状
            data_dict = {field: values for field, values in zip(data.Fields, data.Data)}
            df = pd.DataFrame(data_dict, index=data.Times)
            print("\n单个股票多字段数据:")
            print(df)
    
    def test_multiple_stocks_single_field(self):
        """测试多个股票单个字段"""
        data = w.wsd(self.test_stocks, "close", self.yesterday, self.today)
        
        # 验证结果
        self.assertEqual(data.ErrorCode, 0)
        self.assertEqual(len(data.Codes), len(self.test_stocks))
        
        # 转换为DataFrame查看数据
        if data.ErrorCode == 0:
            # 打印原始数据结构
            print("\n原始数据结构:")
            print(f"Data shape: {len(data.Data)} x {len(data.Data[0])}")
            print(f"Times: {data.Times}")
            print(f"Codes: {data.Codes}")
            print(f"Raw Data: {data.Data}")
            
            # 创建DataFrame
            df = pd.DataFrame([data.Data[0]], 
                            index=data.Times,
                            columns=data.Codes)
            print("\n多个股票收盘价数据:")
            print(df)
            
            # 验证数据
            self.assertEqual(df.shape[1], len(self.test_stocks))
            self.assertTrue(all(code in df.columns for code in self.test_stocks))
    
    def test_multiple_stocks_multiple_fields(self):
        """测试多个股票多个字段"""
        data = w.wsd(self.test_stocks, self.test_fields, self.yesterday, self.today)
        
        # 验证结果
        self.assertEqual(data.ErrorCode, 0)
        self.assertEqual(len(data.Codes), len(self.test_stocks))
        self.assertEqual(len(data.Fields), len(self.test_fields))
        
        if data.ErrorCode == 0:
            # 打印原始数据结构
            print("\n原始数据结构:")
            print(f"Data shape: {len(data.Data)} x {len(data.Data[0])}")
            print(f"Times: {data.Times}")
            print(f"Codes: {data.Codes}")
            print(f"Fields: {data.Fields}")
            print(f"Raw Data: {data.Data}")
            
            # 创建多层索引DataFrame
            data_dict = {}
            for i, code in enumerate(data.Codes):
                stock_data = {}
                for j, field in enumerate(data.Fields):
                    stock_data[field] = data.Data[i * len(self.test_fields) + j]
                data_dict[code] = pd.DataFrame(stock_data, index=data.Times)
            
            # 合并所有股票的数据
            df = pd.concat(data_dict, axis=1)
            
            print("\n多个股票多字段数据:")
            print(df)
            
            # 验证数据结构
            self.assertEqual(df.columns.nlevels, 2)  # 两级索引：股票代码和字段
            self.assertEqual(len(df.columns.unique(level=0)), len(self.test_stocks))  # 股票数量
            self.assertEqual(len(df.columns.unique(level=1)), len(self.test_fields))  # 字段数量
    
    def test_with_options(self):
        """测试带选项的数据获取"""
        # 获取前复权数据
        options = "PriceAdj=F"  # F=前复权
        data = w.wsd(self.stock_code, "close", self.yesterday, self.today, options)
        
        # 验证结果
        self.assertEqual(data.ErrorCode, 0)
        
        # 转换为DataFrame查看数据
        if data.ErrorCode == 0:
            df = pd.DataFrame(data.Data[0],
                            index=data.Times,
                            columns=["close_adj"])
            print("\n前复权收盘价数据:")
            print(df)
    
    def test_error_handling(self):
        """测试错误处理"""
        # 测试无效的股票代码
        invalid_code = "000000.XX"
        data = w.wsd(invalid_code, "close", self.yesterday, self.today)
        
        # 应该返回错误
        self.assertNotEqual(data.ErrorCode, 0)
        print(f"\n预期的错误代码: {data.ErrorCode}")
    
    @classmethod
    def tearDownClass(cls):
        """测试类结束时运行一次"""
        w.close()

if __name__ == "__main__":
    unittest.main() 