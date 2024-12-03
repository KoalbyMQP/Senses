#!/bin/bash
export PYTHONPATH="/home/finley/Documents/GitHub/Vision-Backup:$PYTHONPATH"

# Activate virtual environment if not already activated
if [[ -z "${VIRTUAL_ENV}" ]]; then
    source ./venv/bin/activate
fi

# Run the demo with YOLO model and color camera
python3 depthai_demo.py -cnn yolo-v3-tiny-tf -s color "$@"