#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Optional, Dict, Type
from .base_converter import BaseConverter
from .baostock_converter import BaostockConverter

class ConverterFactory:
    """转换器工厂类
    用于创建不同数据源的转换器
    """
    
    _converters: Dict[str, Type[BaseConverter]] = {
        'baostock': BaostockConverter,
        # 在这里添加其他数据源的转换器
    }
    
    @classmethod
    def create_converter(cls, data_source: str, config_path: Optional[str] = None) -> BaseConverter:
        """创建转换器
        
        Args:
            data_source: 数据源名称
            config_path: 配置文件路径
            
        Returns:
            BaseConverter: 转换器实例
            
        Raises:
            ValueError: 如果数据源不支持
        """
        converter_class = cls._converters.get(data_source.lower())
        if converter_class is None:
            raise ValueError(f'不支持的数据源: {data_source}')
            
        return converter_class(config_path)
    
    @classmethod
    def register_converter(cls, data_source: str, converter_class: Type[BaseConverter]) -> None:
        """注册新的转换器
        
        Args:
            data_source: 数据源名称
            converter_class: 转换器类
        """
        cls._converters[data_source.lower()] = converter_class 