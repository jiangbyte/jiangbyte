---
date: 2026-10-01
description: "首先创建所有服务的数据持久化目录："
categories: ["运维"]
tags: ["运维"]
---

## 前置准备

首先创建所有服务的数据持久化目录：

```bash
# 创建统一的数据存储目录
mkdir -p ~/docker-data/{postgres,redis,rabbitmq}
```

## 服务部署

### PostgreSQL（支持向量扩展，端口5433）

```bash
# 拉取支持向量扩展的PostgreSQL镜像
docker pull pgvector/pgvector:pg17

# 启动PostgreSQL容器
docker run -d \
  --name postgres \
  --restart unless-stopped \
  -m 512m \
  -e POSTGRES_PASSWORD=123456 \
  -e POSTGRES_DB=myapp \
  -v ~/docker-data/postgres:/var/lib/postgresql/data \
  -p 5433:5432 \
  pgvector/pgvector:pg17
```

**启用向量扩展（首次启动后执行）：**
```bash
docker exec -it postgres psql -U postgres -d myapp -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

**连接测试：**
```bash
docker exec -it postgres psql -U postgres -d myapp -c "SELECT 1+1;"
# 返回 ?column? | 2 表示成功
```

### Redis（缓存服务，端口6380）

```bash
# 拉取Redis镜像
docker pull redis:7-alpine

# 启动Redis容器
docker run -d \
  --name redis \
  --restart unless-stopped \
  -m 128m \
  -v ~/docker-data/redis:/data \
  -p 6380:6379 \
  redis:7-alpine \
  redis-server --maxmemory 128mb --maxmemory-policy allkeys-lru --requirepass 123456 --appendonly yes
```

**连接测试：**
```bash
docker exec -it redis redis-cli -a 123456 ping
# 返回 PONG 表示成功
```

### RabbitMQ（消息队列，端口5673/15673）

```bash
# 拉取带管理界面的RabbitMQ镜像
docker pull rabbitmq:4-management-alpine

# 启动RabbitMQ容器
docker run -d \
  --name rabbitmq \
  --restart unless-stopped \
  -m 384m \
  -v ~/docker-data/rabbitmq:/var/lib/rabbitmq \
  -p 5673:5672 \
  -p 15673:15672 \
  -e RABBITMQ_DEFAULT_USER=admin \
  -e RABBITMQ_DEFAULT_PASS=123456 \
  rabbitmq:4-management-alpine
```

**管理界面访问：** `http://你的IP:15673`，账号 `admin` / 密码 `123456`

### MySQL（备用数据库，端口3307）

如需要MySQL作为备用数据库，可使用以下配置：

```bash
# 拉取MySQL镜像
docker pull mysql:8.0

# 启动MySQL容器
docker run -d \
  --name mysql \
  --restart unless-stopped \
  -m 512m \
  -e MYSQL_ROOT_PASSWORD=123456 \
  -e MYSQL_DATABASE=myapp \
  -v ~/docker-data/mysql:/var/lib/mysql \
  -p 3307:3306 \
  mysql:8.0 \
  --innodb_buffer_pool_size=256M
```

## 服务连接信息汇总

| 服务                | 内部端口  | 外部端口      | 账号        | 密码         |
| ----------------- | ----- | --------- | --------- | ---------- |
| **PostgreSQL**    | 5432  | **5433**  | postgres  | **123456** |
| **Redis**         | 6379  | **6380**  | (无)       | **123456** |
| **RabbitMQ**      | 5672  | **5673**  | **admin** | **123456** |
| **RabbitMQ 管理界面** | 15672 | **15673** | **admin** | **123456** |
| **MySQL (备用)**    | 3306  | **3307**  | root      | **123456** |
