#!/bin/bash
export PYTHONPATH="/home/finley/Documents/GitHub/Vision-Backup:$PYTHONPATH"
python3 depthai_demo.py -cnn yolo-v3-tiny-tf -s color "$@" 

#python3 depthai_demo.py -cnn yolov8n_coco_640x352 -s color "$@"
