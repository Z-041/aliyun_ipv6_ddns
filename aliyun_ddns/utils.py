#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阿里云 DDNS 工具函数模块
"""

import logging
import os
import threading
import time
from functools import wraps
import hashlib

# 线程锁用于确保线程安全
_config_lock = threading.Lock()

def setup_logging(log_file="aliyun_ddns.log", verbose=False, max_bytes=10*1024*1024, backup_count=5):
    """配置日志系统"""
    import logging.handlers
    
    # 确保日志目录存在
    log_dir = os.path.dirname(log_file) if os.path.dirname(log_file) else "logs"
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 创建日志记录器
    logger = logging.getLogger('aliyun_ddns')
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    # 清除现有的处理器
    logger.handlers.clear()
    
    # 创建文件处理器（带轮转）
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, 
        maxBytes=max_bytes, 
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    # 创建格式器并添加到处理器
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加处理器到记录器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def is_windows():
    """检查是否为Windows系统"""
    return os.name == 'nt'

def get_config_path():
    """获取配置文件路径"""
    return "config.yaml"

def thread_safe_singleton(cls):
    """线程安全的单例装饰器"""
    instances = {}
    lock = threading.Lock()
    
    @wraps(cls)
    def get_instance(*args, **kwargs):
        if cls not in instances:
            with lock:
                if cls not in instances:
                    instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    
    return get_instance

def retry(max_attempts=3, delay=1, backoff=2):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            current_delay = delay
            
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    if attempts >= max_attempts:
                        raise e
                    time.sleep(current_delay)
                    current_delay *= backoff
            return None
        return wrapper
    return decorator

def mask_sensitive_info(text, patterns=None):
    """遮蔽敏感信息"""
    if not isinstance(text, str):
        return text
        
    # 默认敏感信息模式
    default_patterns = [
        (r'access_key_id["\s]*[=:]["\s]*([^\s"\']{5})[^\s"\']*', r'access_key_id": "\1***"'),  # 遮蔽access_key_id
        (r'access_key_secret["\s]*[=:]["\s]*([^\s"\']{5})[^\s"\']*', r'access_key_secret": "\1***"'),  # 遮蔽access_key_secret
        (r'(\'|")[^\'"]{5}[^\'"]*(\'|")', r'\1*****\2'),  # 遮蔽引号中的长字符串
    ]
    
    patterns = patterns or default_patterns
    result = text
    for pattern, replacement in patterns:
        import re
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result