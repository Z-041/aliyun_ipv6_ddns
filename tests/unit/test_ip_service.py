"""IP服务单元测试."""

from __future__ import annotations

import pytest
import responses

from aliyun_ddns.services.ip import (
    DEFAULT_IPV4_SERVICES,
    DEFAULT_IPV6_SERVICES,
    IPService,
)


class TestIPValidation:
    """IP验证测试."""

    def test_valid_ipv4(self) -> None:
        """测试有效的IPv4地址."""
        assert IPService.validate_ip("192.168.1.1") is True
        assert IPService.validate_ip("8.8.8.8") is True
        assert IPService.validate_ip("255.255.255.255") is True
        assert IPService.validate_ip("0.0.0.0") is True

    def test_invalid_ipv4(self) -> None:
        """测试无效的IPv4地址."""
        assert IPService.validate_ip("256.1.1.1") is False
        assert IPService.validate_ip("192.168.1") is False
        assert IPService.validate_ip("192.168.1.1.1") is False
        assert IPService.validate_ip("abc.def.ghi.jkl") is False
        assert IPService.validate_ip("") is False

    def test_valid_ipv6(self) -> None:
        """测试有效的IPv6地址."""
        assert IPService.validate_ip("::1", ipv6=True) is True
        assert IPService.validate_ip("fe80::1", ipv6=True) is True
        assert (
            IPService.validate_ip("2001:0db8:85a3:0000:0000:8a2e:0370:7334", ipv6=True)
            is True
        )
        assert IPService.validate_ip("2001:db8:85a3::8a2e:370:7334", ipv6=True) is True

    def test_invalid_ipv6(self) -> None:
        """测试无效的IPv6地址."""
        assert IPService.validate_ip("192.168.1.1", ipv6=True) is False
        assert IPService.validate_ip(":::", ipv6=True) is False
        assert IPService.validate_ip("", ipv6=True) is False


class TestIPServiceCache:
    """IP服务缓存测试."""

    def test_cache_get_set(self) -> None:
        """测试缓存读写."""
        service = IPService()

        # 初始缓存为空
        assert service._get_from_cache(ipv6=False) is None

        # 设置缓存
        service._set_cache(ipv6=False, ip="192.168.1.1")
        assert service._get_from_cache(ipv6=False) == "192.168.1.1"

        # IPv6缓存独立
        assert service._get_from_cache(ipv6=True) is None
        service._set_cache(ipv6=True, ip="::1")
        assert service._get_from_cache(ipv6=True) == "::1"

    def test_cache_clear(self) -> None:
        """测试清除缓存."""
        service = IPService()
        service._set_cache(ipv6=False, ip="192.168.1.1")
        service._set_cache(ipv6=True, ip="::1")

        service.clear_cache()

        assert service._get_from_cache(ipv6=False) is None
        assert service._get_from_cache(ipv6=True) is None


class TestIPServiceFetch:
    """IP获取测试（使用mock）."""

    @responses.activate
    def test_fetch_ip_success(self) -> None:
        """测试成功获取IP."""
        responses.add(
            responses.GET,
            "https://api.ipify.org",
            body="192.168.1.1",
            status=200,
        )

        service = IPService()
        ip = service._fetch_ip("https://api.ipify.org", ipv6=False)

        assert ip == "192.168.1.1"

    @responses.activate
    def test_fetch_ip_invalid_response(self) -> None:
        """测试无效的响应."""
        responses.add(
            responses.GET,
            "https://api.ipify.org",
            body="invalid_ip",
            status=200,
        )

        service = IPService()
        ip = service._fetch_ip("https://api.ipify.org", ipv6=False)

        assert ip is None

    @responses.activate
    def test_fetch_ip_http_error(self) -> None:
        """测试HTTP错误."""
        responses.add(
            responses.GET,
            "https://api.ipify.org",
            body="Error",
            status=500,
        )

        service = IPService()
        ip = service._fetch_ip("https://api.ipify.org", ipv6=False)

        assert ip is None

    @responses.activate
    def test_get_public_ip_from_cache(self) -> None:
        """测试从缓存获取IP."""
        service = IPService()
        service._set_cache(ipv6=False, ip="192.168.1.1")

        ip = service.get_public_ip(ipv6=False)

        assert ip == "192.168.1.1"

    @responses.activate
    def test_get_public_ip_from_service(self) -> None:
        """测试从服务获取IP."""
        responses.add(
            responses.GET,
            DEFAULT_IPV4_SERVICES[0],
            body="192.168.1.1",
            status=200,
        )

        service = IPService()
        ip = service.get_public_ip(ipv6=False, services=[DEFAULT_IPV4_SERVICES[0]])

        assert ip == "192.168.1.1"

    @responses.activate
    def test_get_public_ip_all_services_fail(self) -> None:
        """测试所有服务都失败."""
        for url in DEFAULT_IPV4_SERVICES[:2]:
            responses.add(responses.GET, url, body="Error", status=500)

        service = IPService()
        ip = service.get_public_ip(ipv6=False, services=DEFAULT_IPV4_SERVICES[:2])

        assert ip is None

    @responses.activate
    def test_get_public_ip_ipv6(self) -> None:
        """测试获取IPv6地址."""
        responses.add(
            responses.GET,
            DEFAULT_IPV6_SERVICES[0],
            body="fe80::1",
            status=200,
        )

        service = IPService()
        ip = service.get_public_ip(ipv6=True, services=[DEFAULT_IPV6_SERVICES[0]])

        assert ip == "fe80::1"
