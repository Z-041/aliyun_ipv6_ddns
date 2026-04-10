# 阿里云 DDNS 客户端

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

一个基于阿里云 API 的动态域名解析（DDNS）工具，支持系统托盘图形界面和命令行两种使用方式。能够自动检测公网 IP 地址变化，并及时更新阿里云 DNS 记录，确保域名始终指向最新的公网 IP 地址。

支持 IPv4 (A 记录) 和 IPv6 (AAAA 记录) 的动态解析。

## 功能特性

- **自动同步**：按照预设时间间隔自动检测公网 IP 变化，同步到阿里云 DNS
- **手动同步**：通过系统托盘菜单手动触发 IP 同步
- **配置编辑**：直接在系统托盘中打开配置文件进行编辑
- **记录查看**：查看当前阿里云 DNS 记录详情
- **配置验证**：使用 Pydantic 进行严格的配置验证，确保配置正确
- **类型安全**：完整的类型注解，支持 mypy 严格模式检查
- **多记录支持**：并发处理多个 DNS 记录，提高同步效率
- **智能 IP 获取**：自动选择最快的 IP 查询服务，支持缓存

## 项目结构

```
aliyun_ipv6_ddns/
├── src/
│   └── aliyun_ddns/
│       ├── __init__.py          # 包导出
│       ├── cli.py               # CLI 入口
│       ├── core.py              # 核心 DDNS 逻辑
│       ├── gui.py               # 系统托盘 GUI
│       ├── models/
│       │   ├── __init__.py
│       │   └── config.py        # Pydantic 配置模型
│       ├── services/
│       │   ├── __init__.py
│       │   ├── dns.py           # DNS 服务抽象和阿里云实现
│       │   └── ip.py            # IP 获取服务
│       └── utils/
│           ├── __init__.py
│           ├── logging.py       # 日志工具
│           └── retry.py         # 重试装饰器
├── tests/                       # 测试套件
│   ├── unit/                    # 单元测试
│   └── integration/             # 集成测试
├── pyproject.toml               # 现代 Python 项目配置
├── setup.py                     # 兼容安装脚本
├── requirements.txt             # 依赖列表
├── config.yaml.example          # 配置示例
└── README.md
```

## 安装

### 从源码安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/aliyun-ddns.git
cd aliyun-ddns

# 安装依赖
pip install -r requirements.txt

# 开发模式安装（推荐）
pip install -e .

# 或安装开发依赖
pip install -e ".[dev]"
```

### 依赖要求

- Python >= 3.9
- 阿里云 Python SDK
- PyYAML
- Pydantic >= 2.0
- pystray (GUI 模式)
- Pillow (GUI 模式)

## 配置说明

### 首次运行

首次运行时会自动创建默认配置文件 `config.yaml`，请编辑该文件填入您的阿里云 AccessKey 信息：

```bash
# GUI 模式（推荐）
aliyun-ddns-gui

# 或命令行模式
aliyun-ddns
```

### 配置文件

编辑 `config.yaml` 文件：

```yaml
access_key_id: 'your-access-key-id'
access_key_secret: 'your-access-key-secret'
domain: example.com
records:
  - rr: '@'
    type: 'A'      # IPv4 记录
    ttl: 600
  - rr: 'www'
    type: 'AAAA'   # IPv6 记录
    ttl: 600
region: cn-hangzhou
interval: 300      # 自动同步间隔（秒）
ttl: 600           # 默认 DNS 记录 TTL（秒）
```

### 配置项说明

| 配置项 | 必填 | 说明 |
|--------|------|------|
| `access_key_id` | 是 | 阿里云 AccessKey ID |
| `access_key_secret` | 是 | 阿里云 AccessKey Secret |
| `domain` | 是 | 要解析的域名 |
| `records` | 是 | DNS 记录列表 |
| `records.rr` | 是 | 主机记录，如 `@`、`www`、`home` |
| `records.type` | 是 | 记录类型：`A` (IPv4) 或 `AAAA` (IPv6) |
| `records.ttl` | 否 | 单个记录的 TTL，默认使用全局 TTL |
| `region` | 否 | 阿里云区域，默认 `cn-hangzhou` |
| `interval` | 否 | 自动同步间隔（秒），默认 300，范围 60-86400 |
| `ttl` | 否 | 默认 TTL（秒），默认 600，范围 60-86400 |

### 获取阿里云 AccessKey

1. 登录 [阿里云控制台](https://console.aliyun.com/)
2. 点击右上角头像 -> AccessKey 管理
3. 创建 AccessKey 并保存好 ID 和 Secret
4. 建议创建子账号，赋予最小权限（AliyunDNSFullAccess）

## 使用方法

### GUI 模式（推荐）

```bash
aliyun-ddns-gui
```

启动后会在系统托盘显示图标：
- **绿色**：同步成功
- **橙色**：配置无效
- **红色**：同步失败

右键菜单功能：
- **立即同步**：手动触发同步
- **查看记录**：查看当前 DNS 记录
- **编辑配置**：打开配置文件编辑
- **退出**：关闭程序

### 命令行模式

```bash
# 使用默认配置
aliyun-ddns

