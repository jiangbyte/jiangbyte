---
date: 2026-10-03
description: "本机 Docker 拉取并运行 MySQL、Redis、Silo、RabbitMQ、Ollama、etcd、Attu 等基础设施的命令备忘。"
categories: ["运维"]
tags: ["运维"]
---

## 拉取镜像

```bash
# ===== MySQL 9.7.2 =====
docker pull docker.xuanyuan.run/library/mysql:9.7.2; docker tag docker.xuanyuan.run/library/mysql:9.7.2 library/mysql:9.7.2; docker rmi docker.xuanyuan.run/library/mysql:9.7.2

# ===== Redis 8.8.2 =====
docker pull docker.xuanyuan.run/library/redis:8.8.2; docker tag docker.xuanyuan.run/library/redis:8.8.2 library/redis:8.8.2; docker rmi docker.xuanyuan.run/library/redis:8.8.2

# ===== Silo (MinIO 变体) =====
docker pull docker.xuanyuan.run/pgsty/silo:RELEASE.2026-08-06T00-00-00Z; docker tag docker.xuanyuan.run/pgsty/silo:RELEASE.2026-08-06T00-00-00Z pgsty/silo:RELEASE.2026-08-06T00-00-00Z; docker rmi docker.xuanyuan.run/pgsty/silo:RELEASE.2026-08-06T00-00-00Z

# ===== RabbitMQ 4.2.9-management =====
docker pull docker.xuanyuan.run/library/rabbitmq:4.2.9-management; docker tag docker.xuanyuan.run/library/rabbitmq:4.2.9-management library/rabbitmq:4.2.9-management; docker rmi docker.xuanyuan.run/library/rabbitmq:4.2.9-management

# ===== Ollama 0.33.1 =====
docker pull docker.xuanyuan.run/ollama/ollama:0.33.1; docker tag docker.xuanyuan.run/ollama/ollama:0.33.1 ollama/ollama:0.33.1; docker rmi docker.xuanyuan.run/ollama/ollama:0.33.1


docker pull pgexh7a70kca8kgghn-quay.xuanyuan.run/coreos/etcd:v3.6.12; docker tag pgexh7a70kca8kgghn-quay.xuanyuan.run/coreos/etcd:v3.6.12 quay.io/coreos/etcd:v3.6.12; docker rmi pgexh7a70kca8kgghn-quay.xuanyuan.run/coreos/etcd:v3.6.12


docker pull docker.xuanyuan.run/zilliz/attu:v3.0.0; docker tag docker.xuanyuan.run/zilliz/attu:v3.0.0 zilliz/attu:v3.0.0; docker rmi docker.xuanyuan.run/zilliz/attu:v3.0.0
```
## 运行命令

```bash
# ===== MySQL 9.7.2（开机自启）=====
docker run -d --name mysql \
  -p 3306:3306 \
  -e MYSQL_ROOT_PASSWORD='infra123!' \
  -v /home/charlie/Workspace/datas/mysql:/var/lib/mysql \
  --restart unless-stopped \
  mysql:9.7.2

# ===== Redis 8.8.2（开机自启 + AOF）=====
docker run -d --name redis \
  -p 6379:6379 \
  -e REDIS_PASSWORD='infra123!' \
  -v /home/charlie/Workspace/datas/redis:/data \
  --restart unless-stopped \
  redis:8.8.2 \
  --requirepass "infra123!" --appendonly yes


# ===== MySQL 9.7.2（开机不自启）=====
docker run -d --name mysql \
  -p 3306:3306 \
  -e MYSQL_ROOT_PASSWORD='infra123!' \
  -v /home/charlie/Workspace/datas/mysql:/var/lib/mysql \
  --restart no \
  mysql:9.7.2

# ===== Redis 8.8.2（开机不自启 + AOF）=====
docker run -d --name redis \
  -p 6379:6379 \
  -e REDIS_PASSWORD='infra123!' \
  -v /home/charlie/Workspace/datas/redis:/data \
  --restart no \
  redis:8.8.2 \
  --requirepass "infra123!" --appendonly yes


# ===== Silo (MinIO 变体) =====
docker run -d --name silo \
  -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=admin \
  -e MINIO_ROOT_PASSWORD='infra123!' \
  -v silo_data:/data \
  --restart unless-stopped \
  pgsty/silo:RELEASE.2026-08-06T00-00-00Z \
  server /data --console-address ":9001"
  
  
# ===== Silo（默认不自启）=====
docker run -d --name silo \
  -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=admin \
  -e MINIO_ROOT_PASSWORD='infra123!' \
  -v /home/charlie/Workspace/datas/silo:/data \
  --restart no \
  pgsty/silo:RELEASE.2026-08-06T00-00-00Z \
  server /data --console-address ":9001"

# ===== RabbitMQ 4.2.9-management =====
docker run -d --name rabbitmq \
  -p 5672:5672 \
  -p 15672:15672 \
  -e RABBITMQ_DEFAULT_USER=admin \
  -e RABBITMQ_DEFAULT_PASS='infra123!' \
  -v rabbitmq_data:/var/lib/rabbitmq \
  --restart no \
  rabbitmq:4.2.9-management

# ===== Ollama 0.33.1 =====
docker run -d --name ollama \
  -p 11434:11434 \
  -v ollama_data:/root/.ollama \
  --restart unless-stopped \
  ollama/ollama:0.33.1

# ===== Ollama 0.33.1 =====
docker run -d --name ollama \
  -p 11434:11434 \
  -v ollama_data:/root/.ollama \
  --restart no \
  ollama/ollama:0.33.1
  
# ===== Draw.io 31.4.1 =====
docker run -d --name draw \
  -p 18080:8080 \
  --restart unless-stopped \
  jgraph/drawio:31.4.1
  
docker run -d --name drawio \
  -p 18080:8080 \
  --restart no \
  jgraph/drawio:31.4.2
  
# ===== Nacos 2.5.0 =====
docker run -d --name nacos \
  -p 8848:8848 \
  -p 9848:9848 \
  --restart unless-stopped \
  -e MODE=standalone \
  nacos/nacos-server:v2.5.0
  
  
  
docker run -d --name nginx \
  -p 8080:80 \
  -v /home/charlie/Workspace/datas/ngnix/conf/nginx.conf:/etc/nginx/nginx.conf:ro \
  -v /home/charlie/Workspace/datas/ngnix/conf/conf.d:/etc/nginx/conf.d:ro \
  -v /home/charlie/Workspace/datas/ngnix/html:/usr/share/nginx/html:ro \
  -v /home/charlie/Workspace/datas/ngnix/logs:/var/log/nginx \
  -v /home/charlie/Workspace/datas/ngnix/ssl:/etc/nginx/ssl:ro \
  --restart no \
  nginx:stable-alpine3.24
```

