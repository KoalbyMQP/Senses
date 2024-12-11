#!/bin/bash
export PYTHONPATH="/home/finley/Documents/GitHub/Vision-Backup:$PYTHONPATH"

# Function to log with timestamp
log_with_timestamp() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> device_logs.txt
}

# Function to safely execute command if it exists
safe_execute() {
    if command -v "${1%% *}" >/dev/null 2>&1; then
        eval "$1" >> device_logs.txt 2>&1
        return 0
    else
        log_with_timestamp "Command not available: ${1%% *}"
        return 1
    fi
}

# Create or clear log file
echo "" > device_logs.txt

# Log system information before starting
{
    log_with_timestamp "=== Starting Device Diagnostics ==="
    
    # Check USB devices and speeds
    log_with_timestamp "=== USB Configuration ==="
    if safe_execute "lsusb -t"; then
        log_with_timestamp "USB Device Tree obtained"
    else
        log_with_timestamp "Unable to get USB device tree"
    fi
    
    # Check for USB 3.0 support
    if safe_execute "lsusb -v | grep -i 'bcdusb\|luxonis'"; then
        log_with_timestamp "USB speed information obtained"
    else
        log_with_timestamp "Unable to get USB speed information"
    fi
    
    # System Status
    log_with_timestamp "=== System Status ==="
    if safe_execute "vcgencmd measure_temp"; then
        safe_execute "vcgencmd get_throttled"
    fi
    safe_execute "free -h"
    
    # Process Check
    log_with_timestamp "=== Process Status ==="
    safe_execute "ps aux | grep -E 'depthai|python' | grep -v grep"
    
    # Check available memory
    log_with_timestamp "=== Memory Status ==="
    safe_execute "cat /proc/meminfo | grep -E 'MemTotal|MemFree|MemAvailable'"
    
    # Resource Usage
    log_with_timestamp "=== Resource Usage ==="
    safe_execute "top -b -n 1 | head -n 20"
    
    log_with_timestamp "=== Diagnostics Complete ==="
    echo "" >> device_logs.txt

} 2>&1 | tee -a device_logs.txt

# Function to check if process is running
check_process() {
    local process_name=$1
    if pgrep -f "$process_name" > /dev/null; then
        log_with_timestamp "Process $process_name is running"
        return 0
    else
        log_with_timestamp "Warning: Process $process_name is not running"
        return 1
    fi
}

# Run the demo with YOLO model and color camera
log_with_timestamp "=== Starting DepthAI Demo ==="

# Check USB speed before starting
if lsusb -v 2>/dev/null | grep -q "bcdUSB\s*3\."; then
    log_with_timestamp "USB 3.0 connection detected"
else
    log_with_timestamp "WARNING: USB 3.0 not detected. Device may run in low-bandwidth mode"
fi

# Start the demo and capture its PID
python3 depthai_demo.py -cnn yolo-v3-tiny-tf -s color "$@" 2>&1 | tee -a device_logs.txt &
DEMO_PID=$!

# Monitor the demo process
while kill -0 $DEMO_PID 2>/dev/null; do
    # Check processes every 5 seconds
    sleep 5
    check_process "pickAndPlaceVoiceDetection.py"
    check_process "finlyPickAndPlace.py"
    
    # Check for OAK-D device
    if ! lsusb 2>/dev/null | grep -q "Luxonis"; then
        log_with_timestamp "ERROR: OAK-D device disconnected!"
    fi
    
    # Log memory usage
    free -h | grep "Mem:" >> device_logs.txt
done

# Get exit status
wait $DEMO_PID
EXIT_CODE=$?

# Log final status
log_with_timestamp "=== DepthAI Demo Exited with Status: $EXIT_CODE ==="
if [ $EXIT_CODE -ne 0 ]; then
    log_with_timestamp "ERROR: Demo crashed with exit code $EXIT_CODE"
    # Dump last 50 lines of system log
    log_with_timestamp "=== Last System Messages ==="
    dmesg | tail -n 50 >> device_logs.txt 2>&1
fi


