import depthai as dai
import cv2
import numpy as np
import zmq

class DepthAIHandler:
    def __init__(self):
        self.pipeline = dai.Pipeline()
        self.current_target = None
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect("tcp://localhost:5556")
        self.socket.setsockopt_string(zmq.SUBSCRIBE, "")

    def create_pipeline(self):
        # Create neural network node
        detection_nn = self.pipeline.createYoloDetectionNetwork()
        detection_nn.setBlobPath("models/yolo-v3tiny-tf.blob")
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
        highest_conf = 0
        target_detection = None
        
        for detection in detections:
            label = detection.label
            confidence = detection.confidence
            
            if label == target_label and confidence > highest_conf:
                highest_conf = confidence
                target_detection = detection
        
        if target_detection:
            # Draw bounding box only for the target object with highest confidence
            bbox = frameNorm(frame, (target_detection.xmin, target_detection.ymin, 
                                   target_detection.xmax, target_detection.ymax))
            cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
            cv2.putText(frame, f"{target_label}: {confidence:.2f}", 
                       (bbox[0], bbox[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0))
        
        return frame

    def run(self):
        with dai.Device(self.pipeline) as device:
            q_rgb = device.getOutputQueue("rgb")
            q_nn = device.getOutputQueue("nn")
            
            while True:
                # Check for new commands from ZMQ
                try:
                    command = self.socket.recv_string(flags=zmq.NOBLOCK)
                    if command.startswith("pick up"):
                        self.current_target = command.split("pick up ")[1]
                except zmq.Again:
                    pass
                
                if in_rgb := q_rgb.tryGet():
                    frame = in_rgb.getCvFrame()
                    
                    if in_nn := q_nn.tryGet():
                        detections = in_nn.detections
                        
                        if self.current_target:
                            frame = self.process_frame(frame, detections, self.current_target)
                    
                    cv2.imshow("Frame", frame)
                    
                if cv2.waitKey(1) == ord('q'):
                    break
