#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR

# --- 1. 加载配置 ---
if [ ! -f "migrate-config.sh" ]; then
    echo "错误：找不到 migrate-config.sh 文件。请确保该文件与脚本在同一目录下。"
    exit 1
fi
source "migrate-config.sh"

# --- 2. 运行时变量设置 ---
LOG_TIMESTAMP=$(date +"%Y%m%d%H%M%S")
LOG_FILE="${MIGRATE_LOG_DIR}/redis-sync-${LOG_TIMESTAMP}.log"

# --- 3. 函数定义 ---

# 记录日志
log_message() {
    echo "$(date +"%Y-%m-%d %H:%M:%S") - $1" | tee -a "$LOG_FILE"
}

# 检查上一个命令是否成功
check_status() {
    if [ $? -ne 0 ]; then
        log_message "❌ 错误：上一步操作失败。请检查日志获取详情。脚本退出。"
        exit 1
    fi
}

# --- 4. 迁移步骤开始 ---

# 创建日志目录
mkdir -p "$MIGRATE_LOG_DIR"
check_status

log_message "======================================================"
log_message "🚀 Redis 数据迁移同步脚本启动：${LOG_FILE}"
log_message "源服务器 (A) 目录: ${SOURCE_COMPOSE_DIR}"
log_message "目标服务器 (B) SSH: ${DESTINATION_SSH_USER}@${DESTINATION_SSH_HOST}"
log_message "======================================================"

# --- 步骤 4.1: 停止源服务器 A 的 Redis 服务 ---
log_message "1. 正在停止源服务器 A 的 Redis 服务..."
cd "$SOURCE_COMPOSE_DIR"
docker compose stop redis >> "$LOG_FILE" 2>&1
check_status
log_message "   ✅ 源服务器 A Redis 服务已停止。"

# --- 步骤 4.2: 停止目标服务器 B 的 Redis 服务并清除旧数据 (使用 sudo) ---
log_message "2. 正在通过 SSH 停止目标服务器 B 的 Redis 服务并清理旧数据..."

# 在目标服务器 B 上执行停止和清理命令
SSH_COMMANDS="
    cd ${DESTINATION_COMPOSE_DIR} && docker compose stop redis
    if [ \$? -ne 0 ]; then echo 'ERROR: Failed to stop B Redis service'; exit 1; fi

    echo '正在清除目标服务器 B 的旧数据目录 (需要 sudo)...'
    sudo rm -rf ${DESTINATION_DATA_DIR}
    if [ \$? -ne 0 ]; then echo 'ERROR: Failed to remove B data directory'; exit 1; fi

    echo '正在创建新的目标数据目录 (需要 sudo)...'
    sudo mkdir -p ${DESTINATION_DATA_DIR}
    if [ \$? -ne 0 ]; then echo 'ERROR: Failed to create B data directory'; exit 1; fi
"
ssh "${DESTINATION_SSH_USER}@${DESTINATION_SSH_HOST}" "$SSH_COMMANDS" >> "$LOG_FILE" 2>&1
check_status
log_message "   ✅ 目标服务器 B Redis 服务已停止，旧数据已清除。"

# --- 步骤 4.3: 使用 rsync 传输数据到目标服务器 B 并修复权限 ---
log_message "3. 正在使用 rsync 同步数据到目标服务器 B..."

# rsync 使用 --rsync-path='sudo rsync' 确保远程执行 rsync 时使用 root 权限
rsync -avz \
    --rsync-path="sudo rsync" \
    "$SOURCE_DATA_DIR/" \
    "${DESTINATION_SSH_USER}@${DESTINATION_SSH_HOST}:${DESTINATION_DATA_DIR}" >> "$LOG_FILE" 2>&1

check_status
log_message "   ✅ 数据同步完成。正在通过 SSH 修正目标目录权限..."

# 修复目标目录权限为容器预期的 REDIS_CONTAINER_UID (使用 sudo)
SSH_COMMANDS_FIX_PERM="
    echo '正在修正目标数据目录权限为 ${REDIS_CONTAINER_UID}:${REDIS_CONTAINER_UID}...'
    sudo chown -R ${REDIS_CONTAINER_UID}:${REDIS_CONTAINER_UID} ${DESTINATION_DATA_DIR}
    if [ \$? -ne 0 ]; then echo 'ERROR: Failed to set permissions for B data directory'; exit 1; fi
"
ssh "${DESTINATION_SSH_USER}@${DESTINATION_SSH_HOST}" "$SSH_COMMANDS_FIX_PERM" >> "$LOG_FILE" 2>&1
check_status
log_message "   ✅ 目标目录权限修正完毕 (chown -R ${REDIS_CONTAINER_UID}:${REDIS_CONTAINER_UID})。"

# --- 步骤 4.4: 启动目标服务器 B 的 Redis 服务 ---
log_message "4. 正在通过 SSH 启动目标服务器 B 的 Redis 服务..."
ssh "${DESTINATION_SSH_USER}@${DESTINATION_SSH_HOST}" "cd ${DESTINATION_COMPOSE_DIR} && docker compose up -d redis" >> "$LOG_FILE" 2>&1
check_status
log_message "   ✅ 目标服务器 B Redis 服务已启动。"

# --- 步骤 4.5: 启动源服务器 A 的 Redis 服务 ---
log_message "5. 正在启动源服务器 A 的 Redis 服务..."
cd "$SOURCE_COMPOSE_DIR"
docker compose up -d redis >> "$LOG_FILE" 2>&1
check_status
log_message "   ✅ 源服务器 A Redis 服务已启动。"

log_message "======================================================"
log_message "🎉 数据迁移同步过程全部完成！"
log_message "======================================================"

exit 0
