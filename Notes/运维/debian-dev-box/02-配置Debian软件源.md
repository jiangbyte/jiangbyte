---
title: "配置Debian软件源"
date: 2026-10-01
draft: false
description: "默认 deb.debian.org 在国内经常慢或不稳。开发机建议："
categories: ["运维"]
tags: ["运维"]
---
## 为什么要改源

默认 `deb.debian.org` 在国内经常慢或不稳。开发机建议：

- **软件包、更新、backports** → 中科大镜像（也可换清华、北外、阿里云等）
- **安全更新** → 继续用官方 `security.debian.org`（更及时）

同时要避免把 **sid（unstable）**、旧版 **bullseye** 和当前稳定版写进同一套默认源，否则 `apt list --upgradable` 会刷出上千个包，一不小心就把桌面拖进滚动版。

## 1. 备份

```bash
sudo cp /etc/apt/sources.list /etc/apt/sources.list.bak.$(date +%Y%m%d%H%M%S)
```

确认代号：

```bash
. /etc/os-release && echo "$VERSION_CODENAME"
# Debian 13 → trixie
```

下文以 **trixie** 为例，其他版本替换代号即可。

## 2. 推荐的 sources.list

以**中国科学技术大学（USTC）**镜像为例：

```bash
sudo tee /etc/apt/sources.list >/dev/null <<'EOF'
deb https://mirrors.ustc.edu.cn/debian/ trixie main contrib non-free non-free-firmware
deb https://mirrors.ustc.edu.cn/debian/ trixie-updates main contrib non-free non-free-firmware
deb https://mirrors.ustc.edu.cn/debian/ trixie-backports main contrib non-free non-free-firmware

# 安全更新建议走官方
deb https://security.debian.org/debian-security trixie-security main contrib non-free non-free-firmware
EOF
```

镜像站文档：<https://mirrors.ustc.edu.cn/help/debian.html>  
若改用其他镜像，把主机名换成例如 `mirrors.tuna.tsinghua.edu.cn`、`mirrors.bfsu.edu.cn`、`mirrors.aliyun.com` 即可。

说明：

| 行 | 作用 |
|---|---|
| `trixie` | 主仓库 |
| `trixie-updates` | 稳定版点更前的更新 |
| `trixie-backports` | 较新软件（优先级低，不会默认抢走全系统） |
| `trixie-security` | 安全补丁 |

`non-free` / `non-free-firmware` 笔记本固件、部分驱动会用到，桌面机建议带上。

## 3. 不要混进这些

以下内容应注释或删除：

```text
# 危险：会把系统往 unstable 拉
# deb http://ftp.de.debian.org/debian sid main

# 危险：旧稳定版和当前版混用
# deb http://deb.debian.org/debian bullseye main ...
```

临时需要某个 sid 包时，用 **pinning** 或单独下载 deb，不要把 sid 当成默认源长期开着。

## 4. 刷新并检查

```bash
sudo apt update
apt list --upgradable
```

可升级数量应是「正常个位数到几十」，而不是一千多个且候选版本来自 `unstable`。

查看某个包从哪来：

```bash
apt-cache policy firefox-esr
apt-cache policy linux-image-amd64
```

`Candidate` 应落在 `trixie` / `trixie-security`，而不是 `sid`。

## 5. 升级怎么升才稳

```bash
# 安全、常规：在当前发行版内升级
sudo apt upgrade -y

# 会处理依赖变化、可能卸包，开发机慎用、先看模拟
apt-get -s full-upgrade
# sudo apt full-upgrade
```

内核、浏览器等安全更新后如提示重启：

```bash
[ -f /var/run/reboot-required ] && cat /var/run/reboot-required.pkgs
```

## 6. 第三方源（可选）

Chrome、VS Code、Docker 等通常写在 `/etc/apt/sources.list.d/`，与系统源分离，互不影响。例如：

```bash
ls /etc/apt/sources.list.d/
```

Docker 的中国源安装见下一篇。

## 小结

- 主源用中科大镜像（`mirrors.ustc.edu.cn`），安全源用官方  
- **只保留当前代号**（如 trixie），别混 sid / 旧版  
- 日常 `apt upgrade`，不要被「上千个 upgradable」吓去盲升 unstable  

下一篇：[03 Debian 中国源安装 Docker](./03-Debian中国源安装Docker.md)
