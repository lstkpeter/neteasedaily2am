#!/bin/sh
set -e

if [ "$1" = "sync" ] || [ "$1" = "test-netease" ] || [ "$1" = "test-am" ]; then
    exec python3 main.py "$@"
fi

echo "=== 启动 NetEaseDaily2AM 定时守护进程 ==="
echo "设定执行时间: 每天早上 06:30 (Asia/Shanghai)"

# 写入当前环境变量供 cron 使用
printenv | grep -E '^(NCM_|AM_|SYNC_|PLAYLIST_|PATH=)' > /etc/environment

# 配置 cron 任务 (每天 06:30 自动执行，输出实时打入容器终端并保存到 /app/logs)
CRON_SCHEDULE="${CRON_EXPR:-30 6 * * *}"
echo "$CRON_SCHEDULE cd /app && python3 main.py sync > /proc/1/fd/1 2>&1" > /etc/cron.d/sync-cron
chmod 0644 /etc/cron.d/sync-cron
crontab /etc/cron.d/sync-cron

touch /var/log/sync.log

# 启动时先执行一次测试同步
if [ "$RUN_ON_STARTUP" = "true" ]; then
    echo "检测到 RUN_ON_STARTUP=true，正在执行首次同步..."
    python3 main.py sync || true
fi

echo "Cron 守护进程已就绪，等待定时触发..."
cron -f
