#!/bin/bash

# Get the absolute path to Vision-Backup
VISION_BACKUP_PATH="/home/finley/Documents/GitHub/Vision-Backup"

# Create virtual environment if it doesn't exist
if [ ! -d "$VISION_BACKUP_PATH/vdepthai" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VISION_BACKUP_PATH/vdepthai"
fi

# Change to Vision-Backup directory
cd "$VISION_BACKUP_PATH"

# Activate the virtual environment
source "$VISION_BACKUP_PATH/vdepthai/bin/activate"

# Ensure pip is up to date in the virtual environment
"$VISION_BACKUP_PATH/vdepthai/bin/python3" -m pip install --upgrade pip

# Install required packages if not present (using venv's pip)
"$VISION_BACKUP_PATH/vdepthai/bin/pip3" install -r "$VISION_BACKUP_PATH/vdepthai/depthai/requirements.txt"

# Set PYTHONPATH
export PYTHONPATH="$VISION_BACKUP_PATH:$PYTHONPATH"

# Set OpenVINO environment if available
if [ -f "/opt/intel/openvino/bin/setupvars.sh" ]; then
    source /opt/intel/openvino/bin/setupvars.sh
fi

# Run depthai_demo.py with error handling using venv's Python
"$VISION_BACKUP_PATH/vdepthai/bin/python3" vdepthai/depthai/depthai_demo.py -cnn yolo-v3-tiny-tf -s color "$@" || {
    echo "Error running depthai_demo.py"
    echo "Installing missing requirements..."
    "$VISION_BACKUP_PATH/vdepthai/bin/python3" vdepthai/depthai/install_requirements.py
    echo "Retrying depthai_demo.py..."
    "$VISION_BACKUP_PATH/vdepthai/bin/python3" vdepthai/depthai/depthai_demo.py -cnn yolo-v3-tiny-tf -s color "$@"
}