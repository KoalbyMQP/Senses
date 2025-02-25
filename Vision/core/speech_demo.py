import os
import time
import signal
import subprocess
import zmq
import numpy as np
from core.demo_base import Demo
from depthai_sdk.previews import Previews

class SpeechEnabledDemo(Demo):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.speech_process = None
        self.robot_process = None
        self.current_target = None
        
        # Set up ZMQ for command communication
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect("tcp://localhost:5558")
        self.socket.setsockopt_string(zmq.SUBSCRIBE, "")
        
        # Set up ZMQ for coordinate publishing
        self.coord_context = zmq.Context()
        self.coord_socket = self.coord_context.socket(zmq.PUB)
        self.coord_socket.bind("tcp://*:5559")

    def filter_measurements_iqr(self, measurements):
        print(f"Starting IQR filtering with {len(measurements)} measurements")
        
        x_coords = [m['position']['x'] for m in measurements]
        y_coords = [m['position']['y'] for m in measurements]
        z_coords = [m['position']['z'] for m in measurements]
        widths = [m['dimensions']['width'] for m in measurements if 'dimensions' in m]
        heights = [m['dimensions']['height'] for m in measurements if 'dimensions' in m]
        
        print(f"Extracted coordinates ranges:")
        print(f"X: {min(x_coords) if x_coords else 0:.5f} to {max(x_coords) if x_coords else 0:.5f}")
        print(f"Y: {min(y_coords) if y_coords else 0:.5f} to {max(y_coords) if y_coords else 0:.5f}")
        print(f"Z: {min(z_coords) if z_coords else 0:.5f} to {max(z_coords) if z_coords else 0:.5f}")
        
        def apply_iqr_filter(data):
            if not data:
                return -float('inf'), float('inf')
            Q1 = np.percentile(data, 25)
            Q3 = np.percentile(data, 75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            return lower_bound, upper_bound
        
        x_bounds = apply_iqr_filter(x_coords)
        y_bounds = apply_iqr_filter(y_coords)
        z_bounds = apply_iqr_filter(z_coords)
        width_bounds = apply_iqr_filter(widths)
        height_bounds = apply_iqr_filter(heights)
        
        print(f"IQR Bounds:")
        print(f"X: {x_bounds[0]:.5f} to {x_bounds[1]:.5f}")
        print(f"Y: {y_bounds[0]:.5f} to {y_bounds[1]:.5f}")
        print(f"Z: {z_bounds[0]:.5f} to {z_bounds[1]:.5f}")
        
        filtered_measurements = []
        for m in measurements:
            x, y, z = m['position']['x'], m['position']['y'], m['position']['z']
            
            if 'dimensions' in m:
                w, h = m['dimensions']['width'], m['dimensions']['height']
                if (x_bounds[0] <= x <= x_bounds[1] and
                    y_bounds[0] <= y <= y_bounds[1] and
                    z_bounds[0] <= z <= z_bounds[1] and
                    width_bounds[0] <= w <= width_bounds[1] and
                    height_bounds[0] <= h <= height_bounds[1]):
                    filtered_measurements.append(m)
            else:
                if (x_bounds[0] <= x <= x_bounds[1] and
                    y_bounds[0] <= y <= y_bounds[1] and
                    z_bounds[0] <= z <= z_bounds[1]):
                    filtered_measurements.append(m)
        
        print(f"After IQR filtering: {len(filtered_measurements)} measurements remain")
        
        return filtered_measurements

    def setup(self, conf):
        super().setup(conf)
        
        # Start speech detection process
        print("Starting speech detection process...")
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            speech_script_path = os.path.join(project_root, "Speech", "detection", "pickAndPlaceVoiceDetection.py")
            
            venv_path = os.environ.get('VIRTUAL_ENV', '')
            if venv_path:
                activate_cmd = f"source {venv_path}/bin/activate && "
            else:
                activate_cmd = ""
            
            speech_cmd = f"lxterminal -e 'bash -c \"{activate_cmd}python3 {speech_script_path} 2>/dev/null; echo Press Enter to close...; read\"'"
            
            self.speech_process = subprocess.Popen(
                speech_cmd,
                shell=True,
                preexec_fn=os.setsid
            )
            
            time.sleep(1)
            if self.speech_process.poll() is None:
                print("Speech detection process started successfully in new terminal")
            else:
                print("Warning: Speech detection process failed to start")
        except Exception as e:
            print(f"Error starting speech detection: {e}")

        # Start robot control process
        print("Starting robot control process...")
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            robot_script_path = os.path.join(project_root, "backend", "Testing", "finlyPickAndPlace.py")
            
            venv_path = os.environ.get('VIRTUAL_ENV', '')
            if venv_path:
                activate_cmd = f"source {venv_path}/bin/activate && "
            else:
                activate_cmd = ""
            
            robot_cmd = f"lxterminal -e 'bash -c \"export PYTHONPATH=/home/finley/Documents/GitHub/Vision:$PYTHONPATH; {activate_cmd}python3 {robot_script_path}; echo Press Enter to close...; read\"'"

            self.robot_process = subprocess.Popen(
                robot_cmd,
                shell=True,
                preexec_fn=os.setsid
            )
            
            time.sleep(1)
            if self.robot_process.poll() is None:
                print("Robot control process started successfully in new terminal")
            else:
                print("Warning: Robot control process failed to start")
        except Exception as e:
            print(f"Error starting robot control: {e}")

    def run(self):
        print("Starting speech-enabled pipeline...")
        # Start listening for commands before running the main pipeline
        target_object = None
        
        while target_object is None:
            try:
                command = self.socket.recv_string(flags=zmq.NOBLOCK)
                print(f"Received command: {command}")
                
                if command.startswith("pick up"):
                    target_object = command.split("pick up ")[1]
                    self.current_target = target_object
                    print(f"New target received: {target_object}")
                    if hasattr(self, '_nnManager'):
                        print("Setting target object in NNetManager")
                        if self._nnManager.set_target_object(target_object):
                            print(f"Target object set to: {self._nnManager._target_object}")
                        else:
                            print("Failed to set target object")
                            continue
                        
                        # Create measurements file
                        self.measurements_file = open('test_tuple.txt', 'w')
                        print("Created measurements file: test_tuple.txt")
                        break
            except zmq.Again:
                time.sleep(0.01)
                pass
            except Exception as e:
                print(f"Error in ZMQ receive: {e}")
                time.sleep(0.01)
        
        # Now run the parent's run method to start the pipeline
        super().run()

    def loop(self):
        super().loop()
        
        # Handle speech commands while running
        try:
            command = self.socket.recv_string(flags=zmq.NOBLOCK)
            print(f"Received command during operation: {command}")
            
            if command.startswith("pick up"):
                target_object = command.split("pick up ")[1]
                self.current_target = target_object
                print(f"New target received: {target_object}")
                if hasattr(self, '_nnManager'):
                    print("Setting target object in NNetManager")
                    # When the NNetManager is expected to have a "set_target_object" method
                    if hasattr(self._nnManager, 'set_target_object'):
                        if self._nnManager.set_target_object(target_object):
                            print(f"Target object set to: {self._nnManager._target_object}")
                        else:
                            print("Failed to set target object")
                    else:
                        print("NNetManager does not have set_target_object method")
                    
                    if hasattr(self._nnManager, 'measurement_buffer'):
                        self._nnManager.measurement_buffer = []
                        self._nnManager.coordinates_sent = False
                    
        except zmq.Again:
            pass
        except Exception as e:
            print(f"Error in ZMQ receive during loop: {e}")
        
        # Process coordinates if enough measurements have been collected
        if (hasattr(self, '_nnManager') and 
            hasattr(self._nnManager, 'measurement_buffer') and 
            hasattr(self._nnManager, 'max_buffer_size') and
            hasattr(self._nnManager, 'coordinates_sent')):
            
            if (len(self._nnManager.measurement_buffer) >= self._nnManager.max_buffer_size and 
                not self._nnManager.coordinates_sent):
                
                filtered_measurements = self.filter_measurements_iqr(self._nnManager.measurement_buffer)
                if filtered_measurements:
                    mean_x = np.mean([m['position']['x'] for m in filtered_measurements])
                    mean_y = np.mean([m['position']['y'] for m in filtered_measurements])
                    mean_z = np.mean([m['position']['z'] for m in filtered_measurements])
                    print(f"Publishing final mean coordinates: {mean_x:.5f}, {mean_y:.5f}, {mean_z:.5f}")
                    coord_str = f"{mean_x:.5f},{mean_y:.5f},{mean_z:.5f}"
                    self.coord_socket.send_string(coord_str)
                    print("Coordinates sent to robot")
                    self._nnManager.coordinates_sent = True
                    self._nnManager.measurement_buffer = []

    def stop(self, *args, **kwargs):
        # Terminate speech process if running
        if self.speech_process:
            try:
                os.killpg(os.getpgid(self.speech_process.pid), signal.SIGTERM)
            except Exception as e:
                print(f"Error terminating speech process: {e}")

        # Terminate robot process if running
        if self.robot_process:
            try:
                os.killpg(os.getpgid(self.robot_process.pid), signal.SIGTERM)
            except Exception as e:
                print(f"Error terminating robot process: {e}")

        # Clean up ZMQ resources
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'context'):
            self.context.term()
        if hasattr(self, 'coord_socket'):
            self.coord_socket.close()
        if hasattr(self, 'coord_context'):
            self.coord_context.term()

        # Close measurement file if open
        if hasattr(self, 'measurements_file'):
            self.measurements_file.close()

        super().stop(*args, **kwargs) 