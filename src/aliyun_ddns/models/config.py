"""配置模型定义."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


class DNSRecord(BaseModel):
    """DNS记录配置模型."""

    rr: str = Field(..., description="主机记录，如 @、www、home")
    type: Literal["A", "AAAA"] = Field(..., description="记录类型，A为IPv4，AAAA为IPv6")
    ttl: int | None = Field(default=None, description="TTL值，默认使用全局配置")

    @field_validator("rr")
    @classmethod
    def validate_rr(cls, v: str) -> str:
        """验证主机记录格式."""
        v = v.strip()
        if not v:
            raise ValueError("主机记录不能为空")
        if len(v) > 253:
            raise ValueError("主机记录长度不能超过253字符")
        return v

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """验证记录类型."""
        if v not in ("A", "AAAA"):
            raise ValueError("记录类型必须是 A 或 AAAA")
        return v


class Config(BaseModel):
    """DDNS配置模型."""

    access_key_id: str = Field(..., description="阿里云AccessKey ID")
    access_key_secret: str = Field(..., description="阿里云AccessKey Secret")
    domain: str = Field(..., description="域名，如 example.com")
    records: list[DNSRecord] = Field(..., description="DNS记录列表")
    region: str = Field(default="cn-hangzhou", description="阿里云区域")
    interval: int = Field(default=300, ge=60, le=86400, description="同步间隔（秒）")
    ttl: int = Field(default=600, ge=60, le=86400, description="默认TTL值（秒）")

    @field_validator("access_key_id")
    @classmethod
    def validate_access_key_id(cls, v: str) -> str:
        """验证AccessKey ID格式."""
        v = v.strip()
        if not v or len(v) < 10:
            raise ValueError("AccessKey ID格式不正确")
        if v == "YOUR_ACCESS_KEY_ID":
            raise ValueError("请配置有效的阿里云AccessKey ID")
        return v

    @field_validator("access_key_secret")
    @classmethod
    def validate_access_key_secret(cls, v: str) -> str:
        """验证AccessKey Secret格式."""
        v = v.strip()
        if not v or len(v) < 10:
            raise ValueError("AccessKey Secret格式不正确")
        if v == "YOUR_ACCESS_KEY_SECRET":
            raise ValueError("请配置有效的阿里云AccessKey Secret")
        return v

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        """验证域名格式."""
        v = v.strip().lower()
        if not v or "." not in v:
            raise ValueError("域名格式不正确")
        if len(v) > 253:
            raise ValueError("域名长度不能超过253字符")
        return v

    @field_validator("records")
    @classmethod
    def validate_records(cls, v: list[DNSRecord]) -> list[DNSRecord]:
        """验证记录列表."""
        if not v:
            raise ValueError("至少需要配置一条DNS记录")
        return v

    @model_validator(mode="after")
    def set_record_ttl(self) -> Config:
        """为没有设置TTL的记录使用默认值."""
        for record in self.records:
            if record.ttl is None:
                record.ttl = self.ttl
        return self

    @classmethod
    def from_yaml(cls, path: str | Path) -> Config:
        """从YAML文件加载配置."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data:
            raise ValueError("配置文件为空")

        return cls(**data)

    def to_yaml(self, path: str | Path) -> None:
        """保存配置到YAML文件."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(
                self.model_dump(),
                f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
            )

    @classmethod
    def create_default(cls, path: str | Path) -> Config:
        """创建默认配置文件."""
        config = cls(
            access_key_id="YOUR_ACCESS_KEY_ID",
            access_key_secret="YOUR_ACCESS_KEY_SECRET",
            domain="example.com",
            records=[DNSRecord(rr="@", type="A")],
        )
        config.to_yaml(path)
        return config


class Settings(BaseModel):
    """应用设置模型（用于环境变量覆盖）."""

    log_level: str = Field(default="INFO", description="日志级别")
    log_file: str | None = Field(default=None, description="日志文件路径")
    verbose: bool = Field(default=False, description="是否启用详细日志")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """验证日志级别."""
        v = v.upper()
        valid_levels = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        if v not in valid_levels:
            raise ValueError(f"日志级别必须是 {valid_levels} 之一")
        return v
