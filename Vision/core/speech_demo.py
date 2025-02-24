import os
import time
import signal
import subprocess
import zmq
import numpy as np
from core.demo_base import Demo
from utils.error_utils import component_check

@component_check("speech_demo")
class SpeechEnabledDemo(Demo):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.speech_process = None
        self.robot_process = None
        self.current_target = None
        # Set up ZMQ subscriber (for speech commands) and publisher (for coordinates)
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect("tcp://localhost:5558")
        self.socket.setsockopt_string(zmq.SUBSCRIBE, "")
        self.coord_context = zmq.Context()
        self.coord_socket = self.coord_context.socket(zmq.PUB)
        self.coord_socket.bind("tcp://*:5559")

    def filter_measurements_iqr(self, measurements):
        print(f"Starting IQR filtering with {len(measurements)} measurements")
        x_coords = [m['position']['x'] for m in measurements]
        y_coords = [m['position']['y'] for m in measurements]
        z_coords = [m['position']['z'] for m in measurements]
        def bounds(data):
            Q1 = np.percentile(data, 25)
            Q3 = np.percentile(data, 75)
            return Q1 - 1.5 * (Q3 - Q1), Q3 + 1.5 * (Q3 - Q1)
        x_bounds = bounds(x_coords)
        y_bounds = bounds(y_coords)
        z_bounds = bounds(z_coords)
        filtered = [m for m in measurements if (x_bounds[0] <= m['position']['x'] <= x_bounds[1] and
                                                 y_bounds[0] <= m['position']['y'] <= y_bounds[1] and
                                                 z_bounds[0] <= m['position']['z'] <= z_bounds[1])]
        print(f"After IQR filtering: {len(filtered)} measurements remain")
        return filtered

    def calculate_mean_coordinates(self, measurements):
        mean_x = np.mean([m['position']['x'] for m in measurements])
        mean_y = np.mean([m['position']['y'] for m in measurements])
        mean_z = np.mean([m['position']['z'] for m in measurements])
        return mean_x, mean_y, mean_z

    def setup(self, conf):
        super().setup(conf)
        print("Setting up ZMQ subscriber in SpeechEnabledDemo...")
        try:
            self.socket.connect("tcp://localhost:5558")
            self.socket.setsockopt_string(zmq.SUBSCRIBE, "")
        except Exception as e:
            print(f"Error setting up ZMQ subscriber: {e}")
        # Start speech detection process
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            speech_script = os.path.join(project_root, "Speech", "pickAndPlaceVoiceDetection.py")
            activate_cmd = f"python3 {speech_script} "
            self.speech_process = subprocess.Popen(activate_cmd, shell=True, preexec_fn=os.setsid)
            time.sleep(1)
            if self.speech_process.poll() is None:
                print("Speech detection process started successfully")
            else:
                print("Speech detection process failed to start")
        except Exception as e:
            print(f"Error starting speech detection: {e}")
        # Start robot control process
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            robot_script = os.path.join(project_root, "backend", "Testing", "finlyPickAndPlace.py")
            activate_cmd = f"python3 {robot_script}"
            self.robot_process = subprocess.Popen(activate_cmd, shell=True, preexec_fn=os.setsid)
            time.sleep(1)
            if self.robot_process.poll() is None:
                print("Robot control process started successfully")
            else:
                print("Robot control process failed to start")
        except Exception as e:
            print(f"Error starting robot control: {e}")

    def run(self):
        print("Starting speech-enabled pipeline...")
        super().run()
        try:
            while self.shouldRun() and self.canRun():
                if (self._nnManager and 
                    len(self._nnManager.measurement_buffer) >= self._nnManager.max_buffer_size and 
                    not self._nnManager.coordinates_sent):
                    filtered = self.filter_measurements_iqr(self._nnManager.measurement_buffer)
                    if filtered:
                        mean_x, mean_y, mean_z = self.calculate_mean_coordinates(filtered)
                        coord_str = f"{mean_x:.5f},{mean_y:.5f},{mean_z:.5f}"
                        self.coord_socket.send_string(coord_str)
                        print("Coordinates sent to robot")
                        self._nnManager.coordinates_sent = True
                        self._nnManager.measurement_buffer = []
                self.loop()
        except StopIteration:
            pass
        except Exception as ex:
            raise ex
        finally:
            self.stop()

    def stop(self, *args, **kwargs):
        if self.speech_process:
            try:
                os.killpg(os.getpgid(self.speech_process.pid), signal.SIGTERM)
            except Exception as e:
                print(f"Error terminating speech process: {e}")
        if self.robot_process:
            try:
                os.killpg(os.getpgid(self.robot_process.pid), signal.SIGTERM)
            except Exception as e:
                print(f"Error terminating robot process: {e}")
        if self.socket:
            self.socket.close()
        if self.context:
            self.context.term()
        if self.coord_socket:
            self.coord_socket.close()
        if self.coord_context:
            self.coord_context.term()
        super().stop(*args, **kwargs) 