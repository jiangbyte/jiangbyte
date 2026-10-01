## 先说背景

CentOS 7 自带的包管理是 Yum 不是 Dnf，而且官方源里没有 MySQL，得自己加仓库。这篇文章就是我在 CentOS 7 上装 MySQL 的完整记录，包括几种不同的安装方式，方便下次忘了回来看。

## 先看看系统版本

```bash
cat /etc/redhat-release
hostnamectl
```

输出是 `CentOS Linux release 7.x` 就没问题。如果是 8 或 9 那包管理就变成 Dnf 了，步骤不太一样。

## 安装前要确认的事

- 你有 `sudo` 权限
- 机器能联网（离线场景下面有单独的方法）
- 防火墙要不要开 3306 端口看你自己需求

## 方法一：用 Yum 装（最省事）

### 先把仓库加上

Oracle 官方准备好了 RPM 包，一行命令搞定：

```bash
sudo yum install -y https://dev.mysql.com/get/mysql80-community-release-el7-11.noarch.rpm
```

装完之后系统里会多一个 `/etc/yum.repos.d/mysql-community.repo`，里面有好几个子仓库，默认启用的是 MySQL 8.0。

### 想换版本的话

| 仓库名 | 版本 | 说明 |
|--------|------|------|
| mysql80-community | 8.0.x | 当前 LTS，推荐 |
| mysql57-community | 5.7.x | 老 LTS，快停止维护了 |
| mysql-innovation-community | 8.x / 9.x | 尝鲜版 |

切版本就是开关仓库的事：

```bash
sudo yum-config-manager --disable mysql80-community
sudo yum-config-manager --enable mysql57-community
```

> 如果提示找不到 `yum-config-manager`，先装一下 `sudo yum install -y yum-utils`。

### 正式安装

```bash
sudo yum install -y mysql-community-server
```

装完可以看看装了些啥：

```bash
rpm -qa | grep mysql-
```

### 启动服务

```bash
sudo systemctl start mysqld
sudo systemctl enable mysqld
sudo systemctl status mysqld
```

### 找到临时密码

MySQL 8.0 第一次启动的时候会自动生成一个临时 root 密码，记在日志里：

```bash
sudo grep 'temporary password' /var/log/mysqld.log
```

### 跑一下安全配置

```bash
sudo mysql_secure_installation
```

这个脚本会一步步引导你：
- 改 root 密码
- 删匿名用户
- 禁止 root 远程登录
- 删测试数据库
- 重载权限表

### 登录试试

```bash
mysql -u root -p
```

进去之后可以看看版本和运行时间：

```sql
SELECT VERSION();
SHOW STATUS LIKE 'Uptime';
```

## 方法二：用 Docker 装（最干净）

如果 Yum 仓库连不上或者不想污染系统，Docker 是最省心的选择。

```bash
# 先装 Docker
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker

# 拉 MySQL 镜像跑起来
sudo docker run -d \
  --name mysql \
  -e MYSQL_ROOT_PASSWORD=your_password \
  -p 3306:3306 \
  -v /mysql-data:/var/lib/mysql \
  mysql:8.0
```

| 参数 | 什么意思 |
|------|---------|
| `-d` | 后台跑 |
| `--name` | 给容器起个名 |
| `-e MYSQL_ROOT_PASSWORD` | 设 root 密码（第一次启动必填） |
| `-p 3306:3306` | 宿主机 3306 映射到容器 3306 |
| `-v /mysql-data:/var/lib/mysql` | 数据挂到宿主机，删容器不会丢数据 |

想换版本就改镜像标签，`mysql:5.7`、`mysql:9.0` 都行。

验证跑没跑起来：

```bash
sudo docker ps
sudo docker exec mysql mysql -u root -p -e "SELECT VERSION();"
```

## 方法三：离线装（手工 RPM）

公司内网机子连不了外网的话，在有网的机器上下好包带过去：

```bash
# 下载完整 bundle
wget https://dev.mysql.com/get/Downloads/MySQL-8.0/mysql-8.0.40-1.el7.x86_64.rpm-bundle.tar

# 解压安装
tar -xvf mysql-8.0.40-1.el7.x86_64.rpm-bundle.tar
sudo yum install -y mysql-community-*.rpm
```

注意离线装可能缺依赖（比如 `libaio`、`numactl`），提前准备好就行。

## 踩过的坑

### GPG 密钥报错

```bash
sudo rpm --import https://repo.mysql.com/RPM-GPG-KEY-mysql
```

### 和 MariaDB 冲突

CentOS 7 默认带着 MariaDB，不卸掉会冲突：

```bash
sudo yum remove -y mariadb-libs
```

### 日志怎么看

出了问题先翻日志：

```bash
sudo tail -100 /var/log/mysqld.log
```

## 总结一下

- **能联网** → Yum 仓库装，标准省心
- **不想污染宿主机** → Docker，干净利落
- **离线环境** → 手工 RPM，提前下好 bundle

生产环境的话还是推荐 MySQL 8.0 LTS + Yum 安装，安全配置那一步别跳过。
