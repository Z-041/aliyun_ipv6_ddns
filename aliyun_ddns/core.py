#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阿里云 DDNS 核心功能模块
"""

import re
import time
import yaml
import requests
import logging
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.acs_exception.exceptions import ServerException, ClientException
from aliyunsdkalidns.request.v20150109 import (
    DescribeDomainRecordsRequest,
    UpdateDomainRecordRequest,
    AddDomainRecordRequest
)

# 导入工具函数
from .utils import setup_logging, retry

# 配置日志
logger = logging.getLogger('aliyun_ddns')

# 全局缓存用于存储IP地址，避免频繁请求
_ip_cache = {}
_cache_timeout = 60  # 缓存60秒

def log_message(message, level=logging.INFO):
    """通用日志记录函数"""
    logger.log(level, message)

@retry(max_attempts=3, delay=1, backoff=2)
def valid_ip(ip, ipv6=False):
    """验证IP地址格式"""
    try:
        if ipv6:
            # 简化的 IPv6 验证，检查是否包含有效的十六进制字符和冒号
            # 这是一个实用的验证，而不是严格的 RFC 验证
            if not ip or not isinstance(ip, str):
                return False
            # 检查是否只包含有效的 IPv6 字符
            import re
            # 检查是否是有效的 IPv6 格式（简化版）
            if re.match(r'^[0-9a-fA-F:]+$', ip) and ':' in ip:
                # 检查是否有多个冒号
                if '::' in ip:
                    # 压缩格式，最多只能有一个 ::
                    if ip.count('::') > 1:
                        return False
                return True
            return False
        # IPv4 验证
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        for part in parts:
            if not part.isdigit() or not 0 <= int(part) <= 255:
                return False
        return True
    except Exception:
        return False

@retry(max_attempts=3, delay=1, backoff=2)
def get_public_ip(ipv6=False, services=None):
    """获取公网IP"""
    # 检查缓存
    cache_key = 'ipv6' if ipv6 else 'ipv4'
    if cache_key in _ip_cache:
        cached_time, cached_ip = _ip_cache[cache_key]
        if time.time() - cached_time < _cache_timeout:
            logger.debug(f"使用缓存的IP地址: {cached_ip}")
            return cached_ip
    
    # 默认服务列表
    default_ipv4_services = [
        'https://api.ipify.org',
        'https://ipinfo.io/ip',
        'https://ifconfig.me/ip',
        'https://icanhazip.com',
        'https://ident.me'
    ]
    
    default_ipv6_services = [
        'https://api64.ipify.org',
        'https://v6.ident.me',
        'https://ipv6.icanhazip.com'
    ]
    
    if ipv6:
        services = services or default_ipv6_services
    else:
        services = services or default_ipv4_services

    def fetch_ip(url):
        try:
            logger.debug(f"尝试从 {url} 获取IP地址")
            # 添加headers避免被某些服务拒绝
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            r = requests.get(url, timeout=10, headers=headers)  # 10秒超时
            r.raise_for_status()
            ip = r.text.strip()
            if ip and valid_ip(ip, ipv6):
                logger.debug(f"从 {url} 成功获取IP地址: {ip}")
                return ip
            else:
                logger.debug(f"从 {url} 获取的IP地址无效: {ip}")
                return None
        except Exception as e:
            logger.debug(f"从 {url} 获取IP地址失败: {e}")
            return None

    # 使用线程池并发获取IP，但限制并发数以避免触发服务限制
    max_workers = min(3, len(services))  # 限制最大并发数为3
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(fetch_ip, url): url for url in services}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                ip = future.result(timeout=12)  # 12秒超时，略高于请求超时
                if ip:
                    # 缓存结果
                    _ip_cache[cache_key] = (time.time(), ip)
                    logger.debug(f"成功获取IP地址并缓存: {ip}")
                    return ip
            except Exception as e:
                logger.debug(f"从 {url} 获取IP时发生异常: {e}")
                continue
    
    logger.warning("所有IP获取服务都失败了")
    return None

def validate_config(config):
    """验证配置"""
    errors = []
    required = ['access_key_id', 'access_key_secret', 'domain', 'records']
    for field in required:
        if field not in config:
            errors.append(f"缺少配置项: {field}")
    
    # 检查敏感信息是否已配置（不是默认值）
    if config.get('access_key_id') == 'YOUR_ACCESS_KEY_ID' or \
       config.get('access_key_secret') == 'YOUR_ACCESS_KEY_SECRET':
        errors.append("请配置有效的阿里云访问密钥")
    
    if 'records' in config:
        for i, r in enumerate(config['records']):
            if 'rr' not in r:
                errors.append(f"记录{i+1}缺少rr字段")
            if 'type' not in r or r['type'] not in ['A', 'AAAA']:
                errors.append(f"记录{i+1}类型错误，必须是A或AAAA")
    
    if errors:
        raise ValueError("配置错误: " + ", ".join(errors))
    return True

def load_config(path='config.yaml'):
    """加载配置"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
        
        # 设置默认值
        config.setdefault('interval', 300)
        config.setdefault('ttl', 600)
        
        # 为每个记录设置默认 TTL
        for record in config.get('records', []):
            record.setdefault('ttl', config['ttl'])
        
        validate_config(config)
        log_message("配置加载成功")
        return config
    except Exception as e:
        log_message(f"配置加载失败: {e}", logging.ERROR)
        raise

