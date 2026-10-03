---
date: 2026-10-01
description: "新装或刚到手的 Debian 开发机，先把「能正常干活」的底子铺好，再去改软件源、装 Docker、跑 MySQL / Redis。"
categories: ["运维"]
tags: ["运维"]
---

## 目标

新装或刚到手的 **Debian** 开发机，先把「能正常干活」的底子铺好，再去改软件源、装 Docker、跑 MySQL / Redis。

本文以 **Debian 13 (trixie) + 图形桌面（如 XFCE）** 为例，命令对服务器版同样适用（跳过桌面相关即可）。

建议阅读顺序：

1. 本文：01 Linux 初始机
2. [配置 Debian 软件源](./配置Debian软件源.md)
3. [Debian 中国源安装 Docker](./Debian中国源安装Docker.md)
4. [Debian 安装 Redis 和 MySQL](./Debian安装Redis和MySQL.md)

## 确认系统

```bash
cat /etc/os-release
uname -r
hostnamectl
```

关注：

- `VERSION_CODENAME`（如 `trixie`）——后面写源、装 Docker 都要用
- 架构一般为 `x86-64` / `amd64`

## 用户与 sudo

安装时若已创建普通用户并勾选 sudo，可跳过。否则：

```bash
su -
apt update
apt install -y sudo
usermod -aG sudo 你的用户名
```

注销重登后验证：

```bash
sudo -v
whoami
```

开发机建议：**日常用普通用户，需要提权再 `sudo`**，不要长期挂在 root 图形会话里。

## 基础工具包

```bash
sudo apt update
sudo apt install -y \
  curl wget ca-certificates gnupg \
  git vim htop tree unzip \
  net-tools iproute2 dnsutils \
  build-essential \
  lm-sensors
```

按需再加：

```bash
# 压缩 / 磁盘
sudo apt install -y p7zip-full ncdu

# 终端体验
sudo apt install -y tmux fzf ripgrep
```

## 时区与语言

```bash
# 时区（上海）
sudo timedatectl set-timezone Asia/Shanghai
timedatectl

# 中文环境（桌面常用）
sudo apt install -y locales
sudo dpkg-reconfigure locales
# 勾选 zh_CN.UTF-8，并设为默认
```

当前 shell 可先：

```bash
echo 'export LANG=zh_CN.UTF-8' >> ~/.bashrc
```

## 目录习惯（开发机）

后面 Docker 数据、项目都会落到固定路径，建议一开始就定好，例如：

```bash
mkdir -p ~/Workspace/{projects,datas}
mkdir -p ~/Workspace/datas/{mysql,redis,silo,ngnix}
```

约定示例：

| 路径 | 用途 |
|---|---|
| `~/Workspace/projects` | 代码仓库 |
| `~/Workspace/datas` | 容器/服务持久化（MySQL、Redis、对象存储、nginx 配置等） |

不要把数据库目录随手丢在 `/tmp` 或家目录乱七八糟的位置。

## SSH（可选）

笔记本纯本机开发可以不装。若需要远程连进来：

```bash
sudo apt install -y openssh-server
sudo systemctl enable --now ssh
sudo ss -tlnp | grep ':22'
```

**务必配密钥登录，并配合防火墙只放行可信来源。** 开发本默认对外暴露 22 风险较大。

## 图形会话小提示（XFCE）

- 电源管理：插电 / 电池都把自动挂起、熄屏调到合适值（长期编译、下载时建议 Never）
- 输入法：`fcitx5` + 中文插件是常见组合
- 浏览器 / IDE 用官方 `.deb` 或厂商源即可，装完记到 `sources.list.d`，方便以后升级

更细的桌面整理（熄屏、AppMenu、UFW）见：[Debian 13 XFCE 开发机整理](../Debian 13 XFCE 开发机整理：熄屏、软件源、全局菜单与防火墙.md)

## 做完初始机之后

```bash
# 系统是否健康
uptime
free -h
df -h
```

然后进入下一步：**换成国内软件源**，否则 `apt upgrade` 和后续装 Docker 会又慢又容易超时。
