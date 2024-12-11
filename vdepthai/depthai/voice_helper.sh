#!/bin/bash
export PYTHONPATH="/home/finley/Documents/GitHub/Vision-Backup:$PYTHONPATH"

log_with_timestamp() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> device_logs.txt
}

{
    log_with_timestamp "=== Starting Device Diagnostics ==="
    
    log_with_timestamp "=== System Status ==="
    log_with_timestamp "Raspberry Pi Temperature:"
    vcgencmd measure_temp >> device_logs.txt
    
    log_with_timestamp "Memory Usage:"
    free -h >> device_logs.txt
    
    log_with_timestamp "Power Status:"
    vcgencmd get_throttled >> device_logs.txt
    
    log_with_timestamp "=== USB Device Status ==="
    lsusb -v | grep -i luxonis >> device_logs.txt
    
    log_with_timestamp "=== USB Kernel Messages ==="
    dmesg | grep -i "usb\|luxonis" >> device_logs.txt
    
    log_with_timestamp "=== DepthAI Device Status ==="
    ls -l /dev/v4l/by-id/ >> device_logs.txt 2>&1
    
    log_with_timestamp "=== DepthAI System Logs ==="
    journalctl | grep -i depthai | tail -n 50 >> device_logs.txt
    
    log_with_timestamp "=== System Error Logs ==="
    journalctl -b 0 -p err | tail -n 50 >> device_logs.txt
    
    log_with_timestamp "=== Resource Usage ==="
    top -b -n 1 >> device_logs.txt
    iostat >> device_logs.txt 2>&1
    
    log_with_timestamp "=== Diagnostics Complete ==="
    echo "" >> device_logs.txt
} 2>&1 | tee -a device_logs.txt

log_with_timestamp "=== Starting DepthAI Demo ==="
python3 depthai_demo.py -cnn yolo-v3-tiny-tf -s color "$@" 2>&1 | tee depthai_logs.txt

EXIT_CODE=$?
log_with_timestamp "=== DepthAI Demo Exited with Status: $EXIT_CODE ==="

#python3 depthai_demo.py -cnn yolov8n_coco_640x352 -s color "$@"
