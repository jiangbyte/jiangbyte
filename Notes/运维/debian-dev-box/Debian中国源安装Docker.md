---
title: "Debian中国源安装Docker"
date: 2026-10-01
draft: false
description: "已配好 Debian 软件源（见 02 配置 Debian 软件源） 确认代号："
categories: ["运维"]
tags: ["运维"]
---
## 前置

- 已配好 Debian 软件源（见 [配置 Debian 软件源](./配置Debian软件源.md)）
- 确认代号：

```bash
. /etc/os-release && echo "$VERSION_CODENAME"
# 本文按 trixie 写；bookworm 等把下面 URL 里的代号一并改掉
```

不要用发行版仓库里过时的 `docker.io` 凑合（可以跑，但版本和管理源往往不如官方 CE 清晰）。开发机推荐 **Docker CE + 国内镜像**。

## 依赖与 GPG 密钥

```bash
sudo apt update
sudo apt install -y ca-certificates curl

sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/debian/gpg \
  -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
```

若阿里云 GPG 地址异常，可用 Docker 官方密钥再继续用阿里云软件源（密钥与仓库可分开）。

## 添加阿里云 Docker CE 源

```bash
. /etc/os-release
echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://mirrors.aliyun.com/docker-ce/linux/debian ${VERSION_CODENAME} stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list
```

Debian 13 上生效后类似：

```text
deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://mirrors.aliyun.com/docker-ce/linux/debian trixie stable
```

## 安装 Docker Engine

```bash
sudo apt update
sudo apt install -y \
  docker-ce \
  docker-ce-cli \
  containerd.io \
  docker-buildx-plugin \
  docker-compose-plugin
```

开机自启并立刻启动：

```bash
sudo systemctl enable --now docker
sudo systemctl status docker --no-pager
```

## 当前用户免 sudo

```bash
sudo usermod -aG docker "$USER"
```

**注销重新登录**（或重启）后再测：

```bash
docker version
docker run --rm hello-world
```

## 配置镜像加速（拉镜像用）

把加速器写进 daemon 配置（示例为阿里云；也可换中科大、DaoCloud 等）：

```bash
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json >/dev/null <<'EOF'
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io"
  ],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "3"
  }
}
EOF

sudo systemctl daemon-reload
sudo systemctl restart docker
docker info | grep -A5 'Registry Mirrors'
```

加速器地址会随服务商变更，以你账号控制台或镜像站文档为准。

## 常用自检

```bash
docker info
docker compose version
docker ps -a
```

数据盘与项目目录建议分开，例如：

```bash
mkdir -p ~/Workspace/datas
```

容器业务数据（MySQL、Redis、对象存储等）优先 bind 到 `~/Workspace/datas/...`，不要只依赖匿名卷，方便备份和迁移。

## 和防火墙的关系（开发机）

UFW 默认拒入站时，**Docker 映射到 `0.0.0.0` 的端口仍可能被局域网访问**（走 FORWARD/DNAT，不经 UFW 的 INPUT）。开发本若只想本机用：

- 映射写成 `-p 127.0.0.1:3306:3306`，或  
- 在 `DOCKER-USER` 链限制外网访问（见 XFCE 开发机整理一文中的防火墙小节）

## 小结

| 步骤 | 要点 |
|---|---|
| 源 | `mirrors.aliyun.com/docker-ce` + 当前 Debian 代号 |
| 包 | `docker-ce` 及 cli / containerd / buildx / compose 插件 |
| 权限 | 用户进 `docker` 组后重登 |
| 加速 | `/etc/docker/daemon.json` 的 `registry-mirrors` |

下一篇用 Docker 在本机落 **Redis + MySQL**（开机自启、数据在 `Workspace/datas`）：[Debian 安装 Redis 和 MySQL](./Debian安装Redis和MySQL.md)