@retry(max_attempts=3, delay=1, backoff=2)
def get_dns_record(client, domain, rr, record_type):
    """获取DNS记录"""
    try:
        req = DescribeDomainRecordsRequest.DescribeDomainRecordsRequest()
        req.set_DomainName(domain)
        req.set_RRKeyWord(rr)
        req.set_TypeKeyWord(record_type)
        req.set_SearchMode("EXACT")
        resp = client.do_action_with_exception(req)
        records = yaml.safe_load(resp).get('DomainRecords', {}).get('Record', [])
        for r in records:
            if r.get('RR') == rr and r.get('Type') == record_type:
                return r
        return None
    except ServerException as e:
        logger.error(f"查询记录失败 (服务器错误): {e.get_error_code()}")
        raise
    except ClientException as e:
        logger.error(f"查询记录失败 (客户端错误): {e.get_error_code()}")
        raise
    except Exception as e:
        logger.error(f"查询记录失败 (未知错误): {type(e).__name__}")
        raise

@retry(max_attempts=3, delay=1, backoff=2)
def update_dns_record(client, record, ip, config):
    """更新DNS记录"""
    try:
        req = UpdateDomainRecordRequest.UpdateDomainRecordRequest()
        req.set_RecordId(record['RecordId'])
        req.set_RR(record['RR'])
        req.set_Type(record['Type'])
        req.set_Value(ip)
        req.set_TTL(config.get('ttl', 600))
        resp = client.do_action_with_exception(req)
        logger.debug("更新记录成功")
        logger.info(f"已更新记录: {record['RR']} -> {ip}")
        return True
    except ServerException as e:
        if "Forbidden.RAM" in str(e.get_error_code()):
            logger.error("权限不足，请检查阿里云访问密钥权限")
        else:
            logger.error(f"更新记录失败 (服务器错误): {e.get_error_code()}")
        raise
    except ClientException as e:
        logger.error(f"更新记录失败 (客户端错误): {e.get_error_code()}")
        raise
    except Exception as e:
        logger.error(f"更新记录失败 (未知错误): {type(e).__name__}")
        raise

@retry(max_attempts=3, delay=1, backoff=2)
def create_dns_record(client, domain, rr, record_type, ip, config):
    """创建DNS记录"""
    try:
        req = AddDomainRecordRequest.AddDomainRecordRequest()
        req.set_DomainName(domain)
        req.set_RR(rr)
        req.set_Type(record_type)
        req.set_Value(ip)
        req.set_TTL(config.get('ttl', 600))
        resp = client.do_action_with_exception(req)
        logger.debug("创建记录成功")
        logger.info(f"已创建记录: {rr}.{domain} -> {ip}")
        return True
    except ServerException as e:
        if "Forbidden.RAM" in str(e.get_error_code()):
            logger.error("权限不足，请检查阿里云访问密钥权限")
        elif "AlreadyExists" in str(e.get_error_code()):
            logger.info(f"记录已存在: {rr}.{domain}")
            return True
        else:
            logger.error(f"创建记录失败 (服务器错误): {e.get_error_code()}")
        raise
    except ClientException as e:
        logger.error(f"创建记录失败 (客户端错误): {e.get_error_code()}")
        raise
    except Exception as e:
        logger.error(f"创建记录失败 (未知错误): {type(e).__name__}")
        raise

