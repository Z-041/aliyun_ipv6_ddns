# 阿里云 DDNS 客户端

## 项目概述

本项目是一个基于阿里云 API 的动态域名解析（DDNS）工具，具备图形化用户界面（GUI），通过系统托盘图标提供便捷操作。它能够自动检测公网 IP 地址的变化，并及时更新阿里云 DNS 记录，确保域名始终指向最新的公网 IP 地址。

支持 IPv4 (A 记录) 和 IPv6 (AAAA 记录) 的动态解析。

## 功能特性

- **自动同步**：按照预设的时间间隔自动检测公网 IP 变化，并同步到阿里云 DNS 记录。
- **手动同步**：支持通过系统托盘菜单手动触发 IP 同步操作。
- **配置编辑**：可以直接在系统托盘菜单中打开配置文件进行编辑。
- **记录查看**：方便查看当前阿里云 DNS 记录的详细信息。
- **配置更新提醒**：当配置文件发生更改时，会自动重新加载并给出通知。

## 安全性说明

- 项目使用阿里云官方 SDK 进行 API 调用，确保通信安全
- 敏感信息（如 access_key_id 和 access_key_secret）不会记录到日志中
- 配置文件应妥善保管，避免泄露敏感信息
- 建议使用具有最小权限的子账号访问密钥

## 安装

```bash
pip install -r requirements.txt
```

## 配置说明

在项目根目录下，有一个 `config.yaml` 文件，用于配置阿里云账号信息和 DNS 记录。为了安全起见，项目提供了 `config.yaml.example` 示例文件，请复制该文件并修改为您自己的配置：

```bash
cp config.yaml.example config.yaml
```

然后编辑 `config.yaml` 文件，填入您的阿里云访问密钥和域名信息：

```yaml
access_key_id: 'your-access_key_id'
access_key_secret: 'your-access_key_secret'
domain: your-domain.com
records:
  - rr: '@'
    type: 'A'  # 或 'AAAA' 用于 IPv6
interval: 300  # 自动同步间隔（秒）
ttl: 600       # DNS 记录 TTL（秒）
```

配置项说明：
- `access_key_id` 和 `access_key_secret`：阿里云账号的访问密钥，用于身份验证。
- `domain`：要进行动态解析的域名。
- `records`：一个列表，包含要同步的 DNS 记录。每个记录包含 `rr`（主机记录）和 `type`（记录类型，支持 `A` 和 `AAAA`）。
- `interval`：自动同步的时间间隔，单位为秒，默认为 300 秒。
- `ttl`：DNS 记录的生存时间，单位为秒，默认为 600 秒。

## 使用方法

### 命令行模式

```bash
aliyun-ddns-core
```

### GUI 模式

```bash
aliyun-ddns-gui
```

程序启动后，会在系统托盘显示一个图标，右键单击该图标可以进行各种操作：
- **立即同步**：手动触发公网 IP 同步到阿里云 DNS 记录。
- **查看记录**：查看当前阿里云 DNS 记录的详细信息。
- **编辑配置**：打开 `config.yaml` 文件进行编辑。
- **退出**：关闭程序。

## 开发

### 项目结构

```
aliyun_ddns/
├── aliyun_ddns/
│   ├── __init__.py
│   ├── core.py         # 核心功能模块
│   ├── gui.py          # 图形界面模块
│   └── utils.py        # 工具函数模块
├── logs/               # 日志文件目录
├── config.yaml         # 配置文件（请勿提交到版本控制）
├── config.yaml.example # 配置文件示例
├── requirements.txt    # 依赖列表
├── setup.py            # 安装脚本
└── README.md
```

## 性能优化

- 使用线程池并发处理多个 DNS 记录，提高同步效率
- 实现智能 IP 获取策略，自动选择最快的 IP 查询服务
- 采用缓存机制避免频繁请求相同的 IP 地址
- 优化重试机制，智能处理网络异常

## 注意事项

- 请确保你的阿里云账号具有足够的权限来管理 DNS 记录。
- 如果在使用过程中遇到问题，可以查看日志文件以获取更多详细信息。
- 配置文件修改后，程序会自动检测并重新加载配置。
- 请勿将包含敏感信息的 config.yaml 文件提交到版本控制系统。