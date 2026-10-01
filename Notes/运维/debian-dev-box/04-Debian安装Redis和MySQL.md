---
title: "Debian安装Redis和MySQL"
date: 2026-10-01
draft: false
description: "本文要装的是 Oracle MySQL 和 Redis，不是 MariaDB。"
categories: ["运维"]
tags: ["运维"]
---
## 说明

本文要装的是 **Oracle MySQL** 和 **Redis**，不是 MariaDB。

Debian 自带仓库里的 `default-mysql-server` 实际会装成 **MariaDB**，**不要用那个包**。本机用 apt 装 MySQL 时，走 **MySQL 官方 APT 源**。

| 方式 | Redis | MySQL |
|---|---|---|
| **A. 软件源** | Debian 源 `redis-server` | MySQL 官方 APT → `mysql-community-server` |
| **B. Docker** | `redis:8.8.2` | `mysql:9.7.2` |

密码示例：`infra123!`（请改成自己的）。

**不要两套同时占 3306 / 6379。**

前置：

- [01 Linux 初始机](./01-linux初始机.md)
- [02 配置 Debian 软件源](./02-配置Debian软件源.md)
- 走 Docker 时还需 [03 Debian 中国源安装 Docker](./03-Debian中国源安装Docker.md)

---

## 方式 A：软件源安装（含密码配置）

### A0. 先清掉可能装过的 MariaDB（如有）

若以前误装过 `default-mysql-server` / `mariadb-*`，先卸干净，避免抢端口和混淆：

```bash
sudo systemctl stop mariadb mysql 2>/dev/null || true
sudo apt purge -y 'mariadb-*' 'default-mysql-*' 2>/dev/null || true
sudo apt autoremove -y
# 确认没有残留服务占 3306
sudo ss -tlnp | grep 3306 || echo '3306 free'
```

### A1. 安装 Redis（Debian 源）

```bash
sudo apt update
sudo apt install -y redis-server
sudo systemctl enable --now redis-server
sudo systemctl status redis-server --no-pager
```

未设密码时：

```bash
redis-cli ping
# PONG
```

### A2. 配置 Redis 密码

```bash
sudo vim /etc/redis/redis.conf
```

建议：

```conf
bind 127.0.0.1 -::1
requirepass infra123!
supervised systemd
appendonly yes
```

```bash
sudo systemctl restart redis-server

redis-cli ping
# (error) NOAUTH Authentication required.

redis-cli -a 'infra123!' ping
# PONG
```

或：

```bash
redis-cli
127.0.0.1:6379> AUTH infra123!
OK
```

数据默认在 `/var/lib/redis/`，配置在 `/etc/redis/redis.conf`。

### A3. 添加 MySQL 官方 APT 源

Debian 仓库里没有真正的 `mysql-server`，需要 Oracle 的配置包：

```bash
sudo apt update
sudo apt install -y wget gnupg lsb-release ca-certificates

cd /tmp
# 版本号以官网为准：https://dev.mysql.com/downloads/repo/apt/
wget https://dev.mysql.com/get/mysql-apt-config_0.8.34-1_all.deb
sudo DEBIAN_FRONTEND=noninteractive dpkg -i mysql-apt-config_0.8.34-1_all.deb
```

`dpkg -i` 若弹出交互界面：

1. 选 **MySQL Server & Cluster**
2. 选需要的系列（推荐 **mysql-8.4-lts** 或 **mysql-9.7-lts**，按项目要求）
3. 确认 Debian 代号；若列表暂无 `trixie`，可选相近的 `bookworm`，或等官方完整支持后重配
4. OK 退出

也可事后再改：

```bash
sudo dpkg-reconfigure mysql-apt-config
sudo apt update
```

确认源里已是社区版 MySQL，而不是 MariaDB：

```bash
apt-cache policy mysql-community-server
# Candidate 应来自 repo.mysql.com，而不是 mariadb
```

### A4. 安装 MySQL Community Server

```bash
sudo apt update
sudo apt install -y mysql-community-server
```

安装过程通常会提示设置 **root 密码**，直接设为例如 `infra123!`，认证插件选默认（MySQL 8+ 多为 `caching_sha2_password`）即可。

若安装未弹窗，装完后再设（见下一节）。

