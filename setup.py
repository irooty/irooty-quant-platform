from setuptools import setup, find_packages

def read_requirements():
    with open("requirements.txt", encoding="utf-8-sig") as f:  # 使用 utf-8-sig 来自动处理 BOM
        return [
            line.strip() 
            for line in f.readlines() 
            if line.strip() and not line.strip().startswith("#")
        ]

setup(
    name="irooty-quant-platform",
    version="0.1.0",
    packages=find_packages(),
    install_requires=read_requirements(),
    python_requires=">=3.11,<3.12",  # 指定Python 3.11.x版本
) 