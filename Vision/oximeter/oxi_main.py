import depthai as dai
import cv2
import numpy as np
from ultralytics import YOLO

from digits import (
    detect_digits,
    extract_boxes_labels,
    xyhw_to_xyxy,
    get_values,
)

def image_to_oxi_pipeline():
    """Get camera input, detect digitis, return values, and display input with bounding boxes.

    Args:
        image (np.ndarray): Input image containing the oximeter display.
        model (YOLO): YOLO model for digit detection.
        confidence (dict, optional): Dictionary containing confidence thresholds for detection. Defaults to None.

    Returns:
        list: List of detected digit values from the oximeter display.
    """

    #load model
    digits_model = YOLO("digits_model.pt")

    #Initialize camera
    pipeline = dai.Pipeline()
    cam = pipeline.createColorCamera()
    cam.setBoardSocket(dai.CameraBoardSocket.RGB)
    cam.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
    cam.setInterleaved(False)
    cam.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)

    xout = pipeline.createXLinkOut()
    xout.setStreamName("oxi_vision")
    cam.video.link(xout.input)

    # Set default confidence thresholds if not provided
    conf_threshold = confidence.get('conf', 0.5) if confidence else 0.5
    iou_threshold = confidence.get('iou', 0.35) if confidence else 0.35

    # Detect digits in the image
    results = detect_digits(digits_model, image, confidence_threshold=conf_threshold, iou=iou_threshold)
    
    # Extract bounding boxes and labels
    boxes, labels = extract_boxes_labels(results)
    
    # Get values from the detected digits
    values = get_values(results)

    return values