```bash
sudo systemctl enable --now mysql
sudo systemctl status mysql --no-pager
mysql --version
# 应显示 MySQL Community Server，而不是 MariaDB
```

Debian 13 若启动报缺 `libaio.so.1`，可先装兼容库并做符号链接后再启：

```bash
sudo apt install -y libaio1t64
sudo ln -sf /usr/lib/x86_64-linux-gnu/libaio.so.1t64 \
  /usr/lib/x86_64-linux-gnu/libaio.so.1
sudo systemctl restart mysql
```

### A5. 配置 / 修改 MySQL root 密码

**做法一：安全脚本**

```bash
sudo mysql_secure_installation
```

按提示设 root 密码、关远程 root、删测试库等。

**做法二：已能用 sudo 进库时（临时无密码或 socket）**

```bash
sudo mysql
```

```sql
ALTER USER 'root'@'localhost' IDENTIFIED BY 'infra123!';
FLUSH PRIVILEGES;
EXIT;
```

**做法三：忘记密码时（简要）**

```bash
sudo systemctl stop mysql
sudo mysqld --skip-grant-tables --user=mysql &
mysql -u root
```

```sql
FLUSH PRIVILEGES;
ALTER USER 'root'@'localhost' IDENTIFIED BY 'infra123!';
FLUSH PRIVILEGES;
EXIT;
```

```bash
sudo pkill mysqld
sudo systemctl start mysql
```

验证：

```bash
mysql -uroot -p'infra123!' -e "SELECT VERSION();"
# 版本字符串应含 MySQL，不含 MariaDB
```

### A6. 建库与业务用户

```bash
mysql -uroot -p'infra123!'
```

```sql
CREATE DATABASE app DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'app'@'localhost' IDENTIFIED BY 'infra123!';
GRANT ALL PRIVILEGES ON app.* TO 'app'@'localhost';
FLUSH PRIVILEGES;
```

### A7. 临时远程连接（MySQL 8.0+）

仅在调试需要时开放，用完立刻收回。MySQL 8.0 要求 **先建用户、再授权**，不能再写成老的 `GRANT ... IDENTIFIED BY` 一条龙。

**1）允许监听非本机（按需）**

```bash
sudo vim /etc/mysql/mysql.conf.d/mysqld.cnf
```

临时改成：

```conf
bind-address = 0.0.0.0
```

```bash
sudo systemctl restart mysql
```

若开了 UFW，再临时放行（示例）：

```bash
sudo ufw allow from 192.168.10.0/24 to any port 3306 proto tcp comment 'temp-mysql'
sudo ufw reload
```

**2）创建可从任意主机登录的 root（或专用账号）并授权**

```sql
-- 1. 先创建用户（8.0 要求分开写）
CREATE USER IF NOT EXISTS 'root'@'%' IDENTIFIED BY 'infra123!';

-- 2. 再授权
GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' WITH GRANT OPTION;

-- 3. 刷新权限
FLUSH PRIVILEGES;
```

更稳妥是用业务账号而不是 `root@'%'`，例如：

```sql
CREATE USER IF NOT EXISTS 'app'@'%' IDENTIFIED BY 'infra123!';
GRANT ALL PRIVILEGES ON app.* TO 'app'@'%';
FLUSH PRIVILEGES;
```

其他机器测试：

```bash
mysql -h <本机局域网IP> -uroot -p'infra123!' -e "SELECT 1;"
```

**3）用完撤销（务必做）**

```sql
REVOKE ALL PRIVILEGES ON *.* FROM 'root'@'%';
FLUSH PRIVILEGES;

-- 若不再需要该账号，可直接删掉
DROP USER IF EXISTS 'root'@'%';
FLUSH PRIVILEGES;
```

然后把 `bind-address` 改回 `127.0.0.1` 并重启 MySQL；UFW 临时规则也删掉：

```bash
sudo ufw status numbered
# sudo ufw delete <规则编号>
sudo systemctl restart mysql
```

### A8. 默认只绑本机（日常）

```bash
sudo vim /etc/mysql/mysql.conf.d/mysqld.cnf
```

```conf
bind-address = 127.0.0.1
```

```bash
sudo systemctl restart mysql
```

### A9. apt 方式常用命令

