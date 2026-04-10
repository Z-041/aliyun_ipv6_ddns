"""服务层模块."""

from .dns import AliyunDNSProvider, DNSProvider
from .ip import IPService

__all__ = ["AliyunDNSProvider", "DNSProvider", "IPService"]
