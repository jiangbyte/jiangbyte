## 先说背景

Ubuntu 的 APT 源里自带 MySQL，装起来比 CentOS 省心不少。不过默认版本可能不是最新的，想指定版本或者用官方最新版也有办法。

## 方法一：APT 直接装（最省事）

```bash
sudo apt update
sudo apt install mysql-server
```

装完启动：

```bash
sudo systemctl start mysql
sudo systemctl enable mysql
```

然后跑一下安全配置脚本：

```bash
sudo mysql_secure_installation
```

这个脚本会一步步引导你改 root 密码、删匿名用户、禁止 root 远程登录、删测试数据库。别跳过。

## 方法二：装特定版本

APT 里其实各个版本都有独立的包名：

```bash
sudo apt install mysql-server-8.0   # 装 8.0
sudo apt install mysql-server-5.7   # 装 5.7（如果源里还有的话）
```

## 方法三：用官方 APT 仓库（想用最新版）

如果 APT 里的版本太老，可以用 Oracle 官方的仓库：

```bash
wget https://dev.mysql.com/get/mysql-apt-config_0.8.24-1_all.deb
sudo dpkg -i mysql-apt-config_0.8.24-1_all.deb
sudo apt update
sudo apt install mysql-server
```

安装过程中会让你选版本，选好之后装的就是官方最新版了。

## 基本操作

### 检查状态

```bash
sudo systemctl status mysql
```

### 连 MySQL

```bash
sudo mysql -u root -p
```

### 创建用户和数据库

```sql
CREATE USER 'username'@'localhost' IDENTIFIED BY 'password';
CREATE DATABASE dbname;
GRANT ALL PRIVILEGES ON dbname.* TO 'username'@'localhost';
FLUSH PRIVILEGES;
```

### 配置文件位置

| 文件 | 路径 |
|------|------|
| 主配置 | `/etc/mysql/mysql.conf.d/mysqld.cnf` |
| 数据目录 | `/var/lib/mysql` |
| 日志 | `/var/log/mysql` |

## 常见问题

### 忘了 root 密码

```bash
sudo systemctl stop mysql
sudo mysqld_safe --skip-grant-tables &
```

然后进 MySQL 重设密码：

```sql
USE mysql;
UPDATE user SET authentication_string=PASSWORD('new_password') WHERE User='root';
FLUSH PRIVILEGES;
EXIT;
```

重启服务：

```bash
sudo systemctl restart mysql
```

### 开启远程连接

默认 MySQL 只绑 `127.0.0.1`，外网连不了。改配置：

```bash
sudo vi /etc/mysql/mysql.conf.d/mysqld.cnf
```

找到 `bind-address` 那行改成：

```
bind-address = 0.0.0.0
```

然后授权 root 远程登录（不推荐，见下方安全建议）：

```sql
CREATE USER 'root'@'%' IDENTIFIED BY 'MySql2025@';
GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' WITH GRANT OPTION;
FLUSH PRIVILEGES;
```

重启 MySQL，防火墙放行 3306：

```bash
sudo systemctl restart mysql
sudo ufw allow 3306
```

### 从远程测试连接

```bash
mysql -h 你的服务器IP -u root -p
```

## 安全建议

**别直接用 root 远程登录**，正经做法是：

- 建个专用管理用户

```sql
CREATE USER 'admin'@'%' IDENTIFIED BY '强密码';
GRANT ALL PRIVILEGES ON *.* TO 'admin'@'%' WITH GRANT OPTION;
```

- 限制来源 IP

```sql
CREATE USER 'admin'@'192.168.1.%' IDENTIFIED BY '密码';
```

- 或者走 SSH 隧道

```bash
ssh -L 3306:localhost:3306 用户名@服务器IP
```

## 总结

- **图省事** → `apt install mysql-server`，一行搞定
- **要指定版本** → `mysql-server-8.0` 这样装
- **要最新版** → 加官方仓库再装

Ubuntu 比 CentOS 省心很多，自带的 APT 源就有 MySQL，不用折腾第三方仓库。生产环境记得跑 `mysql_secure_installation`，远程连接别用 root。
