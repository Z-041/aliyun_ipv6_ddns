"""阿里云 DDNS 客户端包.

提供动态域名解析功能，支持 IPv4 和 IPv6。

示例:
    >>> from aliyun_ddns import DDNSService, Config
    >>> config = Config.from_yaml("config.yaml")
    >>> service = DDNSService(config)
    >>> service.sync_all()
"""

from aliyun_ddns.core import DDNSService, DDNSSyncResult, load_config
from aliyun_ddns.gui import DDNSTrayApp
from aliyun_ddns.models.config import Config, DNSRecord, Settings
from aliyun_ddns.services.dns import (
    AliyunDNSProvider,
    DNSCreateError,
    DNSProvider,
    DNSQueryError,
    DNSRecordInfo,
    DNSUpdateError,
)
from aliyun_ddns.services.ip import IPService
from aliyun_ddns.utils.logging import get_logger, setup_logging
from aliyun_ddns.utils.retry import retry

__version__ = "2.2.0"
__author__ = "Your Name"

__all__ = [
    # 核心功能
    "DDNSService",
    "DDNSSyncResult",
    "load_config",
    # GUI
    "DDNSTrayApp",
    # 模型
    "Config",
    "DNSRecord",
    "Settings",
    # 服务
    "AliyunDNSProvider",
    "DNSProvider",
    "DNSRecordInfo",
    "IPService",
    # 异常
    "DNSCreateError",
    "DNSQueryError",
    "DNSUpdateError",
    # 工具
    "get_logger",
    "setup_logging",
    "retry",
    # 元信息
    "__version__",
    "__author__",
]
