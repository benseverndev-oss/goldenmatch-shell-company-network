#!/bin/sh
echo "=== /proc summary ==="
for pid in $(ls /proc | grep -E '^[0-9]+$'); do
    c=$(cat /proc/$pid/comm 2>/dev/null)
    case "$c" in
        *python*|*goldenmatch*|*uvicorn*) echo "$pid $c";;
    esac
done
echo "=== meminfo ==="
grep -E 'MemTotal|MemAvailable|MemFree' /proc/meminfo
echo "=== cgroup memory ==="
cat /sys/fs/cgroup/memory.current 2>/dev/null
cat /sys/fs/cgroup/memory.max 2>/dev/null
echo "=== loadavg ==="
cat /proc/loadavg
echo "=== chunk progress ==="
ls -la /data/reports/generated 2>/dev/null
