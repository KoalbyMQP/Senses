#!/bin/bash

# Get the absolute path to Vision-Backup
VISION_BACKUP_PATH="/home/finley/Documents/GitHub/Vision-Backup"

# Change to Vision-Backup directory
cd "$VISION_BACKUP_PATH"

# Activate the virtual environment
source "$VISION_BACKUP_PATH/vdepthai/bin/activate"

# Install required packages if not present
pip install -r "$VISION_BACKUP_PATH/vdepthai/depthai/requirements.txt" 2>/dev/null

# Set PYTHONPATHSet PYTHONPATH

export PYTHONPATH="$VISION_BACKUP_PATH:$PYTHONPATH"

# Set OpenVINO environment if available

if [ -f "/opt/intel/openvino/bin/setupvars.sh" ]; then

    source /opt/intel/openvino/bin/setupvars.sh

fi

# Run depthai_demo.py with error handling

python3 vdepthai/depthai/depthai_demo.py -cnn yolo-v3-tiny-tf -s color "$@" || {

    echo "Error running depthai_demo.py"

    echo "Installing missing requirements..."

    python3 vdepthai/depthai/install_requirements.py

    echo "Retrying depthai_demo.py..."

    python3 vdepthai/depthai/depthai_demo.py -cnn yolo-v3-tiny-tf -s color "$@"
}