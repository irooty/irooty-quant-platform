from setuptools import setup, find_packages
import os
from pathlib import Path

def read_requirements():
    with open("requirements.txt", encoding="utf-8-sig") as f:  # 使用 utf-8-sig 来自动处理 BOM
        return [
            line.strip() 
            for line in f.readlines() 
            if line.strip() and not line.strip().startswith("#")
        ]

# 创建.build目录
build_dir = Path('.build')
build_dir.mkdir(exist_ok=True)

setup(
    name="irooty-quant-platform",
    version="0.1.0",
    packages=find_packages(),
    install_requires=read_requirements(),
    python_requires=">=3.11,<3.12",  # 指定Python 3.11.x版本
    # 将egg-info目录放在.build目录下
    options={
        'egg_info': {
            'egg_base': str(build_dir),
        },
    },
) 