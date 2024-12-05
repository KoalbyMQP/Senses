#!/bin/bash

# Set up environment
export PYTHONPATH="/home/finley/Documents/GitHub/Vision-Backup:$PYTHONPATH"

# Check for OAK device
echo "Checking for OAK device..."
python3 -c "import depthai; print(depthai.Device.getAllAvailableDevices())"

# Run the demo with YOLOv8 model with specific flags
python3 depthai_demo.py \
    -cnn yolov7tiny_coco_416x416 \
    -s color \
    "$@"