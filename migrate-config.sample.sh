#!/bin/bash
# ----------------------------------------------------------------------
# Redis 迁移同步配置样本 - migrate-config.sample.sh
#
# 使用说明：将此文件重命名为 'migrate-config.sh'，并替换所有配置值。
# ----------------------------------------------------------------------

# --- A. 目标服务器 (DESTINATION / 服务器 B) 配置 ---
# 目标服务器 B 的 SSH 连接信息
# --------------------------------------------------------
DESTINATION_SSH_USER="your_ssh_username"   # <--- **必须替换**：B 服务器上具有 sudo 权限的用户名
DESTINATION_SSH_HOST="target_server_ip_or_domain" # <--- **必须替换**：B 服务器的 IP 地址或域名

# 目标服务器 B 的 docker-compose.yml 文件所在的绝对路径
# 【请替换为 B 机器上实际的 Compose 文件路径】
DESTINATION_COMPOSE_DIR="/path/to/target/docker-project"

# 目标服务器 B 的 Redis 数据目录（必须与 docker-compose.yml 中 volumes 映射的宿主机路径一致）
DESTINATION_DATA_DIR="${DESTINATION_COMPOSE_DIR}/redis-data"


# --- B. 源服务器 (SOURCE / 服务器 A) 配置 ---
# --------------------------------------------------------
# 源服务器 A 的 docker-compose.yml 文件所在的绝对路径
# 【请替换为 A 机器上实际的 Compose 文件路径】
SOURCE_COMPOSE_DIR="/path/to/source/docker-project"

# 源服务器 A 的 Redis 数据目录（必须与 docker-compose.yml 中 volumes 映射的宿主机路径一致）
SOURCE_DATA_DIR="${SOURCE_COMPOSE_DIR}/redis-data"


# --- C. 权限与日志配置 ---
# --------------------------------------------------------
# 日志文件将保存在执行脚本的当前目录下的这个文件夹中
MIGRATE_LOG_DIR="./migrate"

# Redis 容器内用户/组 ID。这是关键，用于修复目标服务器上的数据目录权限。
# 默认的官方 Redis 镜像是使用 ID 999 运行。
REDIS_CONTAINER_UID="999"

# ----------------------------------------------------------------------
# END OF CONFIGURATION
# ----------------------------------------------------------------------
