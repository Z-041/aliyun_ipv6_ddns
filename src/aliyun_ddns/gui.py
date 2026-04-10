"""阿里云 DDNS 图形界面模块.

提供系统托盘应用程序，支持自动同步和手动操作。
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from typing import TYPE_CHECKING, ClassVar

import pystray
from PIL import Image, ImageDraw

from aliyun_ddns.core import DDNSService, load_config
from aliyun_ddns.models.config import Config
from aliyun_ddns.services.dns import AliyunDNSProvider
from aliyun_ddns.utils.logging import get_logger, setup_logging

if TYPE_CHECKING:
    from pystray import Icon, MenuItem

logger = get_logger(__name__)

APP_NAME: str = "阿里云DDNS"
VERSION: str = "2.2.0"
CONFIG_FILE: str = "config.yaml"
SYNC_CHECK_INTERVAL: int = 30  # 同步检查间隔（秒）
CONFIG_CHECK_INTERVAL: int = 60  # 配置检查间隔（秒）

# 颜色常量
COLOR_SUCCESS: str = "#4CAF50"  # 绿色
COLOR_ERROR: str = "#F44336"    # 红色
COLOR_WARNING: str = "#FF9800"  # 橙色


class DDNSTrayApp:
    """DDNS托盘应用程序."""

    def __init__(self) -> None:
        """初始化托盘应用."""
        self._running: bool = True
        self._config: Config | None = None
        self._config_mtime: float = 0.0
        self._last_sync_time: float = 0.0
        self._sync_lock: threading.Lock = threading.Lock()
        self._config_valid: bool = False
        self._pending_notification: tuple[str, str] | None = None

        # 加载配置
        self._config_valid = self._load_config()

        # 如果配置无效，显示警告图标
        icon_color = COLOR_SUCCESS if self._config_valid else COLOR_WARNING

        # 创建托盘图标
        self._icon: Icon = pystray.Icon(
            APP_NAME,
            self._create_icon(icon_color),
            f"{APP_NAME} - {'配置无效' if not self._config_valid else '就绪'}",
            self._create_menu(),
        )

        logger.info("应用已启动")

    def _load_config(self) -> bool:
        """加载配置（线程安全）.

        Returns:
            是否成功加载或更新
        """
        config_path = Path(CONFIG_FILE)

        try:
            # 配置文件不存在则创建默认配置
            if not config_path.exists():
                Config.create_default(config_path)
                logger.info("已创建默认配置文件")
                # 保存通知待显示
                self._pending_notification = (
                    "配置文件已创建",
                    "首次运行，已创建默认配置文件。请点击'编辑配置'菜单填写阿里云AccessKey信息后重启应用。"
                )
                return False

            # 检查文件修改时间
            current_mtime = config_path.stat().st_mtime
            if current_mtime <= self._config_mtime and self._config is not None:
                return True  # 配置已加载且未修改

            # 加载新配置
            self._config = Config.from_yaml(config_path)
            self._config_mtime = current_mtime
            logger.info("配置已更新")
            return True

        except Exception as e:
            logger.error(f"配置加载失败: {e}")
            self._config = None
            # 保存通知待显示
            error_msg = str(e)
            if "AccessKey" in error_msg:
                self._pending_notification = (
                    "配置错误",
                    "配置验证失败，请点击'编辑配置'菜单修改后重启应用。"
                )
            return False

    def _create_icon(self, color: str) -> Image.Image:
        """创建托盘图标.

        Args:
            color: 图标颜色

        Returns:
            图标图像
        """
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 绘制云朵形状
        draw.ellipse((10, 10, 54, 30), fill=color)  # 云朵上部
        draw.ellipse((5, 20, 35, 50), fill=color)   # 云朵左下部
        draw.ellipse((25, 20, 55, 50), fill=color)  # 云朵右下部

        # 绘制DNS文本
        try:
            draw.text((20, 25), "DNS", fill="white")
        except Exception:
            # 字体问题则跳过文本
            pass

        return img.resize((32, 32), Image.Resampling.LANCZOS)

    def _create_menu(self) -> pystray.Menu:
        """创建托盘菜单.

        Returns:
            菜单对象
        """
        return pystray.Menu(
            pystray.MenuItem("立即同步", self._on_sync),
            pystray.MenuItem("查看记录", self._on_show_records),
            pystray.MenuItem("编辑配置", self._on_edit_config),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(f"版本 {VERSION}", lambda icon, item: None, enabled=False),
            pystray.MenuItem("退出", self._on_quit),
        )

    def _on_sync(self, icon: Icon | None = None, item: MenuItem | None = None) -> None:
        """处理同步菜单点击.

        Args:
            icon: 托盘图标
            item: 菜单项
        """
        threading.Thread(target=self._sync_once, daemon=True).start()

    def _on_show_records(
        self, icon: Icon | None = None, item: MenuItem | None = None
    ) -> None:
        """处理查看记录菜单点击.

        Args:
            icon: 托盘图标
            item: 菜单项
        """
        threading.Thread(target=self._show_records, daemon=True).start()

    def _on_edit_config(
        self, icon: Icon | None = None, item: MenuItem | None = None
    ) -> None:
        """处理编辑配置菜单点击.

        Args:
            icon: 托盘图标
            item: 菜单项
        """
        self._edit_config()

    def _on_quit(
        self, icon: Icon | None = None, item: MenuItem | None = None
    ) -> None:
        """处理退出菜单点击.

        Args:
            icon: 托盘图标
            item: 菜单项
        """
        self._running = False
        if self._icon:
            self._icon.stop()

    def _sync_once(self) -> None:
        """执行一次同步."""
        with self._sync_lock:
            if not self._config:
                logger.warning("配置未加载，跳过同步")
                self._update_icon(COLOR_ERROR)
                return

            try:
                service = DDNSService(self._config)
                result = service.sync_all()

                if result.success:
                    self._update_icon(COLOR_SUCCESS)
                    self._icon.title = f"{APP_NAME} - 已同步"
                else:
                    self._update_icon(COLOR_ERROR)
                    self._icon.title = f"{APP_NAME} - 同步失败"

                self._last_sync_time = time.time()

            except Exception as e:
                logger.error(f"同步错误: {e}")
                self._update_icon(COLOR_ERROR)

    def _update_icon(self, color: str) -> None:
        """更新托盘图标颜色.

        Args:
            color: 颜色代码
        """
        try:
            self._icon.icon = self._create_icon(color)
        except Exception as e:
            logger.debug(f"更新图标失败: {e}")

    def _show_records(self) -> None:
        """显示DNS记录信息."""
        if not self._config:
            self._show_message("错误", "配置未加载")
            return

        try:
            provider = AliyunDNSProvider(self._config)
            records_info: list[str] = []

            for record in self._config.records:
                dns_record = provider.get_record(
                    self._config.domain, record.rr, record.type
                )
                if dns_record:
                    records_info.append(
                        f"{dns_record.rr}.{self._config.domain}: {dns_record.value}"
                    )
                else:
                    records_info.append(
                        f"{record.rr}.{self._config.domain}: (未找到)"
                    )

            message = "\n".join(records_info) if records_info else "无记录"
            self._show_message("DNS记录", message)

        except Exception as e:
            logger.error(f"获取记录失败: {e}")
            self._show_message("错误", f"获取记录失败: {e}")

    def _edit_config(self) -> None:
        """打开配置文件编辑器."""
        config_path = Path(CONFIG_FILE).resolve()

        try:
            system = platform.system()
            if system == "Windows":
                subprocess.run(["notepad", str(config_path)], check=True)
            elif system == "Darwin":  # macOS
                subprocess.run(["open", str(config_path)], check=True)
            else:  # Linux
                subprocess.run(["xdg-open", str(config_path)], check=True)

            # 编辑器关闭后重新加载配置
            self._load_config()

        except Exception as e:
            logger.error(f"无法打开配置文件: {e}")
            self._show_message("错误", f"无法打开配置文件: {e}")

    def _show_message(self, title: str, message: str) -> None:
        """显示消息对话框.

        Args:
            title: 标题
            message: 消息内容
        """
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo(title, message)
            root.destroy()
        except Exception as e:
            logger.error(f"显示消息失败: {e}")



    def _worker(self) -> None:
        """后台工作线程."""
        last_config_check: float = 0.0

        while self._running:
            try:
                current_time = time.time()

                # 检查配置更新
                if current_time - last_config_check >= CONFIG_CHECK_INTERVAL:
                    if self._load_config():
                        try:
                            self._icon.notify("配置已更新", APP_NAME)
                        except Exception:
                            pass
                    last_config_check = current_time

                # 自动同步
                if self._config:
                    interval = self._config.interval
                    if current_time - self._last_sync_time >= interval:
                        self._sync_once()

                # 休眠
                time.sleep(SYNC_CHECK_INTERVAL)

            except Exception as e:
                logger.error(f"工作线程错误: {e}")
                time.sleep(SYNC_CHECK_INTERVAL * 2)

    def run(self) -> None:
        """启动应用程序."""
        # 启动后台工作线程
        worker_thread = threading.Thread(target=self._worker, daemon=True)
        worker_thread.start()

        # 显示待处理的通知
        if self._pending_notification:
            try:
                title, message = self._pending_notification
                self._icon.notify(message, title)
            except Exception as e:
                logger.error(f"显示通知失败: {e}")

        # 运行托盘图标
        self._icon.run()


def main(argv: list[str] | None = None) -> int:
    """GUI入口函数.

    Args:
        argv: 命令行参数

    Returns:
        退出码
    """
    import argparse

    parser = argparse.ArgumentParser(description=f"{APP_NAME} 图形界面")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="启用详细日志"
    )
    parser.add_argument(
        "--log-file",
        default="logs/gui.log",
        help="日志文件路径 (默认: logs/gui.log)",
    )

    args = parser.parse_args(argv)

    # 配置日志
    setup_logging(args.log_file, args.verbose)

    try:
        app = DDNSTrayApp()
        app.run()
        return 0
    except Exception as e:
        logger.exception(f"程序错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
