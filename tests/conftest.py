"""pytest配置和共享fixtures."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Generator

import pytest

from aliyun_ddns.models.config import Config, DNSRecord


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """提供临时目录."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_config() -> Config:
    """提供示例配置."""
    return Config(
        access_key_id="test_access_key_id_12345",
        access_key_secret="test_access_key_secret_12345",
        domain="example.com",
        records=[
            DNSRecord(rr="@", type="A"),
            DNSRecord(rr="www", type="AAAA"),
        ],
        interval=300,
        ttl=600,
    )


@pytest.fixture
def config_file(temp_dir: Path, sample_config: Config) -> Path:
    """提供配置文件路径."""
    config_path = temp_dir / "config.yaml"
    sample_config.to_yaml(config_path)
    return config_path
