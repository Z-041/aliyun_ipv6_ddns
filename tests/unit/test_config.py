"""配置模型单元测试."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from aliyun_ddns.models.config import Config, DNSRecord


class TestDNSRecord:
    """DNSRecord模型测试."""

    def test_valid_record(self) -> None:
        """测试有效的DNS记录."""
        record = DNSRecord(rr="@", type="A")
        assert record.rr == "@"
        assert record.type == "A"
        assert record.ttl is None

    def test_valid_ipv6_record(self) -> None:
        """测试有效的IPv6记录."""
        record = DNSRecord(rr="www", type="AAAA", ttl=300)
        assert record.rr == "www"
        assert record.type == "AAAA"
        assert record.ttl == 300

    def test_invalid_type(self) -> None:
        """测试无效的记录类型."""
        with pytest.raises(ValidationError) as exc_info:
            DNSRecord(rr="@", type="MX")
        assert "A" in str(exc_info.value) or "AAAA" in str(exc_info.value)

    def test_empty_rr(self) -> None:
        """测试空的主机记录."""
        with pytest.raises(ValidationError):
            DNSRecord(rr="", type="A")

    def test_rr_stripping(self) -> None:
        """测试主机记录去除空格."""
        record = DNSRecord(rr="  www  ", type="A")
        assert record.rr == "www"


class TestConfig:
    """Config模型测试."""

    def test_valid_config(self) -> None:
        """测试有效配置."""
        config = Config(
            access_key_id="test_key_id_12345",
            access_key_secret="test_key_secret_12345",
            domain="example.com",
            records=[DNSRecord(rr="@", type="A")],
        )
        assert config.domain == "example.com"
        assert config.interval == 300  # 默认值
        assert config.ttl == 600  # 默认值

    def test_invalid_access_key_id(self) -> None:
        """测试无效的AccessKey ID."""
        with pytest.raises(ValidationError):
            Config(
                access_key_id="short",
                access_key_secret="valid_secret_12345",
                domain="example.com",
                records=[DNSRecord(rr="@", type="A")],
            )

    def test_placeholder_access_key_id(self) -> None:
        """测试占位符AccessKey ID."""
        with pytest.raises(ValidationError) as exc_info:
            Config(
                access_key_id="YOUR_ACCESS_KEY_ID",
                access_key_secret="valid_secret_12345",
                domain="example.com",
                records=[DNSRecord(rr="@", type="A")],
            )
        assert "AccessKey ID" in str(exc_info.value)

    def test_invalid_domain(self) -> None:
        """测试无效域名."""
        with pytest.raises(ValidationError):
            Config(
                access_key_id="valid_key_id_12345",
                access_key_secret="valid_secret_12345",
                domain="nodot",
                records=[DNSRecord(rr="@", type="A")],
            )

    def test_empty_records(self) -> None:
        """测试空记录列表."""
        with pytest.raises(ValidationError):
            Config(
                access_key_id="valid_key_id_12345",
                access_key_secret="valid_secret_12345",
                domain="example.com",
                records=[],
            )

    def test_interval_validation(self) -> None:
        """测试间隔时间验证."""
        with pytest.raises(ValidationError):
            Config(
                access_key_id="valid_key_id_12345",
                access_key_secret="valid_secret_12345",
                domain="example.com",
                records=[DNSRecord(rr="@", type="A")],
                interval=30,  # 小于最小值60
            )

    def test_ttl_inheritance(self) -> None:
        """测试TTL继承."""
        config = Config(
            access_key_id="valid_key_id_12345",
            access_key_secret="valid_secret_12345",
            domain="example.com",
            records=[
                DNSRecord(rr="@", type="A"),  # 没有指定TTL
                DNSRecord(rr="www", type="A", ttl=300),  # 指定了TTL
            ],
            ttl=600,
        )
        assert config.records[0].ttl == 600  # 继承全局TTL
        assert config.records[1].ttl == 300  # 使用自己的TTL


class TestConfigIO:
    """配置读写测试."""

    def test_from_yaml(self, config_file: Path) -> None:
        """测试从YAML加载配置."""
        config = Config.from_yaml(config_file)
        assert config.domain == "example.com"
        assert len(config.records) == 2

    def test_from_yaml_not_found(self, temp_dir: Path) -> None:
        """测试加载不存在的配置文件."""
        with pytest.raises(FileNotFoundError):
            Config.from_yaml(temp_dir / "nonexistent.yaml")

    def test_from_yaml_empty(self, temp_dir: Path) -> None:
        """测试加载空配置文件."""
        empty_file = temp_dir / "empty.yaml"
        empty_file.write_text("")
        with pytest.raises(ValueError, match="配置文件为空"):
            Config.from_yaml(empty_file)

    def test_to_yaml(self, temp_dir: Path, sample_config: Config) -> None:
        """测试保存配置到YAML."""
        output_file = temp_dir / "output.yaml"
        sample_config.to_yaml(output_file)

        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        assert "example.com" in content
        assert "access_key_id" in content

    def test_create_default(self, temp_dir: Path) -> None:
        """测试创建默认配置."""
        config_path = temp_dir / "default.yaml"
        Config.create_default(config_path)

        assert config_path.exists()
        with pytest.raises(ValidationError):
            # 默认配置包含占位符，验证会失败
            Config.from_yaml(config_path)


class TestConfigDomainNormalization:
    """域名规范化测试."""

    def test_domain_lowercase(self) -> None:
        """测试域名转换为小写."""
        config = Config(
            access_key_id="valid_key_id_12345",
            access_key_secret="valid_secret_12345",
            domain="EXAMPLE.COM",
            records=[DNSRecord(rr="@", type="A")],
        )
        assert config.domain == "example.com"

    def test_domain_stripping(self) -> None:
        """测试域名去除空格."""
        config = Config(
            access_key_id="valid_key_id_12345",
            access_key_secret="valid_secret_12345",
            domain="  example.com  ",
            records=[DNSRecord(rr="@", type="A")],
        )
        assert config.domain == "example.com"
