#!/bin/sh
set -e

if [ "$1" = "sync" ] || [ "$1" = "test-netease" ] || [ "$1" = "test-am" ]; then
    exec python3 main.py "$@"
fi

echo "=== 启动 NetEaseDaily2AM 定时守护进程 ==="
echo "设定执行时间: 每天早上 06:30 (Asia/Shanghai)"

# 导出完整的环境变量供 cron 进程及其子进程使用（包含 PATH 和所有 Token）
export -p > /app/env.sh
chmod 0600 /app/env.sh

# 准备定时任务执行包装脚本
cat << 'EOF' > /app/run_sync.sh
#!/bin/sh
. /app/env.sh
cd /app
exec /usr/local/bin/python3 main.py sync
EOF
chmod +x /app/run_sync.sh

# 配置 cron 任务 (每天 06:30 自动执行，输出实时打入容器终端并保存到 /app/logs)
CRON_SCHEDULE="${CRON_EXPR:-30 6 * * *}"
cat << EOF > /etc/cron.d/sync-cron
SHELL=/bin/sh
PATH=/usr/local/bin:/usr/local/sbin:/usr/bin:/bin:/sbin
$CRON_SCHEDULE /app/run_sync.sh > /proc/1/fd/1 2>&1
EOF
chmod 0644 /etc/cron.d/sync-cron
crontab /etc/cron.d/sync-cron

mkdir -p /app/logs
touch /app/logs/sync.log

# 启动时先执行一次测试同步
if [ "$RUN_ON_STARTUP" = "true" ]; then
    echo "检测到 RUN_ON_STARTUP=true，正在执行首次同步..."
    /app/run_sync.sh || true
fi

cron
echo "Cron 守护进程已就绪，等待定时触发..."
exec tail -f /app/logs/sync.log
