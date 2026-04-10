"""阿里云 DDNS 客户端安装脚本.

兼容旧版安装方式，推荐使用 pyproject.toml。
"""

from setuptools import find_packages, setup

setup(
    name="aliyun-ddns",
    version="2.2.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="阿里云 DDNS 客户端，支持 IPv4 和 IPv6",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/aliyun-ddns",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
    ],
    license="MIT",
    python_requires=">=3.9",
    install_requires=[
        "aliyun-python-sdk-core>=2.13.3",
        "aliyun-python-sdk-alidns>=2.6.18",
        "pystray>=0.19.4",
        "Pillow>=9.0.0",
        "requests>=2.28.0",
        "PyYAML>=6.0",
        "pydantic>=2.0",
        "pydantic-settings>=2.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-asyncio>=0.21",
            "pytest-cov>=4.0",
            "black>=23.0",
            "ruff>=0.1.0",
            "mypy>=1.5",
            "pre-commit>=3.0",
            "types-requests>=2.31",
            "types-PyYAML>=6.0",
            "responses>=0.23",
        ],
    },
    entry_points={
        "console_scripts": [
            "aliyun-ddns=aliyun_ddns.cli:main",
        ],
        "gui_scripts": [
            "aliyun-ddns-gui=aliyun_ddns.gui:main",
        ],
    },
    package_data={
        "": ["*.yaml", "*.md"],
    },
    include_package_data=True,
)
