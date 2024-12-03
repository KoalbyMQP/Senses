import depthai as dai
import cv2
import numpy as np
import zmq
import time
import numpy as np
from pickAndPlaceVoiceDetection import State

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

    def process_frame(self, frame, detections, current_state):
    # Map states to YOLO class names
        state_mapping = {
            State.APPLE: "apple",
            State.ORANGE: "orange", 
            State.BOTTLE: "bottle",
            State.CUP: "cup",
            State.REMOTE: "remote"
        }
        
        # Get target label based on current state
        target_label = state_mapping.get(current_state)
        
        if not target_label:
            return frame  # Return unmodified frame if no valid state
        
        # Only process detections for the target object
        target_detections = []
        for detection in detections:
            label = self.getLabelText(detection.label).lower()
            if label == target_label:
                target_detections.append(detection)
        
        # Draw bounding boxes only for target object detections
        if target_detections:
            self._nnManager.draw(frame, target_detections)
        
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
                            target_object = command.split("pick up ")[1]
                            self.current_target = target_object
                            # Update the neural network manager's target
                            self._nnManager.set_target_object(target_object)
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
