"""DNS服务抽象和阿里云实现."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

import yaml
from aliyunsdkalidns.request.v20150109 import (
    AddDomainRecordRequest,
    DescribeDomainRecordsRequest,
    UpdateDomainRecordRequest,
)
from aliyunsdkcore.acs_exception.exceptions import ClientException, ServerException
from aliyunsdkcore.client import AcsClient

from aliyun_ddns.utils.logging import get_logger

if TYPE_CHECKING:
    from aliyun_ddns.models.config import Config, DNSRecord

logger = get_logger(__name__)


class DNSRecordInfo:
    """DNS记录信息."""

    def __init__(self, record_id: str, rr: str, record_type: str, value: str) -> None:
        self.record_id = record_id
        self.rr = rr
        self.record_type = record_type
        self.value = value

    @classmethod
    def from_aliyun_response(cls, data: dict[str, Any]) -> DNSRecordInfo:
        """从阿里云响应创建记录信息."""
        return cls(
            record_id=str(data.get("RecordId", "")),
            rr=str(data.get("RR", "")),
            record_type=str(data.get("Type", "")),
            value=str(data.get("Value", "")),
        )


class DNSProvider(ABC):
    """DNS服务提供者抽象基类."""

    @abstractmethod
    def get_record(
        self, domain: str, rr: str, record_type: str
    ) -> DNSRecordInfo | None:
        """获取DNS记录.

        Args:
            domain: 域名
            rr: 主机记录
            record_type: 记录类型 (A 或 AAAA)

        Returns:
            记录信息，如果不存在则返回None
        """
        pass

    @abstractmethod
    def update_record(
        self, record_id: str, rr: str, record_type: str, value: str, ttl: int
    ) -> bool:
        """更新DNS记录.

        Args:
            record_id: 记录ID
            rr: 主机记录
            record_type: 记录类型
            value: 新的记录值
            ttl: TTL值

        Returns:
            是否更新成功
        """
        pass

    @abstractmethod
    def create_record(
        self, domain: str, rr: str, record_type: str, value: str, ttl: int
    ) -> bool:
        """创建DNS记录.

        Args:
            domain: 域名
            rr: 主机记录
            record_type: 记录类型
            value: 记录值
            ttl: TTL值

        Returns:
            是否创建成功
        """
        pass


class AliyunDNSProvider(DNSProvider):
    """阿里云DNS服务提供者."""

    def __init__(self, config: Config) -> None:
        """初始化阿里云DNS客户端.

        Args:
            config: DDNS配置
        """
        self.config = config
        self._client: AcsClient | None = None

    @property
    def client(self) -> AcsClient:
        """获取或创建阿里云客户端."""
        if self._client is None:
            self._client = AcsClient(
                self.config.access_key_id,
                self.config.access_key_secret,
                self.config.region,
            )
        return self._client

    def get_record(
        self, domain: str, rr: str, record_type: str
    ) -> DNSRecordInfo | None:
        """获取DNS记录."""
        try:
            request = DescribeDomainRecordsRequest.DescribeDomainRecordsRequest()
            request.set_DomainName(domain)
            request.set_RRKeyWord(rr)
            request.set_TypeKeyWord(record_type)
            request.set_SearchMode("EXACT")

            response = self.client.do_action_with_exception(request)
            data = yaml.safe_load(response)
            records = (
                data.get("DomainRecords", {}).get("Record", [])
                if isinstance(data, dict)
                else []
            )

            for record_data in records:
                if (
                    isinstance(record_data, dict)
                    and record_data.get("RR") == rr
                    and record_data.get("Type") == record_type
                ):
                    return DNSRecordInfo.from_aliyun_response(record_data)

            return None

        except ServerException as e:
            logger.error(f"查询记录失败 (服务器错误): {e.get_error_code()}")
            raise DNSQueryError(f"服务器错误: {e.get_error_code()}") from e
        except ClientException as e:
            logger.error(f"查询记录失败 (客户端错误): {e.get_error_code()}")
            raise DNSQueryError(f"客户端错误: {e.get_error_code()}") from e

    def update_record(
        self, record_id: str, rr: str, record_type: str, value: str, ttl: int
    ) -> bool:
        """更新DNS记录."""
        try:
            request = UpdateDomainRecordRequest.UpdateDomainRecordRequest()
            request.set_RecordId(record_id)
            request.set_RR(rr)
            request.set_Type(record_type)
            request.set_Value(value)
            request.set_TTL(ttl)

            self.client.do_action_with_exception(request)
            logger.info(f"已更新记录: {rr} -> {value}")
            return True

        except ServerException as e:
            error_code = e.get_error_code()
            if "Forbidden.RAM" in str(error_code):
                logger.error("权限不足，请检查阿里云访问密钥权限")
            else:
                logger.error(f"更新记录失败 (服务器错误): {error_code}")
            raise DNSUpdateError(f"更新失败: {error_code}") from e
        except ClientException as e:
            logger.error(f"更新记录失败 (客户端错误): {e.get_error_code()}")
            raise DNSUpdateError(f"客户端错误: {e.get_error_code()}") from e

    def create_record(
        self, domain: str, rr: str, record_type: str, value: str, ttl: int
    ) -> bool:
        """创建DNS记录."""
        try:
            request = AddDomainRecordRequest.AddDomainRecordRequest()
            request.set_DomainName(domain)
            request.set_RR(rr)
            request.set_Type(record_type)
            request.set_Value(value)
            request.set_TTL(ttl)

            self.client.do_action_with_exception(request)
            logger.info(f"已创建记录: {rr}.{domain} -> {value}")
            return True

        except ServerException as e:
            error_code = e.get_error_code()
            if "Forbidden.RAM" in str(error_code):
                logger.error("权限不足，请检查阿里云访问密钥权限")
            elif "AlreadyExists" in str(error_code):
                logger.info(f"记录已存在: {rr}.{domain}")
                return True
            else:
                logger.error(f"创建记录失败 (服务器错误): {error_code}")
            raise DNSCreateError(f"创建失败: {error_code}") from e
        except ClientException as e:
            logger.error(f"创建记录失败 (客户端错误): {e.get_error_code()}")
            raise DNSCreateError(f"客户端错误: {e.get_error_code()}") from e


class DNSError(Exception):
    """DNS操作基础异常."""

    pass


class DNSQueryError(DNSError):
    """DNS查询异常."""

    pass


class DNSUpdateError(DNSError):
    """DNS更新异常."""

    pass


class DNSCreateError(DNSError):
    """DNS创建异常."""

    pass
