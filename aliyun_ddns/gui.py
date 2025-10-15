#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阿里云 DDNS 图形界面模块
"""

import os
import sys
import time
import yaml
import logging
import threading
import subprocess
import platform
import pystray
from PIL import Image, ImageDraw
from tkinter import Tk, messagebox

# 导入核心模块和工具函数
from . import core
from .utils import setup_logging, get_config_path, _config_lock

APP_NAME = "阿里云DDNS"
VERSION = "2.1.0"
CONFIG_FILE = get_config_path()

class DDNSTrayApp:
    def __init__(self):
        self.running = True
        self.config = None
        self.config_mtime = 0
        self.last_sync_time = 0  # 上次同步时间
        self.sync_interval = 30   # 同步间隔检查（秒），增加到30秒以减少频繁检查
        
        # 立即加载配置
        self._load_config()
        
        # 创建托盘
        self.icon = pystray.Icon(
            APP_NAME,
            self._create_icon(),
            APP_NAME,
            self._create_menu()
        )
        core.log_message("应用已启动")

    def _load_config(self):
        """加载配置（线程安全）"""
        with _config_lock:
            try:
                if not os.path.exists(CONFIG_FILE):
                    self._create_default_config()
                
                current_mtime = os.path.getmtime(CONFIG_FILE)
                if current_mtime > self.config_mtime:
                    self.config_mtime = current_mtime
                    self.config = core.load_config(CONFIG_FILE)
                    return True
                return False
            except Exception as e:
                core.log_message(f"配置错误: {type(e).__name__}", logging.ERROR)
                self.config = None
                return False

    def _create_default_config(self):
        """创建默认配置"""
        default = {
            "access_key_id": "YOUR_ACCESS_KEY_ID",
            "access_key_secret": "YOUR_ACCESS_KEY_SECRET",
            "domain": "example.com",
            "records": [
                {"rr": "@", "type": "A"}
            ],
            "interval": 300,
            "ttl": 600
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(default, f, allow_unicode=True, default_flow_style=False)
        core.log_message("已创建默认配置文件")

    def _create_icon(self, color="#4CAF50"):
        """创建图标"""
        img = Image.new('RGBA', (64, 64))
        draw = ImageDraw.Draw(img)
        # 绘制云朵形状
        draw.ellipse((10, 10, 54, 30), fill=color)  # 云朵上部
        draw.ellipse((5, 20, 35, 50), fill=color)   # 云朵左下部
        draw.ellipse((25, 20, 55, 50), fill=color)  # 云朵右下部
        # 绘制DNS文本
        draw.text((20, 25), "DNS", fill="white")
        return img.resize((32, 32))

    def _create_menu(self):
        """创建菜单"""
        return pystray.Menu(
            pystray.MenuItem("立即同步", self._sync),
            pystray.MenuItem("查看记录", self._show_records),
            pystray.MenuItem("编辑配置", self._edit_config),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self.quit)
        )

    def run(self):
        """启动应用"""
        threading.Thread(target=self._worker, daemon=True).start()
        self.icon.run()

    def _worker(self):
        """后台工作线程"""
        while self.running:
            try:
                # 检查配置更新（每60秒检查一次，减少频繁检查）
                if int(time.time()) % 60 == 0:
                    if self._load_config():
                        self.icon.notify("配置已更新", APP_NAME)
                
                # 自动同步
                if self.config:
                    interval = self.config.get('interval', 300)
                    current_time = time.time()
                    
                    # 检查是否到了同步时间
                    if current_time - self.last_sync_time >= interval:
                        self._sync_once()
                        self.last_sync_time = current_time
                
                # 减少CPU占用，增加到30秒
                time.sleep(30)
            except Exception as e:
                core.log_message(f"工作线程错误: {type(e).__name__}", logging.ERROR)
                time.sleep(60)  # 出错时等待更长时间

    def _sync_once(self):
        """执行同步"""
        try:
            if self.config and core.sync_records(self.config):
                self.icon.title = f"{APP_NAME} - 已同步"
                self.icon.icon = self._create_icon("#4CAF50")  # 绿色
            else:
                self.icon.icon = self._create_icon("#F44336")  # 红色
        except Exception as e:
            core.log_message(f"同步错误: {type(e).__name__}", logging.ERROR)

    def _sync(self, icon, item):
        """手动同步"""
        threading.Thread(target=self._sync_once, daemon=True).start()

    def _show_records(self, icon, item):
        """显示记录"""
        try:
            # 检查配置是否已加载
            if not self.config:
                self._msg("错误", "配置未加载")
                return
                
            from aliyunsdkcore.client import AcsClient
            client = AcsClient(
                self.config['access_key_id'],
                self.config['access_key_secret'],
                self.config.get('region', 'cn-hangzhou')
            )
            msg = []
            for r in self.config['records']:
                rec = core.get_dns_record(client, self.config['domain'], r['rr'], r['type'])
                if rec:
                    msg.append(f"{rec['RR']}.{self.config['domain']}: {rec['Value']}")
            self._msg("DNS记录", "\n".join(msg) or "无记录")
        except Exception as e:
            core.log_message(f"获取记录失败: {type(e).__name__}", logging.ERROR)
            self._msg("错误", "获取记录失败")

    def _edit_config(self, icon, item):
        """编辑配置"""
        try:
            system = platform.system()
            if system == "Windows":
                subprocess.run(["notepad", CONFIG_FILE], check=True)
            elif system == "Darwin":  # macOS
                subprocess.run(["open", CONFIG_FILE], check=True)
            else:  # Linux
                subprocess.run(["xdg-open", CONFIG_FILE], check=True)
        except Exception as e:
            core.log_message(f"无法打开配置文件: {type(e).__name__}", logging.ERROR)
            self._msg("错误", "无法打开配置文件")

    def _msg(self, title, msg):
        """显示消息"""
        root = Tk()
        root.withdraw()
        messagebox.showinfo(title, msg)
        root.destroy()

    def quit(self, icon, item):
        """退出应用"""
        self.running = False
        self.icon.stop()

def main():
    """GUI 入口函数"""
    # 配置日志
    setup_logging("logs/gui.log")
    
    try:
        app = DDNSTrayApp()
        app.run()
    except Exception as e:
        core.log_message(f"启动失败: {type(e).__name__}", logging.ERROR)
        sys.exit(1)

if __name__ == '__main__':
    main()