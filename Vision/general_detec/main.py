import depthai as dai
import cv2
import numpy as np
from ultralytics import YOLO


def names_to_classes(model, names):
    '''
    Converts a list of class names to their corresponding indices in the YOLO model.
    Args:
        model (YOLO): The YOLO model.
        names (list): List of class names.
    Returns:
        list: List of class indices corresponding to the names.
    '''
    names_to_indices = {
        cls_name: idx for idx, cls_name in model.names.items()
    }
    indices = []
    for name in names:
        if name in names_to_indices:
            indices.append(names_to_indices[name])
        else:
            raise ValueError(f"Class name '{name}' not found in model names.")
    return indices

def detect_obj(model_name, image, confidence_threshold=0.5, iou_threshold=0.35, desired_objs=None):
    """
    The function detects objects in the image using the provided YOLO model.

    Args:
        model_name (str): Name of YOLO model to use for detection.
        image: Image to be processed, in image format. If using DepthAI, this should be a frame from the camera.
        confidence_threshold (float): Confidence threshold for the model.
        iou_threshold (float): Intersection over union threshold for the model.
        desired_objs (list, optional): List of class names from model to detect. If None, all classes will be detected.

    Returns:
        results: The prediction results from the model.
    """

    model = YOLO("Vision/models/" + model_name + ".pt")
    classes = names_to_classes(model, desired_objs) if desired_objs else None

    if classes is None:
        results = model.predict(image, conf=confidence_threshold, iou=iou_threshold)
    else:
        results = model.predict(image, conf=confidence_threshold, iou=iou_threshold, classes=classes)

    return results

def extract_boxes(results):
    """
    Extracts bounding boxes from the model's prediction results.

    Args:
        results: The prediction results from the YOLO model.

    Returns:
        list: List of bounding boxes in xywh format.
    """
    boxes = results[0].boxes.xywh.cpu().numpy()
    return boxes.tolist() if boxes.size else []



#======================================================TESTING========================================================
# Test usage, loads an image from a file path for testing purposes
image = cv2.imread("Vision/chess/test_images/complex.jpg")
model_name = "pieces"
results = detect_obj(model_name, image, confidence_threshold=0.5, iou_threshold=0.35, desired_objs=["white-king", "white-rook", "black-knight"])
boxes = extract_boxes(results)
print("Detected boxes:", boxes)

#Display the image with bounding boxes
cv2.imshow("Detected Objects", image)
for box in boxes:
    x, y, w, h = box
    cv2.rectangle(image, (int(x - w / 2), int(y - h / 2)), (int(x + w / 2), int(y + h / 2)), (0, 255, 0), 2)
cv2.imshow("Detected Objects with Boxes", image)
cv2.waitKey(0)
cv2.destroyAllWindows()