"""阿里云 DDNS 核心功能模块.

该模块提供 DDNS 同步的核心功能，包括配置加载、IP获取和DNS记录管理。
"""

from __future__ import annotations

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING

from aliyun_ddns.models.config import Config
from aliyun_ddns.services.dns import (
    AliyunDNSProvider,
    DNSCreateError,
    DNSProvider,
    DNSQueryError,
    DNSUpdateError,
)
from aliyun_ddns.services.ip import IPService
from aliyun_ddns.utils.logging import get_logger, setup_logging

if TYPE_CHECKING:
    from aliyun_ddns.models.config import DNSRecord

logger = get_logger(__name__)

DEFAULT_CONFIG_PATH: str = "config.yaml"
DEFAULT_LOG_PATH: str = "logs/aliyun_ddns.log"


class DDNSSyncResult:
    """DDNS同步结果."""

    def __init__(self) -> None:
        """初始化结果."""
        self.success_count: int = 0
        self.fail_count: int = 0
        self.skipped_count: int = 0
        self.details: list[dict] = []

    @property
    def total(self) -> int:
        """获取总记录数."""
        return self.success_count + self.fail_count + self.skipped_count

    @property
    def success(self) -> bool:
        """是否全部成功."""
        return self.fail_count == 0 and self.success_count > 0

    def add_success(self, record_name: str, old_ip: str | None, new_ip: str) -> None:
        """添加成功记录."""
        self.success_count += 1
        self.details.append(
            {
                "record": record_name,
                "status": "success",
                "old_ip": old_ip,
                "new_ip": new_ip,
            }
        )

    def add_failure(self, record_name: str, error: str) -> None:
        """添加失败记录."""
        self.fail_count += 1
        self.details.append(
            {"record": record_name, "status": "failed", "error": error}
        )

    def add_skipped(self, record_name: str, reason: str) -> None:
        """添加跳过记录."""
        self.skipped_count += 1
        self.details.append(
            {"record": record_name, "status": "skipped", "reason": reason}
        )


class DDNSService:
    """DDNS服务."""

    def __init__(
        self,
        config: Config,
        dns_provider: DNSProvider | None = None,
        ip_service: IPService | None = None,
    ) -> None:
        """初始化DDNS服务.

        Args:
            config: DDNS配置
            dns_provider: DNS服务提供者，默认使用阿里云
            ip_service: IP服务，默认创建新实例
        """
        self.config = config
        self.dns = dns_provider or AliyunDNSProvider(config)
        self.ip_service = ip_service or IPService()

    def sync_record(self, record: DNSRecord) -> bool:
        """同步单个DNS记录.

        Args:
            record: DNS记录配置

        Returns:
            是否同步成功
        """
        record_name = f"{record.rr}.{self.config.domain}"
        record_type = record.type

        try:
            # 获取当前IP
            logger.info(f"[{record_name}] 正在获取{record_type}地址...")
            ip = self.ip_service.get_public_ip(record_type == "AAAA")

            if not ip:
                logger.error(f"[{record_name}] 获取IP失败")
                return False

            # 查询现有记录
            existing = self.dns.get_record(
                self.config.domain, record.rr, record_type
            )

            if existing:
                if existing.value == ip:
                    logger.info(f"[{record_name}] IP未变化: {ip}")
                    return True
                else:
                    old_ip = existing.value
                    if self.dns.update_record(
                        existing.record_id,
                        record.rr,
                        record_type,
                        ip,
                        record.ttl or self.config.ttl,
                    ):
                        logger.info(f"[{record_name}] IP已更新: {old_ip} → {ip}")
                        return True
                    return False
            else:
                if self.dns.create_record(
                    self.config.domain,
                    record.rr,
                    record_type,
                    ip,
                    record.ttl or self.config.ttl,
                ):
                    logger.info(f"[{record_name}] 记录已创建: {ip}")
                    return True
                return False

        except (DNSQueryError, DNSUpdateError, DNSCreateError) as e:
            logger.error(f"[{record_name}] DNS操作失败: {e}")
            return False
        except Exception as e:
            logger.error(f"[{record_name}] 处理记录时发生异常: {type(e).__name__}: {e}")
            return False

    def sync_all(self, max_workers: int = 5) -> DDNSSyncResult:
        """同步所有DNS记录.

        Args:
            max_workers: 最大并发数

        Returns:
            同步结果
        """
        result = DDNSSyncResult()
        total_records = len(self.config.records)

        if total_records == 0:
            logger.warning("没有需要同步的记录")
            return result

        logger.info(f"开始同步 {total_records} 条记录")

        # 限制并发数
        max_workers = min(max_workers, total_records)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_record = {
                executor.submit(self.sync_record, record): record
                for record in self.config.records
            }

            for future in as_completed(future_to_record):
                record = future_to_record[future]
                record_name = f"{record.rr}.{self.config.domain}"

                try:
                    success = future.result(timeout=30)
                    if success:
                        result.add_success(record_name, None, "")
                    else:
                        result.add_failure(record_name, "同步失败")
                except Exception as e:
                    result.add_failure(record_name, str(e))

        logger.info(
            f"同步完成: {result.success_count}/{result.total} 成功, "
            f"{result.fail_count} 失败, {result.skipped_count} 跳过"
        )

        return result


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> Config:
    """加载配置文件.

    Args:
        path: 配置文件路径

    Returns:
        配置对象

    Raises:
        FileNotFoundError: 配置文件不存在
        ValueError: 配置验证失败
    """
    path = Path(path)

    if not path.exists():
        logger.info(f"配置文件不存在，创建默认配置: {path}")
        Config.create_default(path)
        raise FileNotFoundError(
            f"配置文件不存在，已创建默认配置: {path}\n"
            f"请编辑配置文件后重新运行程序。"
        )

    config = Config.from_yaml(path)
    logger.info("配置加载成功")
    return config


def main(argv: list[str] | None = None) -> int:
    """命令行入口函数.

    Args:
        argv: 命令行参数

    Returns:
        退出码
    """
    parser = argparse.ArgumentParser(
        description="阿里云 DDNS 客户端",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                           # 使用默认配置
  %(prog)s -c /path/to/config.yaml   # 指定配置文件
  %(prog)s -v                        # 启用详细日志
        """,
    )
    parser.add_argument(
        "-c",
        "--config",
        default=DEFAULT_CONFIG_PATH,
        help=f"配置文件路径 (默认: {DEFAULT_CONFIG_PATH})",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="启用详细日志"
    )
    parser.add_argument(
        "--log-file",
        default=DEFAULT_LOG_PATH,
        help=f"日志文件路径 (默认: {DEFAULT_LOG_PATH})",
    )

    args = parser.parse_args(argv)

    # 配置日志
    setup_logging(args.log_file, args.verbose)

    try:
        # 加载配置
        config = load_config(args.config)

        # 创建服务并执行同步
        service = DDNSService(config)
        result = service.sync_all()

        return 0 if result.success else 1

    except FileNotFoundError as e:
        logger.error(str(e))
        return 2
    except ValueError as e:
        logger.error(f"配置错误: {e}")
        return 3
    except Exception as e:
        logger.exception(f"程序执行失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