## 运行命令

```bash
# ===== MySQL 9.7.2（开机不自启）=====
docker run -d --name mysql \
  -p 3306:3306 \
  -e MYSQL_ROOT_PASSWORD='infra123!' \
  -v mysql_data:/var/lib/mysql \
  --restart no \
  mysql:9.7.2

# ===== Redis 8.8.2（开机不自启 + AOF）=====
docker run -d --name redis \
  -p 6379:6379 \
  -e REDIS_PASSWORD='infra123!' \
  -v redis_data:/data \
  --restart no \
  redis:8.8.2 \
  --requirepass "infra123!" --appendonly yes

# ===== Silo（默认不自启）=====
docker run -d --name silo \
  -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=admin \
  -e MINIO_ROOT_PASSWORD='infra123!' \
  -v silo_data:/data \
  --restart no \
  pgsty/silo:RELEASE.2026-08-06T00-00-00Z \
  server /data --console-address ":9001"

# ===== RabbitMQ 4.2.9-management =====
docker run -d --name rabbitmq \
  -p 5672:5672 \
  -p 15672:15672 \
  -e RABBITMQ_DEFAULT_USER=admin \
  -e RABBITMQ_DEFAULT_PASS='infra123!' \
  -v rabbitmq_data:/var/lib/rabbitmq \
  --restart no \
  rabbitmq:4.2.9-management

# ===== Ollama 0.33.1 =====
docker run -d --name ollama \
  -p 11434:11434 \
  -v ollama_data:/root/.ollama \
  --restart no \
  ollama/ollama:0.33.1

docker run -d --name drawio \
  -p 18080:8080 \
  --restart no \
  jgraph/drawio:31.4.6
  
# ===== Nacos 2.5.0 =====
docker run -d --name nacos \
  -p 8848:8848 \
  -p 9848:9848 \
  --restart unless-stopped \
  -e MODE=standalone \
  nacos/nacos-server:v2.5.0
  
  
# ===== Milvus 前置：命名卷写入 etcd 配置 =====
docker volume create milvus_data
docker run --rm -v milvus_data:/var/lib/milvus alpine sh -c 'cat > /var/lib/milvus/embedEtcd.yaml << EOF
listen-client-urls: http://0.0.0.0:2379
advertise-client-urls: http://0.0.0.0:2379
quota-backend-bytes: 4294967296
auto-compaction-mode: revision
auto-compaction-retention: '\''1000'\''
EOF'
# ===== Milvus（开机不自启）=====
docker run -d --name milvus \
  --pull=never \
  --security-opt seccomp:unconfined \
  -e ETCD_USE_EMBED=true \
  -e ETCD_DATA_DIR=/var/lib/milvus/etcd \
  -e ETCD_CONFIG_PATH=/var/lib/milvus/embedEtcd.yaml \
  -e COMMON_STORAGETYPE=local \
  -e DEPLOY_MODE=STANDALONE \
  -v milvus_data:/var/lib/milvus \
  -p 19530:19530 \
  -p 9091:9091 \
  -p 2379:2379 \
  --health-cmd="curl -f http://localhost:9091/healthz" \
  --health-interval=30s \
  --health-start-period=90s \
  --health-timeout=20s \
  --health-retries=3 \
  --restart no \
  milvusdb/milvus:v3.0.1 \
  milvus run standalone
# ===== 开启鉴权，并把 root 密码改为 infra123! =====
docker exec milvus sh -c 'cat > /milvus/configs/user.yaml << EOF
common:
  security:
    authorizationEnabled: true
EOF'
docker restart milvus
# 等 healthy 后执行
curl -sS -X POST "http://127.0.0.1:19530/v2/vectordb/users/update_password" \
  -H "Authorization: Bearer root:Milvus" \
  -H "Content-Type: application/json" \
  -d '{"userName":"root","password":"Milvus","newPassword":"infra123!"}'
# ===== Attu（开机不自启）=====
docker run -d --name attu \
  --pull=never \
  -p 8000:3000 \
  -e MILVUS_URL=http://host.docker.internal:19530 \
  -e ATTU_ADMIN_USER=admin \
  -e ATTU_ADMIN_PASSWORD='infra123!' \
  -v attu_data:/data \
  --add-host=host.docker.internal:host-gateway \
  --restart no \
  zilliz/attu:v3.0.0
```