```bash
sudo systemctl restart redis-server
sudo journalctl -u redis-server -e

sudo systemctl restart mysql
sudo journalctl -u mysql -e
```

数据目录默认：`/var/lib/mysql/`；配置：`/etc/mysql/`。

---

## 方式 B：Docker 安装（固定版本 + datas 持久化）

| 服务 | 镜像 | 宿主机数据 | 端口 | 重启策略 |
|---|---|---|---|---|
| MySQL | `mysql:9.7.2` | `~/Workspace/datas/mysql` | 3306 | `unless-stopped` |
| Redis | `redis:8.8.2` | `~/Workspace/datas/redis` | 6379 | `unless-stopped` |

### B1. 准备目录

```bash
mkdir -p ~/Workspace/datas/{mysql,redis}
```

从旧 volume 迁移时：

```bash
# sudo chown -R 999:999 ~/Workspace/datas/mysql
# sudo chown -R 999:999 ~/Workspace/datas/redis
```

### B2. MySQL 9.7.2

```bash
docker run -d --name mysql \
  -p 3306:3306 \
  -e MYSQL_ROOT_PASSWORD='infra123!' \
  -v /home/charlie/Workspace/datas/mysql:/var/lib/mysql \
  --restart unless-stopped \
  mysql:9.7.2
```

```bash
docker exec mysql mysqladmin ping -uroot -p'infra123!' --silent
docker exec -it mysql mysql -uroot -p'infra123!'
```

```sql
SHOW DATABASES;
CREATE DATABASE app DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

连接：`127.0.0.1:3306` / `root` / `infra123!`

临时远程时：SQL 与方式 A 的 **A7** 相同（`CREATE USER 'root'@'%'` → `GRANT` → `FLUSH`；用完 `REVOKE` / `DROP USER`）。Docker 侧把端口从 `127.0.0.1:3306` 临时改成 `0.0.0.0:3306`（或保持 `3306:3306`），UFW / `DOCKER-USER` 同步放开可信网段，用完改回。

### B3. Redis 8.8.2

官方镜像不会自动把 `REDIS_PASSWORD` 变成 `requirepass`，密码写在参数里，并开 AOF：

```bash
docker run -d --name redis \
  -p 6379:6379 \
  -e REDIS_PASSWORD='infra123!' \
  -v /home/charlie/Workspace/datas/redis:/data \
  --restart unless-stopped \
  redis:8.8.2 \
  --requirepass "infra123!" --appendonly yes
```

```bash
docker exec redis redis-cli -a 'infra123!' ping
docker exec redis redis-cli -a 'infra123!' SET hello world
ls -la ~/Workspace/datas/redis
```

### B4. Docker 运维

```bash
docker ps -a --filter name='mysql|redis'
docker logs -f mysql
docker restart mysql redis
docker stop mysql redis && docker start mysql redis
```

删容器可保留数据：不要删 `~/Workspace/datas/{mysql,redis}`。

### B5. 从命名卷迁到 datas（可选）

```bash
docker stop mysql
sudo rsync -aHAX /var/lib/docker/volumes/mysql_data/_data/ \
  /home/charlie/Workspace/datas/mysql/
sudo chown -R 999:999 /home/charlie/Workspace/datas/mysql
docker rm mysql
# 再按 B2 启动
docker volume rm mysql_data   # 确认无误后
```

### B6. 端口安全

仅本机访问时：

```bash
-p 127.0.0.1:3306:3306
-p 127.0.0.1:6379:6379
```

---

## 怎么选

| 需求 | 建议 |
|---|---|
| 系统服务、`systemctl` 管理、官方 MySQL | **方式 A**（MySQL APT + Debian Redis） |
| 版本钉死、数据放 `Workspace/datas`、好搬家 | **方式 B（Docker）** |

再次强调：**不要用 `apt install default-mysql-server`，那会变成 MariaDB。**

## 小结

**方式 A：** Redis → Debian `redis-server` + `requirepass`；MySQL → `mysql-apt-config` + `mysql-community-server`，安装时或 `ALTER USER` / `mysql_secure_installation` 设 root 密码。

**方式 B：** `mysql:9.7.2` / `redis:8.8.2`，密码用环境变量或 `--requirepass`，数据 bind 到 `~/Workspace/datas`，`--restart unless-stopped`。
