import depthai as dai
import cv2
import numpy as np
import zmq
import time
import numpy as np

def frameNorm(frame, bbox):
    normVals = np.full(len(bbox), frame.shape[0])
    normVals[::2] = frame.shape[1]
    return (np.clip(np.array(bbox), 0, 1) * normVals).astype(int)

class DepthAIHandler:
    def __init__(self):
        self.pipeline = dai.Pipeline()
        self.current_target = None
        
        # Initialize ZMQ subscriber with retry mechanism
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                self.context = zmq.Context()
                self.socket = self.context.socket(zmq.SUB)
                self.socket.connect("tcp://localhost:6325")
                self.socket.setsockopt_string(zmq.SUBSCRIBE, "")
                print("DepthAI handler ZMQ subscriber initialized")
                break
            except zmq.error.ZMQError as e:
                print(f"ZMQ connection attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(retry_delay)
                if hasattr(self, 'socket'):
                    self.socket.close()
                if hasattr(self, 'context'):
                    self.context.term()

    def cleanup(self):
        print("Cleaning up DepthAI handler...")
        if self.socket:
            self.socket.close()
        if self.context:
            self.context.term()

    def create_pipeline(self):
        # Create neural network node
        detection_nn = self.pipeline.createYoloDetectionNetwork()
        detection_nn.setBlobPath("models/yolo-v3-tiny-tf.blob")
        detection_nn.setConfidenceThreshold(0.5)
        
        # Create color camera
        cam_rgb = self.pipeline.createColorCamera()
        cam_rgb.setPreviewSize(416, 416)
        cam_rgb.setInterleaved(False)
        cam_rgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)
        
        # Link camera -> NN
        cam_rgb.preview.link(detection_nn.input)
        
        # Create outputs
        xout_rgb = self.pipeline.createXLinkOut()
        xout_rgb.setStreamName("rgb")
        cam_rgb.preview.link(xout_rgb.input)
        
        xout_nn = self.pipeline.createXLinkOut()
        xout_nn.setStreamName("nn")
        detection_nn.out.link(xout_nn.input)

    def process_frame(self, frame, detections, target_label):
        # Convert target label to match YOLO class names
        label_mapping = {
            "apple": "apple",
            "orange": "orange",
            "bottle": "bottle",
            "cup": "cup",
            "remote": "remote control"
        }
        
        yolo_label = label_mapping.get(target_label.lower(), target_label)
        
        # Find detection with highest confidence for target object
        target_detection = None
        highest_conf = 0
        
        for detection in detections:
            label = detection.label
            confidence = detection.confidence
            
            if str(label).lower() == yolo_label and confidence > highest_conf:
                highest_conf = confidence
                target_detection = detection
        
        # Only draw the target detection with highest confidence
        if target_detection:
            bbox = frameNorm(frame, [
                target_detection.xmin,
                target_detection.ymin,
                target_detection.xmax,
                target_detection.ymax
            ])
            
            # Draw filled background for text
            cv2.rectangle(frame, 
                         (bbox[0], (bbox[1] - 28)),
                         ((bbox[0] + 110), bbox[1]),
                         (0, 255, 0),
                         cv2.FILLED)
            
            # Draw bounding box
            cv2.rectangle(frame, 
                         (bbox[0], bbox[1]),
                         (bbox[2], bbox[3]),
                         (0, 255, 0),
                         2)
            
            # Add label and confidence score
            label_text = f"{yolo_label}: {int(highest_conf * 100)}%"
            cv2.putText(frame,
                       label_text,
                       (bbox[0] + 5, bbox[1] - 10),
                       cv2.FONT_HERSHEY_SIMPLEX,
                       0.5,
                       (0, 0, 0),
                       1,
                       cv2.LINE_AA)
            
            if hasattr(target_detection, 'spatialCoordinates'):
                # Add spatial coordinates if available
                texts = [
                    f"X: {target_detection.spatialCoordinates.x:.3f}m",
                    f"Y: {target_detection.spatialCoordinates.y:.3f}m",
                    f"Z: {target_detection.spatialCoordinates.z:.3f}m"
                ]
                
                for i, text in enumerate(texts):
                    y_pos = bbox[1] + 20 + (i * 20)
                    cv2.putText(frame, text,
                               (bbox[0], y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX,
                               0.5,
                               (0, 255, 0),
                               2)
        
        return frame

    def run(self):
        try:
            with dai.Device(self.pipeline) as device:
                q_rgb = device.getOutputQueue("rgb")
                q_nn = device.getOutputQueue("nn")
                
                while True:
                    try:
                        # Check for new commands from speech recognition
                        command = self.socket.recv_string(flags=zmq.NOBLOCK)
                        if command.startswith("pick up"):
                            self.current_target = command.split("pick up ")[1]
                            print(f"New target object: {self.current_target}")
                    except zmq.Again:
                        pass
                    
                    if in_rgb := q_rgb.tryGet():
                        frame = in_rgb.getCvFrame()
                        
                        if in_nn := q_nn.tryGet():
                            detections = in_nn.detections
                            
                            # Only process detections if we have a target object
                            if self.current_target:
                                frame = self.process_frame(frame, detections, self.current_target)
                            else:
                                # If no target object, show all detections
                                for detection in detections:
                                    x1 = int(detection.xmin * frame.shape[1])
                                    y1 = int(detection.ymin * frame.shape[0])
                                    x2 = int(detection.xmax * frame.shape[1])
                                    y2 = int(detection.ymax * frame.shape[0])
                                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), 1)
                        
                        cv2.imshow("Frame", frame)
                        
                    if cv2.waitKey(1) == ord('q'):
                        break
        finally:
            self.cleanup()
