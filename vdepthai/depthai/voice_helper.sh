#!/bin/bash
export PYTHONPATH="/home/finley/Documents/GitHub/Vision-Backup:$PYTHONPATH"


log_with_timestamp() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> device_logs.txt
}

safe_execute() {
    if command -v "${1%% *}" >/dev/null 2>&1; then
        eval "$1" >> device_logs.txt 2>&1
        return 0
    else
        log_with_timestamp "Command not available: ${1%% *}"
        return 1
    fi
}

{
    log_with_timestamp "=== Starting Device Diagnostics ==="

    log_with_timestamp "=== System Status ==="
    safe_execute "vcgencmd measure_temp"
    safe_execute "free -h"
    safe_execute "vcgencmd get_throttled"
    
    log_with_timestamp "=== USB Device Status ==="
    safe_execute "lsusb -v | grep -i luxonis"
    safe_execute "dmesg | grep -i 'usb\|luxonis'"
    
    log_with_timestamp "=== DepthAI Device Status ==="
    safe_execute "ls -l /dev/v4l/by-id/"
    
    if command -v journalctl >/dev/null 2>&1; then
        log_with_timestamp "=== DepthAI System Logs ==="
        safe_execute "journalctl | grep -i depthai | tail -n 50"
        log_with_timestamp "=== System Error Logs ==="
        safe_execute "journalctl -b 0 -p err | tail -n 50"
    fi
    
    log_with_timestamp "=== Resource Usage ==="
    safe_execute "top -b -n 1"
    safe_execute "iostat"
    
    log_with_timestamp "=== Diagnostics Complete ==="
    echo "" >> device_logs.txt
} 2>&1 | tee -a device_logs.txt

log_with_timestamp "=== Starting DepthAI Demo ==="
python3 depthai_demo.py -cnn yolo-v3-tiny-tf -s color "$@" 2>&1 | tee -a device_logs.txt

EXIT_CODE=$?
log_with_timestamp "=== DepthAI Demo Exited with Status: $EXIT_CODE ==="

#python3 depthai_demo.py -cnn yolov8n_coco_640x352 -s color "$@"