def sync_records(config):
    """同步所有记录（带详细日志）"""
    start_time = time.time()
    try:
        # 创建客户端时检查密钥格式
        access_key_id = config['access_key_id']
        access_key_secret = config['access_key_secret']
        
        # 简单检查密钥格式（不记录具体值）
        if not access_key_id or not access_key_secret or \
           len(access_key_id) < 10 or len(access_key_secret) < 10:
            logger.error("阿里云访问密钥格式不正确")
            return False
            
        client = AcsClient(
            access_key_id,
            access_key_secret,
            config.get('region', 'cn-hangzhou')
        )
        success_count = 0
        total_records = len(config['records'])
        logger.info(f"开始同步 {total_records} 条记录")
        
        # 使用线程池并发处理所有记录，但限制并发数
        max_workers = min(5, total_records)  # 限制最大并发数为5
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有记录同步任务
            future_to_record = {
                executor.submit(sync_single_record, client, config, record): record 
                for record in config['records']
            }
            
            # 处理完成的任务
            for future in as_completed(future_to_record):
                record = future_to_record[future]
                try:
                    result = future.result(timeout=30)  # 30秒超时
                    if result:
                        success_count += 1
                except Exception as e:
                    record_name = f"{record['rr']}.{config['domain']}"
                    record_type = record['type']
                    logger.error(f"[{record_name}] 同步记录失败: {type(e).__name__}")
        
        duration = time.time() - start_time
        logger.info(f"同步完成: {success_count}/{total_records} 成功 ({duration:.1f}s)")
        return success_count > 0
    except Exception as e:
        logger.error(f"同步失败: {type(e).__name__}")
        return False

def sync_single_record(client, config, record):
    """同步单个记录"""
    record_name = f"{record['rr']}.{config['domain']}"
    record_type = record['type']
    
    try:
        # 获取当前IP
        logger.info(f"[{record_name}] 正在获取{record_type}地址...")
        ip = get_public_ip(record_type == 'AAAA')
        if not ip:
            logger.error(f"[{record_name}] 获取IP失败")
            return False
        
        # 查询现有记录
        existing = get_dns_record(client, config['domain'], record['rr'], record_type)
        if existing:
            if existing['Value'] == ip:
                logger.info(f"[{record_name}] IP未变化: {ip}")
                return True
            else:
                old_ip = existing['Value']
                if update_dns_record(client, existing, ip, config):
                    logger.info(f"[{record_name}] IP已更新: {old_ip} → {ip}")
                    return True
                else:
                    return False
        else:
            if create_dns_record(client, config['domain'], record['rr'], record_type, ip, config):
                logger.info(f"[{record_name}] 记录已创建: {ip}")
                return True
            else:
                return False
    except Exception as e:
        logger.error(f"[{record_name}] 处理记录时发生异常: {type(e).__name__}")
        return False

def main():
    """主函数 - 命令行入口"""
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description='阿里云 DDNS 客户端')
    parser.add_argument('-c', '--config', default='config.yaml', help='配置文件路径')
    parser.add_argument('-v', '--verbose', action='store_true', help='详细日志')
    
    args = parser.parse_args()
    
    # 配置日志
    setup_logging("logs/core.log", args.verbose)
    
    try:
        # 加载配置
        config = load_config(args.config)
        
        # 执行同步
        success = sync_records(config)
        return 0 if success else 1
    except Exception as e:
        log_message(f"程序执行失败: {type(e).__name__}", logging.ERROR)
        return 1

if __name__ == '__main__':
    exit(main())