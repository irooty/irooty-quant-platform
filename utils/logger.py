"""
日志工具模块
提供统一的日志记录功能
"""

import sys
from pathlib import Path
from loguru import logger

def setup_logger(name, config=None):
    """
    设置日志记录器
    
    Args:
        name (str): 模块名称
        config (dict, optional): 日志配置. Defaults to None.
    
    Returns:
        logger: 配置好的日志记录器
    """
    # 移除默认的处理器
    logger.remove()
    
    # 如果没有配置，使用默认配置
    if config is None:
        config = {
            'level': 'INFO',
            'rotation': '500 MB',
            'retention': '10 days',
        }
    
    # 确保日志目录存在
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    # 添加控制台处理器
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=config.get('level', 'INFO'),
        enqueue=True
    )
    
    # 添加文件处理器
    logger.add(
        log_dir / f"{name}.log",
        rotation=config.get('rotation', '500 MB'),
        retention=config.get('retention', '10 days'),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=config.get('level', 'INFO'),
        encoding='utf-8',
        enqueue=True
    )
    
    return logger.bind(name=name)