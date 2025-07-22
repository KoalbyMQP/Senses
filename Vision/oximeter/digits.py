import depthai as dai
import cv2
import numpy as np
from ultralytics import YOLO

predefined_labels = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]

def detect_digits(model, image, confidence_threshold=0.5, iou_threshold=0.35):
    """Detects digits in the image using the provided YOLO model.

    Args:
        model (YOLO): The YOLO model for digit detection.
        image (np.ndarray): The input image.
        confidence_threshold (float, optional): Confidence threshold for detection. Defaults to 0.5.
        iou_threshold (float, optional): Intersection over union threshold for detection. Defaults to 0.35.

    Returns:
        list: Detected digits with their bounding boxes and labels.
    """
    results = model.predict(image, conf=confidence_threshold, iou=iou_threshold)
    return results

def extract_boxes_labels(results):
    """Extracts bounding boxes and labels from the detection results.

    Args:
        results (list): Detection results from the YOLO model.

    Returns:
        tuple: A tuple containing:
            - boxes (np.ndarray): Bounding boxes in xywh format.
            - labels (np.ndarray): Labels of the detected digits.
    """
    boxes = results[0].boxes.xywh.cpu().numpy()
    labels = results[0].boxes.cls.cpu().numpy()
    return boxes, labels

def xyhw_to_xyxy(box):
    """
    Somehow x and y in xywh are the center of the box (normally top left?)
    """
    x, y, w, h = box
    # Calculate top-left corner (x1, y1)
    x1 = x - w / 2
    y1 = y - h / 2
    # Calculate bottom-right corner (x2, y2)
    x2 = x + w / 2
    y2 = y + h / 2
    return [x1, y1, x2, y2] 

def get_values(results):
    """
    Gets the values from the detection results.
    """
    boxes, labels = extract_boxes_labels(results)
    boxes = [xyhw_to_xyxy(box) for box in boxes]  # Convert boxes to xyxy format
    #sort boxes by x and y coordinates
    #TODO: sort boxes by x and y coordinates, based on display format of oximeter
    values = []
    #convert boxes and labels into key value pairs
    for box, label in zip(boxes, labels):
        digit = predefined_labels[int(label)]
        values.append((box, digit))
    zipped = zip(boxes, labels)
    for i in len(zipped):
        if ((i+1) < len(zipped)):
            # each value is made of two detected digits
            digit1 = predefined_labels[int(label[i])]
            digit2 = predefined_labels[int(label[i+1])]
            value = digit1 + digit2
            values.append(value)
    return values

