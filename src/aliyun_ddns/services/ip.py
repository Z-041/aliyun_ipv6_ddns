"""IP地址获取服务."""

from __future__ import annotations

import ipaddress
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import ClassVar

import requests

from aliyun_ddns.utils.logging import get_logger
from aliyun_ddns.utils.retry import retry

logger = get_logger(__name__)

DEFAULT_IPV4_SERVICES: list[str] = [
    "https://api.ipify.org",
    "https://ipinfo.io/ip",
    "https://ifconfig.me/ip",
    "https://icanhazip.com",
    "https://ident.me",
]

DEFAULT_IPV6_SERVICES: list[str] = [
    "https://api64.ipify.org",
    "https://v6.ident.me",
    "https://ipv6.icanhazip.com",
]

HTTP_HEADERS: dict[str, str] = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

REQUEST_TIMEOUT: int = 10
MAX_WORKERS: int = 3


@dataclass
class IPCacheEntry:
    """IP缓存条目."""

    ip: str
    timestamp: float


class IPService:
    """IP地址获取服务."""

    _cache_timeout: ClassVar[int] = 60  # 缓存60秒

    def __init__(self) -> None:
        """初始化IP服务."""
        self._cache: dict[str, IPCacheEntry] = {}
        self._executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

    def __del__(self) -> None:
        """清理资源."""
        self._executor.shutdown(wait=False)

    @staticmethod
    @retry(max_attempts=3, delay=1, backoff=2)
    def validate_ip(ip: str, ipv6: bool = False) -> bool:
        """验证IP地址格式.

        Args:
            ip: IP地址字符串
            ipv6: 是否为IPv6地址

        Returns:
            是否为有效IP地址
        """
        if not ip or not isinstance(ip, str):
            return False

        try:
            if ipv6:
                ipaddress.IPv6Address(ip)
                return True
            else:
                ipaddress.IPv4Address(ip)
                return True
        except ipaddress.AddressValueError:
            return False

    def _get_from_cache(self, ipv6: bool) -> str | None:
        """从缓存获取IP地址."""
        cache_key = "ipv6" if ipv6 else "ipv4"
        entry = self._cache.get(cache_key)

        if entry and (time.time() - entry.timestamp) < self._cache_timeout:
            logger.debug(f"使用缓存的IP地址: {entry.ip}")
            return entry.ip

        return None

    def _set_cache(self, ipv6: bool, ip: str) -> None:
        """设置IP缓存."""
        cache_key = "ipv6" if ipv6 else "ipv4"
        self._cache[cache_key] = IPCacheEntry(ip=ip, timestamp=time.time())
        logger.debug(f"IP地址已缓存: {ip}")

    def _fetch_ip(self, url: str, ipv6: bool) -> str | None:
        """从单个服务获取IP地址.

        Args:
            url: 服务URL
            ipv6: 是否为IPv6地址

        Returns:
            IP地址或None
        """
        try:
            logger.debug(f"尝试从 {url} 获取IP地址")
            response = requests.get(
                url, timeout=REQUEST_TIMEOUT, headers=HTTP_HEADERS
            )
            response.raise_for_status()
            ip = response.text.strip()

            if ip and self.validate_ip(ip, ipv6):
                logger.debug(f"从 {url} 成功获取IP地址: {ip}")
                return ip
            else:
                logger.debug(f"从 {url} 获取的IP地址无效: {ip}")
                return None

        except requests.RequestException as e:
            logger.debug(f"从 {url} 获取IP地址失败: {e}")
            return None

    @retry(max_attempts=3, delay=1, backoff=2)
    def get_public_ip(
        self, ipv6: bool = False, services: list[str] | None = None
    ) -> str | None:
        """获取公网IP地址.

        Args:
            ipv6: 是否获取IPv6地址
            services: 自定义服务列表，默认使用内置列表

        Returns:
            公网IP地址，获取失败返回None
        """
        # 检查缓存
        cached_ip = self._get_from_cache(ipv6)
        if cached_ip:
            return cached_ip

        # 使用默认服务列表
        if services is None:
            services = DEFAULT_IPV6_SERVICES if ipv6 else DEFAULT_IPV4_SERVICES

        if not services:
            logger.warning("没有配置IP获取服务")
            return None

        # 提交所有任务
        futures = {
            self._executor.submit(self._fetch_ip, url, ipv6): url
            for url in services
        }

        # 获取第一个成功的结果
        for future in as_completed(futures):
            url = futures[future]
            try:
                ip = future.result(timeout=REQUEST_TIMEOUT + 2)
                if ip:
                    self._set_cache(ipv6, ip)
                    return ip
            except Exception as e:
                logger.debug(f"从 {url} 获取IP时发生异常: {e}")
                continue

        logger.warning("所有IP获取服务都失败了")
        return None

    def clear_cache(self) -> None:
        """清除IP缓存."""
        self._cache.clear()
        logger.debug("IP缓存已清除")
