"""日志配置工具."""

from __future__ import annotations

import logging
import logging.handlers
import os
from pathlib import Path
from typing import ClassVar

DEFAULT_LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
DEFAULT_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
DEFAULT_MAX_BYTES: int = 10 * 1024 * 1024  # 10MB
DEFAULT_BACKUP_COUNT: int = 5


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器."""

    COLORS: ClassVar[dict[str, str]] = {
        "DEBUG": "\033[36m",  # 青色
        "INFO": "\033[32m",  # 绿色
        "WARNING": "\033[33m",  # 黄色
        "ERROR": "\033[31m",  # 红色
        "CRITICAL": "\033[35m",  # 紫色
        "RESET": "\033[0m",
    }

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录."""
        log_color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset_color = self.COLORS["RESET"]

        # 保存原始值
        original_levelname = record.levelname
        original_msg = record.msg

        # 添加颜色
        record.levelname = f"{log_color}{record.levelname}{reset_color}"
        if isinstance(record.msg, str):
            record.msg = f"{log_color}{record.msg}{reset_color}"

        result = super().format(record)

        # 恢复原始值
        record.levelname = original_levelname
        record.msg = original_msg

        return result


def setup_logging(
    log_file: str | None = None,
    verbose: bool = False,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
    use_colors: bool = True,
) -> logging.Logger:
    """配置日志系统.

    Args:
        log_file: 日志文件路径，None则不写入文件
        verbose: 是否启用详细日志
        max_bytes: 单个日志文件最大字节数
        backup_count: 保留的备份文件数量
        use_colors: 是否在控制台使用颜色

    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger("aliyun_ddns")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    # 清除现有处理器
    logger.handlers.clear()

    # 创建格式化器
    file_formatter = logging.Formatter(DEFAULT_LOG_FORMAT, datefmt=DEFAULT_DATE_FORMAT)
    console_formatter = (
        ColoredFormatter(DEFAULT_LOG_FORMAT, datefmt=DEFAULT_DATE_FORMAT)
        if use_colors
        else logging.Formatter(DEFAULT_LOG_FORMAT, datefmt=DEFAULT_DATE_FORMAT)
    )

    # 文件处理器
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """获取模块日志记录器.

    Args:
        name: 模块名称

    Returns:
        日志记录器
    """
    return logging.getLogger(name)
