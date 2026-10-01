---
title: "ubuntu安装redis"
date: 2026-10-01
draft: false
description: "Ubuntu 比 CentOS 省心点，APT 源里直接有 Redis，不用额外加仓库。不过版本可能不是最新的，想尝鲜还是得自己编译。"
categories: ["运维"]
tags: ["运维"]
---
## 先说背景

Ubuntu 比 CentOS 省心点，APT 源里直接有 Redis，不用额外加仓库。不过版本可能不是最新的，想尝鲜还是得自己编译。

## 方法一：APT 装（最省事）

### 更新源然后直接装

```bash
sudo apt update
sudo apt install redis-server
```

### 启动服务

```bash
sudo systemctl start redis-server
sudo systemctl enable redis-server
sudo systemctl status redis-server
```

## 方法二：编译安装（想要最新版本）

APT 里的版本一般落后一两个大版本，想用最新的就自己编译。

### 装编译工具

```bash
sudo apt update
sudo apt install build-essential tcl
```

### 下载源码编译

```bash
cd /tmp
wget https://download.redis.io/redis-stable.tar.gz
tar -xzvf redis-stable.tar.gz
cd redis-stable
make
sudo make install
```

### 准备配置目录

```bash
sudo mkdir /etc/redis
sudo mkdir /var/redis
sudo cp redis.conf /etc/redis/
```

## 基本配置

### 测试连接

```bash
redis-cli
127.0.0.1:6379> ping
PONG
127.0.0.1:6379> set test "hello"
OK
127.0.0.1:6379> get test
"hello"
127.0.0.1:6379> exit
```

### 改配置

```bash
sudo nano /etc/redis/redis.conf
```

几个常用的：

```
bind 127.0.0.1       # 绑定 IP
port 6379            # 端口
requirepass yourpassword  # 密码
daemonize yes        # 后台运行
```

改完重启：

```bash
sudo systemctl restart redis-server
```

## 安全配置

### 设密码

```bash
requirepass your_strong_password
```

### 禁危险命令

```bash
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command CONFIG ""
```

### 防火墙

```bash
sudo ufw allow from your_ip to any port 6379
```

## 验证安装

```bash
redis-server --version
redis-benchmark -q -n 100000
```

## 总结

- **图省事** → APT 直接装，一行搞定
- **要最新** → 编译安装，多等几分钟

Ubuntu 比 CentOS 舒服的地方就是 APT 源自带 Redis，不用折腾仓库。生产环境一样要设密码、绑 IP、禁危险命令。
