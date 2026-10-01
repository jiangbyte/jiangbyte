---
title: "centos安装redis"
description: "CentOS 7 默认源里没有 Redis，得自己想办法。这篇整理了几种装法，从最省事的 Yum 到手动编译，看情况选就行。"
permalink: /blog/运维/redis/centos安装redis/
createTime: 2026-10-01
tags: ["运维"]
type: post
---
## 先说背景

CentOS 7 默认源里没有 Redis，得自己想办法。这篇整理了几种装法，从最省事的 Yum 到手动编译，看情况选就行。

## 方法一：Yum 装（最省事）

### 先加 EPEL 仓库

Redis 在 EPEL（Extra Packages for Enterprise Linux）里：

```bash
sudo yum install epel-release
```

### 然后直接装

```bash
sudo yum install redis
```

### 启动服务

```bash
sudo systemctl start redis
sudo systemctl enable redis
sudo systemctl status redis
```

## 方法二：编译安装（想要最新版本）

Yum 里的 Redis 版本一般比较老，想尝鲜就自己编译。

### 装编译工具

```bash
sudo yum groupinstall "Development Tools"
sudo yum install tcl
```

### 下载源码编译

```bash
cd /tmp
wget http://download.redis.io/redis-stable.tar.gz
tar xzf redis-stable.tar.gz
cd redis-stable
make
sudo make install
```

### 准备配置目录和数据目录

```bash
sudo mkdir /etc/redis
sudo mkdir /var/lib/redis
sudo cp redis.conf /etc/redis/
```

## 方法三：Remi 仓库装（折中方案）

Remi 仓库里有比较新的 Redis 版本，又不用自己编译：

```bash
sudo yum install https://rpms.remirepo.net/enterprise/remi-release-7.rpm
sudo yum --enablerepo=remi install redis
```

## 基本配置

### 改配置

```bash
sudo vi /etc/redis.conf
```

几个常用的配置项：

```
# 绑定 IP，0.0.0.0 表示允许所有 IP 访问
bind 0.0.0.0

# 保护模式（外网访问要关掉）
protected-mode no

# 密码（建议设一个）
requirepass your_password

# 持久化策略
save 900 1
save 300 10
save 60 10000
```

改完重启：

```bash
sudo systemctl restart redis
```

### 测试一下

```bash
redis-cli
127.0.0.1:6379> ping
PONG
127.0.0.1:6379> set test "Hello Redis"
OK
127.0.0.1:6379> get test
"Hello Redis"
```

### 防火墙放行（如果需要远程连）

```bash
sudo firewall-cmd --permanent --add-port=6379/tcp
sudo firewall-cmd --reload
```

## 安全配置

Redis 默认没有密码，裸奔很危险。几个基本操作：

### 设密码

```bash
requirepass your_strong_password
```

### 禁掉危险命令

```bash
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command CONFIG ""
```

### 限制绑定 IP

如果只在本机用，绑 `127.0.0.1` 就好：

```bash
bind 127.0.0.1
```

## 验证安装

```bash
# 看看版本
redis-server --version

# 跑个性能测试
redis-benchmark -q -n 100000
```

## 总结

- **图省事** → Yum + EPEL，一行搞定
- **要最新** → 编译安装，就是多等几分钟
- **想折中** → Remi 仓库，版本新又不用编译

生产环境记得设密码、绑 IP、禁危险命令，别裸奔。
