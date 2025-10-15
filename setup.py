#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阿里云 DDNS 客户端安装脚本
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="aliyun-ddns",
    version="2.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="阿里云 DDNS 客户端，支持 IPv4 和 IPv6",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/aliyun-ddns",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    license="MIT",
    python_requires=">=3.7",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "aliyun-ddns-core=aliyun_ddns.core:main",
        ],
        "gui_scripts": [
            "aliyun-ddns-gui=aliyun_ddns.gui:main",
        ]
    },
    package_data={
        "": ["*.yaml", "*.md"],
    },
    include_package_data=True,
)