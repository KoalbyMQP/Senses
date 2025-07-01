#!/bin/bash
export PYTHONPATH="/home/finley/Documents/GitHub/Senses/Vision:$PYTHONPATH"
SCRIPT_DIR="/home/finley/Documents/GitHub/Senses/Vision"
# Run the demo with YOLO model and color camera
echo "Voice helper started"
sleep 1
echo "Processing complete"
python3 -u "$SCRIPT_DIR/depthai_demo.py" -cnn yolo-v3-tiny-tf -s color "$@" 
#python3 depthai_demo.py -cnn yolov8n_coco_640x352 -s color "$@"