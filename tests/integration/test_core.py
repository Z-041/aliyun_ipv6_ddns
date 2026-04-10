"""核心功能集成测试."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aliyun_ddns.core import DDNSService, load_config
from aliyun_ddns.models.config import Config, DNSRecord
from aliyun_ddns.services.dns import DNSRecordInfo


class TestLoadConfig:
    """配置加载集成测试."""

    def test_load_valid_config(self, config_file: Path) -> None:
        """测试加载有效配置."""
        config = load_config(config_file)

        assert isinstance(config, Config)
        assert config.domain == "example.com"
        assert len(config.records) == 2

    def test_load_nonexistent_config_creates_default(self, temp_dir: Path) -> None:
        """测试加载不存在的配置会创建默认配置."""
        config_path = temp_dir / "new_config.yaml"

        with pytest.raises(FileNotFoundError) as exc_info:
            load_config(config_path)

        assert "已创建默认配置" in str(exc_info.value)
        assert config_path.exists()


class TestDDNSService:
    """DDNS服务集成测试."""

    @pytest.fixture
    def mock_dns_provider(self) -> MagicMock:
        """提供模拟的DNS提供者."""
        return MagicMock()

    @pytest.fixture
    def mock_ip_service(self) -> MagicMock:
        """提供模拟的IP服务."""
        return MagicMock()

    def test_sync_record_update_existing(
        self, sample_config: Config, mock_dns_provider: MagicMock, mock_ip_service: MagicMock
    ) -> None:
        """测试更新现有记录."""
        # 设置模拟
        mock_ip_service.get_public_ip.return_value = "192.168.1.100"
        mock_dns_provider.get_record.return_value = DNSRecordInfo(
            record_id="12345", rr="@", record_type="A", value="192.168.1.1"
        )
        mock_dns_provider.update_record.return_value = True

        # 创建服务
        service = DDNSService(
            config=sample_config,
            dns_provider=mock_dns_provider,
            ip_service=mock_ip_service,
        )

        # 执行同步
        result = service.sync_record(sample_config.records[0])

        assert result is True
        mock_dns_provider.update_record.assert_called_once()

    def test_sync_record_create_new(
        self, sample_config: Config, mock_dns_provider: MagicMock, mock_ip_service: MagicMock
    ) -> None:
        """测试创建新记录."""
        # 设置模拟
        mock_ip_service.get_public_ip.return_value = "192.168.1.100"
        mock_dns_provider.get_record.return_value = None
        mock_dns_provider.create_record.return_value = True

        # 创建服务
        service = DDNSService(
            config=sample_config,
            dns_provider=mock_dns_provider,
            ip_service=mock_ip_service,
        )

        # 执行同步
        result = service.sync_record(sample_config.records[0])

        assert result is True
        mock_dns_provider.create_record.assert_called_once()

    def test_sync_record_no_change(
        self, sample_config: Config, mock_dns_provider: MagicMock, mock_ip_service: MagicMock
    ) -> None:
        """测试IP未变化时不更新."""
        # 设置模拟 - IP未变化
        mock_ip_service.get_public_ip.return_value = "192.168.1.1"
        mock_dns_provider.get_record.return_value = DNSRecordInfo(
            record_id="12345", rr="@", record_type="A", value="192.168.1.1"
        )

        # 创建服务
        service = DDNSService(
            config=sample_config,
            dns_provider=mock_dns_provider,
            ip_service=mock_ip_service,
        )

        # 执行同步
        result = service.sync_record(sample_config.records[0])

        assert result is True
        mock_dns_provider.update_record.assert_not_called()
        mock_dns_provider.create_record.assert_not_called()

    def test_sync_record_get_ip_failed(
        self, sample_config: Config, mock_dns_provider: MagicMock, mock_ip_service: MagicMock
    ) -> None:
        """测试获取IP失败."""
        # 设置模拟 - IP获取失败
        mock_ip_service.get_public_ip.return_value = None

        # 创建服务
        service = DDNSService(
            config=sample_config,
            dns_provider=mock_dns_provider,
            ip_service=mock_ip_service,
        )

        # 执行同步
        result = service.sync_record(sample_config.records[0])

        assert result is False
        mock_dns_provider.get_record.assert_not_called()

    def test_sync_all_multiple_records(
        self, sample_config: Config, mock_dns_provider: MagicMock, mock_ip_service: MagicMock
    ) -> None:
        """测试同步多条记录."""
        # 设置模拟
        mock_ip_service.get_public_ip.return_value = "192.168.1.100"
        mock_dns_provider.get_record.return_value = None
        mock_dns_provider.create_record.return_value = True

        # 创建服务
        service = DDNSService(
            config=sample_config,
            dns_provider=mock_dns_provider,
            ip_service=mock_ip_service,
        )

        # 执行同步
        result = service.sync_all()

        assert result.success is True
        assert result.success_count == 2
        assert result.fail_count == 0

    def test_sync_result_properties(self) -> None:
        """测试同步结果属性."""
        from aliyun_ddns.core import DDNSSyncResult

        result = DDNSSyncResult()

        # 初始状态
        assert result.total == 0
        assert result.success is False

        # 添加成功记录
        result.add_success("test.example.com", "192.168.1.1", "192.168.1.2")
        assert result.success_count == 1
        assert result.total == 1
        assert result.success is True

        # 添加失败记录
        result.add_failure("test2.example.com", "error")
        assert result.fail_count == 1
        assert result.total == 2
        assert result.success is False

        # 添加跳过记录
        result.add_skipped("test3.example.com", "reason")
        assert result.skipped_count == 1
        assert result.total == 3