# 指定配置文件
aliyun-ddns -c /path/to/config.yaml

# 启用详细日志
aliyun-ddns -v

# 查看帮助
aliyun-ddns --help
```

### 退出码说明

| 退出码 | 说明 |
|--------|------|
| 0 | 成功 |
| 1 | 一般错误 |
| 2 | 配置文件不存在 |
| 3 | 配置验证失败 |

## 开发

### 运行测试

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest tests/unit

# 运行集成测试
pytest tests/integration

# 生成覆盖率报告
pytest --cov=src/aliyun_ddns --cov-report=html
```

### 代码格式化

```bash
# 使用 black 格式化
black src tests

# 使用 ruff 检查
ruff check src tests

# 使用 mypy 类型检查
mypy src/aliyun_ddns
```

### 项目架构

本项目采用分层架构设计：

```
┌─────────────────────────────────────┐
│           Presentation              │
│    (GUI / CLI)                      │
├─────────────────────────────────────┤
│           Service Layer             │
│    (DDNSService / IPService)        │
├─────────────────────────────────────┤
│           Data Access               │
│    (AliyunDNSProvider)              │
├─────────────────────────────────────┤
│           Models                    │
│    (Config / DNSRecord)             │
└─────────────────────────────────────┘
```

- **Models**: Pydantic 数据模型，负责配置验证
- **Services**: 业务逻辑层，实现核心功能
- **Providers**: 数据访问抽象，便于扩展其他 DNS 服务商

## 安全性说明

- 使用阿里云官方 SDK 进行 API 调用，确保通信安全
- 敏感信息（AccessKey）不会记录到日志中
- 配置文件应妥善保管，避免泄露
- 建议使用具有最小权限的子账号 AccessKey
- 不要将 `config.yaml` 提交到版本控制（已添加到 `.gitignore`）

## 常见问题

### Q: 配置验证失败，提示 AccessKey 格式不正确？
A: 请确保：
1. 已替换 `YOUR_ACCESS_KEY_ID` 和 `YOUR_ACCESS_KEY_SECRET` 为真实值
2. AccessKey ID 长度至少 10 个字符
3. 没有多余的空格

### Q: 托盘图标没有显示？
A: 
1. 检查是否已安装 `pystray` 和 `Pillow`
2. Windows 系统请检查任务栏设置，确保图标未被隐藏
3. 查看日志文件 `logs/gui.log` 获取详细错误信息

### Q: 如何支持其他 DNS 服务商？
A: 实现 `DNSProvider` 抽象接口：

```python
from aliyun_ddns.services.dns import DNSProvider

class MyDNSProvider(DNSProvider):
    def get_record(self, domain, rr, record_type): ...
    def update_record(self, record_id, rr, record_type, value, ttl): ...
    def create_record(self, domain, rr, record_type, value, ttl): ...
```

## 更新日志

### v2.2.0
- 重构项目架构，采用现代 Python 项目结构
- 使用 Pydantic 进行配置验证
- 添加完整的类型注解
- 新增单元测试和集成测试
- 优化 GUI 配置无效时的提示

### v2.1.0
- 添加 IPv6 支持
- 优化 IP 获取策略
- 添加线程池并发处理

## 许可证

[MIT License](LICENSE)

## 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 致谢

- [阿里云 Python SDK](https://github.com/aliyun/aliyun-openapi-python-sdk)
- [pystray](https://github.com/moses-palmer/pystray)
- [Pydantic](https://docs.pydantic.dev/)
