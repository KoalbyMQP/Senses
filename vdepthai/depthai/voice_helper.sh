#!/bin/bash

# Get the absolute path to Vision-Backup
VISION_BACKUP_PATH="/home/finley/Documents/GitHub/Vision-Backup"

# Change to Vision-Backup directory
cd "$VISION_BACKUP_PATH"

# Activate the virtual environment
source "$VISION_BACKUP_PATH/vdepthai/bin/activate"

# Set PYTHONPATH
export PYTHONPATH="$VISION_BACKUP_PATH:$PYTHONPATH"

# Run depthai_demo.py
python3 vdepthai/depthai/depthai_demo.py -cnn yolo-v3-tiny-tf -s color "$@"