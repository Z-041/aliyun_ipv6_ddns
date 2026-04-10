"""命令行接口模块.

提供 aliyun-ddns 命令行工具入口。
"""

from __future__ import annotations

import sys

from aliyun_ddns.core import main as core_main


def main(argv: list[str] | None = None) -> int:
    """CLI入口函数.

    Args:
        argv: 命令行参数

    Returns:
        退出码
    """
    return core_main(argv)


if __name__ == "__main__":
    sys.exit(main())
