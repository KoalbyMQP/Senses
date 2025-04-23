import os
import time
import signal
import subprocess
import zmq
import numpy as np
from core.demo_base import Demo
from depthai_sdk.previews import Previews
import sys
import math


class SpeechEnabledDemo(Demo):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.speech_process = None
        self.robot_process = None
        self.temperature_process = None
        self.face_process = None
        self.current_target = None
        self.measurement_buffer = []
        self.max_buffer_size = 400
        self.coordinates_sent = False 
        
        # Camera parameters for 1080p
        self.nn_source_width = 1920
        self.nn_source_height = 1080
        self.fx = 1504.128173828125
        self.fy = 1504.2720947265625
        
        # State tracking for demo transitions
        self._temp_demo_running = False
        self._main_pipeline_started = False
        self._pending_temperature_demo = False
        self.error = None
        
        # Set up ZMQ for command communication
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect("tcp://localhost:5558")
        self.socket.setsockopt_string(zmq.SUBSCRIBE, "")
        
        # Set up ZMQ for coordinate publishing
        self.coord_context = zmq.Context()
        self.coord_socket = self.coord_context.socket(zmq.PUB)
        self.coord_socket.bind("tcp://*:5559")

        # Set up ZMQ for face commands
        self.face_publisher = None
        try:
            self.face_publisher = self.context.socket(zmq.PUB)
            self.face_publisher.connect("tcp://localhost:5563")
            print("Connected to face interface socket at localhost:5563 for speech_demo")
        except Exception as e:
             print(f"speech_demo: Error connecting to face interface: {e}. Face commands will not be sent.")
             if self.face_publisher:
                 self.face_publisher.close()
             self.face_publisher = None

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
        print(f"W: {min(widths) if widths else 0:.5f} to {max(widths) if widths else 0:.5f}")
        print(f"H: {min(heights) if heights else 0:.5f} to {max(heights) if heights else 0:.5f}")
        
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
        print(f"W: {width_bounds[0]:.5f} to {width_bounds[1]:.5f}")
        print(f"H: {height_bounds[0]:.5f} to {height_bounds[1]:.5f}")
        
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
        self.send_face_command("neutral")
        
        self._start_face_interface()
        
        print("Starting speech detection process...")
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            speech_script_path = os.path.join(project_root, "Speech", "detection", "pickAndPlaceVoiceDetection.py")
            
            venv_path = os.environ.get('VIRTUAL_ENV', '')
            if not venv_path:
                venv_path = "/home/finley/Documents/GitHub/Senses/venv"
            
            # Create a temporary shell script for speech detection
            temp_speech_script = "/tmp/pickAndPlaceVoiceListener.sh"
            with open(temp_speech_script, "w") as f:
                f.write(f"""#!/bin/bash
source "{venv_path}/bin/activate"
export PYTHONPATH="{project_root}:$PYTHONPATH"
cd {os.path.dirname(speech_script_path)}
python3 {os.path.basename(speech_script_path)} || echo "Error occurred! Press Enter to close..." && read
""")
            os.chmod(temp_speech_script, 0o755)
            
            print(f"Created speech detection script: {temp_speech_script}")
            
            # Launch the script in a new terminal
            self.speech_process = subprocess.Popen(
                f"lxterminal --geometry=80x24 -e 'bash -c \"{temp_speech_script}; exec bash\"'",
                shell=True,
                preexec_fn=os.setsid
            )
            
            time.sleep(1)
            print("Speech detection process started successfully in new terminal")
        except Exception as e:
            print(f"Error starting speech detection: {e}")

        # Start robot control process
        print("Starting robot control process...")
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            robot_script_path = os.path.join(project_root, "Gripper", "pickandplace", "finlyPickAndPlace.py")
            
            venv_path = os.environ.get('VIRTUAL_ENV', '')
            if not venv_path:
                venv_path = "/home/finley/Documents/GitHub/Senses/venv"  # Default path if not in virtual env
            
            # Create a temporary shell script for robot control
            temp_robot_script = "/tmp/robotController.sh"
            with open(temp_robot_script, "w") as f:
                f.write(f"""#!/bin/bash
source "{venv_path}/bin/activate"
export PYTHONPATH="{project_root}:$PYTHONPATH"
cd {os.path.dirname(robot_script_path)}
python3 {os.path.basename(robot_script_path)} || echo "Error occurred! Press Enter to close..." && read
""")
            os.chmod(temp_robot_script, 0o755)
            
            print(f"Created robot control script: {temp_robot_script}")
            
            # Launch the script in a new terminal
            self.robot_process = subprocess.Popen(
                f"lxterminal --geometry=0x0 -e 'bash -c \"{temp_robot_script}; exec bash\"'",
                shell=True,
                preexec_fn=os.setsid
            )
            
            # Wait a moment for the terminal to appear, then bring face window to top
            time.sleep(1)
            os.system('wmctrl -r "Finley" -b add,above')
            
            time.sleep(1)
            print("Robot control process started successfully in new terminal")
        except Exception as e:
            print(f"Error starting robot control: {e}")

    def _start_face_interface(self):
        """Start face interface in new terminal"""
        print("\nStarting Face interface...")
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            face_script_dir = os.path.join(project_root, "Face")
            face_script = os.path.join(face_script_dir, "face.py")

            if not os.path.exists(face_script):
                 print(f"Error: Face script not found at {face_script}")
                 self.face_process = None
                 return

            venv_path = os.environ.get('VIRTUAL_ENV', '')
            if not venv_path:
                venv_path = "/home/finley/Documents/GitHub/Senses/venv"
                print(f"Warning: No active virtual environment detected. Using default: {venv_path}")

            temp_script = "/tmp/faceInterfaceLaunch.sh" 
            with open(temp_script, "w") as f:
                f.write(f"""#!/bin/bash
source \"{venv_path}/bin/activate\"
export PYTHONPATH=\"{project_root}:$PYTHONPATH\"
cd \"{face_script_dir}\"
python3 {os.path.basename(face_script)} || read -p \"Face script exited. Press Enter to close...\"
""")
            os.chmod(temp_script, 0o755)
            print(f"Created face launch script: {temp_script}")

            self.face_process = subprocess.Popen(
                f"lxterminal --geometry=80x24 --title='Finley Face (Pick/Place)' -e 'bash -c \"{temp_script}; exec bash\"'",
                shell=True,
                preexec_fn=os.setsid
            )

            time.sleep(1)
            print("Face interface process started successfully in new terminal.")
        
        except Exception as e:
            print(f"Failed to start face interface: {e}")
            self.face_process = None

    def send_face_command(self, emotion_command):
        """Send an emotion command string to the face interface."""
        if self.face_publisher:
            try:
                self.face_publisher.send_string(emotion_command, zmq.NOBLOCK)
            except zmq.error.Again:
                 print(f"Warning: speech_demo Face command '{emotion_command}' send would block.")
            except Exception as e:
                print(f"speech_demo: Error sending face command '{emotion_command}': {e}")

    def run(self):
        print("Starting speech-enabled pipeline...")
        # Start listening for commands before running the main pipeline
        target_object = None
        run_temperature_demo = False
        
        # Set initial state
        self._temp_demo_running = False
        self._main_pipeline_started = False
        
        print("Waiting for initial command (pick up <object> or get temperature)...")
        self.send_face_command("listening") # Face: Listening for first command
        
        while target_object is None and not run_temperature_demo:
            try:
                command = self.socket.recv_string(flags=zmq.NOBLOCK)
                print(f"Received command: {command}")
                
                if command.startswith("pick up"):
                    target_object = command.split("pick up ")[1]
                    self.current_target = target_object
                    print(f"New target received: {target_object}")
                    
                    self.measurement_buffer = []
                    self.coordinates_sent = False
                    print("Measurement buffer and coordinate sent flag reset.")

                    # Face: Focused, ready for pick & place
                    self.send_face_command("focused")
                    self.measurements_file = open('test_tuple.txt', 'w')
                    print("Created measurements file: test_tuple.txt")
                    break
                elif command == "get temperature":
                    print("Temperature command received")
                    run_temperature_demo = True
                    # Face: Focused, ready for temperature check
                    self.send_face_command("focused")
                    break
            except zmq.Again:
                time.sleep(0.01)
                pass
            except Exception as e:
                print(f"Error in ZMQ receive: {e}")
                time.sleep(0.01)
        
        # If temperature command received, run the temperature demo instead of the standard pipeline
        if run_temperature_demo:
            self._run_temperature_demo()
            
            # After temperature demo completes, check for new commands
            print("Temperature demo completed. Listening for new commands...")
            self.send_face_command("neutral") # Face: Neutral after temp demo
            self._listen_for_next_command()
        else:
            # Mark that the main pipeline is starting
            self._main_pipeline_started = True
            
            # Run the parent's run method to start the pipeline for pick and place
            try:
                super().run()
            except Exception as e:
                print(f"Error in main pipeline: {e}")
            finally:
                self._main_pipeline_started = False
    
    def _listen_for_next_command(self):
        """Listen for new commands after a demo completes"""
        print("Listening for new commands...")
        self.send_face_command("listening") # Face: Listening again
        timeout = 300  # 5 minutes
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                command = self.socket.recv_string(flags=zmq.NOBLOCK)
                if command:
                    print(f"Received new command: {command}")
                    self.send_face_command("focused") # Face: Focused on new command
                    
                    if command.startswith("pick up"):
                        # Start the main pipeline with the new target
                        target_object = command.split("pick up ")[1]
                        self.current_target = target_object
                        print(f"New target for pick and place: {target_object}")
                        
                        self.measurement_buffer = []
                        self.coordinates_sent = False
                        print("Measurement buffer and coordinate sent flag reset.")

                        # Face: Focused, ready for pick & place
                        self.send_face_command("focused")

                        if not hasattr(self, 'measurements_file') or self.measurements_file.closed:
                            self.measurements_file = open('test_tuple.txt', 'w')
                            print("Created measurements file: test_tuple.txt")
                                
                        self._main_pipeline_started = True
                        super().run()
                        return
                    
                    elif command == "get temperature":
                        # Run temperature demo again
                        self._run_temperature_demo()
                        # Reset timeout
                        start_time = time.time()
                        self.send_face_command("listening") # Face: Back to listening after temp demo
            
            except zmq.Again:
                time.sleep(0.1)
            except Exception as e:
                print(f"Error while listening for new commands: {e}")
                time.sleep(0.1)
                
        print("Timeout reached. Exiting command listener.")
        self.send_face_command("neutral") # Face: Neutral on timeout

    def _run_temperature_demo(self):
        """Runs the temperature demo by launching demo.py in the Thermometer folder"""
        print("========== STARTING TEMPERATURE MEASUREMENT SEQUENCE ==========")
        print("Step 1: Starting temperature monitoring demo...")
        self.send_face_command("scanning") # Face: Scanning for temperature
        
        # First, check if we need to close any existing device connections
        if hasattr(self, '_device') and not self._device.isClosed():
            print("Closing main pipeline device before starting temperature demo...")
            try:
                # Stop the main pipeline to release the device
                print("Temporarily stopping the main pipeline...")
                
                # Save current state to restore later if needed
                self._temp_demo_running = True
                
                # Close the device to release it for the temperature demo
                self._device.close()
                print("Device closed successfully")
                
                # Small delay to ensure device is released
                time.sleep(1)
            except Exception as e:
                print(f"Error closing device: {e}")
                return
        
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            temp_demo_path = os.path.join(project_root, "Vision", "Thermometer", "demo.py")
            
            if not os.path.exists(temp_demo_path):
                print(f"Error: Temperature demo script not found at {temp_demo_path}")
                return
            
            venv_path = os.environ.get('VIRTUAL_ENV', '')
            if not venv_path:
                venv_path = "/home/finley/Documents/GitHub/Senses/venv"  # Default path if not in virtual env
            
            # Create a temporary shell script for temperature demo
            temp_script = "/tmp/temperature_demo.sh"
            with open(temp_script, "w") as f:
                f.write(f"""#!/bin/bash
source "{venv_path}/bin/activate"
export PYTHONPATH="{project_root}:$PYTHONPATH"
cd {os.path.dirname(temp_demo_path)}
python3 {os.path.basename(temp_demo_path)} -a -xyz -n 0 || echo "Error occurred! Press Enter to close..." && read
""")
            os.chmod(temp_script, 0o755)
            
            print(f"Created temperature demo script: {temp_script}")
            
            # Launch the script in a new terminal
            self.temperature_process = subprocess.Popen(
                f"lxterminal --geometry=80x24 -e 'bash -c \"{temp_script}; exec bash\"'",
                shell=True,
                preexec_fn=os.setsid
            )
            
            print("Step 2: Temperature demo started in new terminal")
            
            # Create a socket for receiving coordinates from the temperature demo
            coord_receiver = self.context.socket(zmq.SUB)
            coord_receiver.connect("tcp://localhost:5560")
            coord_receiver.setsockopt_string(zmq.SUBSCRIBE, "")
            coord_receiver.setsockopt(zmq.RCVTIMEO, 120000)  
            
            print("Step 3: Waiting for forehead coordinates from temperature demo...")
            self.send_face_command("thinking") # Face: Thinking while waiting for coords
            try:
                # Wait for coordinates from the demo
                coordinates_str = coord_receiver.recv_string()
                print(f"Step 4: Received coordinates from thermometer demo: {coordinates_str}")
                self.send_face_command("neutral") # Face: Neutral after getting coords
                
                # After receiving coordinates, try ALL methods to move the robot
                print("Step 5: Received coordinates, now trying multiple methods to move the robot...")
                
                # METHOD 1: Try creating and running a script in a new terminal
                print("METHOD 1: Launching temperature check script in new terminal...")
                temp_robot_path = os.path.join(project_root, "Gripper", "thermometer", "finlyTemperatureCheck.py")
                
                try:
                    # Create a temporary script to run the robot movement
                    robot_temp_script = "/tmp/temperature_robot.sh"
                    with open(robot_temp_script, "w") as f:
                        f.write(f"""#!/bin/bash
echo "Starting temperature check robot movement..."
source "{venv_path}/bin/activate"
export PYTHONPATH="{project_root}:$PYTHONPATH"
cd {project_root}
python3 {temp_robot_path} --test --coords={coordinates_str} || echo "Error occurred! Press Enter to close..." && read
""")
                    os.chmod(robot_temp_script, 0o755)
                    
                    # Launch the robot movement in a new terminal
                    self.robot_process = subprocess.Popen(
                        f"lxterminal --geometry=80x24 -e 'bash -c \"{robot_temp_script}; exec bash\"'",
                        shell=True,
                        preexec_fn=os.setsid
                    )
                    print("Temperature check script launched in new terminal")
                except Exception as e:
                    print(f"METHOD 1 FAILED: {e}")
                    
                # METHOD 2: Try running the script directly in a background thread
                print("METHOD 2: Executing temperature check script directly in background thread...")
                try:
                    import threading
                    
                    def run_direct_script():
                        try:
                            cmd = [sys.executable, temp_robot_path, "--test", f"--coords={coordinates_str}"]
                            print(f"Executing: {' '.join(cmd)}")
                            subprocess.run(cmd, check=True)
                            print("METHOD 2 SUCCEEDED: Direct execution completed")
                        except Exception as e:
                            print(f"METHOD 2 FAILED: {e}")
                            
                    thread = threading.Thread(target=run_direct_script)
                    thread.daemon = True
                    thread.start()
                    print("Background execution thread started")
                except Exception as e:
                    print(f"METHOD 2 FAILED to start thread: {e}")
                    
            except zmq.error.Again:
                print("Timeout waiting for coordinates from temperature demo")
                self.send_face_command("curious") # Face: Curious on timeout
                time.sleep(1.5)
            except Exception as e:
                print(f"Error in temperature demo process: {e}")
                self.send_face_command("curious") # Face: Curious on error
                time.sleep(1.5)
                import traceback
                traceback.print_exc()
            finally:
                coord_receiver.close()
        except Exception as e:
            print(f"Error starting temperature demo: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # In case we need to restart the pipeline
            if hasattr(self, '_temp_demo_running'):
                self._temp_demo_running = False
            print("========== TEMPERATURE MEASUREMENT SEQUENCE COMPLETE ==========")
            self.send_face_command("neutral") # Ensure neutral at the very end

    def loop(self):
        # Call super().loop() first to handle core processing (frame prep, NN parsing etc.)
        super().loop()
        
        # Handle speech commands while running
        try:
            command = self.socket.recv_string(flags=zmq.NOBLOCK)
            print(f"Received command during operation: {command}")
            
            # Log command for debugging
            print(f"DEBUG: Command received: '{command}' - Type: {type(command)}")
            
            if command.lower() == "get temperature":
                print("TEMPERATURE COMMAND DETECTED! Starting temperature measurement process...")
                
                # Make sure we're not already in a temperature demo
                if hasattr(self, '_temp_demo_running') and self._temp_demo_running:
                    print("Temperature demo is already running")
                    self.send_face_command("focused") # Keep face focused if already running
                    return
                
                # Launch temperature demo in a separate process
                self._run_temperature_demo()
                
                # SPECIAL FAILSAFE: If for some reason the above doesn't trigger the robot,
                # directly try to move robot with default coordinates after a delay
                def delayed_emergency_check():
                    import threading
                    import time
                    
                    # Wait 20 seconds to see if normal methods work
                    time.sleep(20)
                    
                    print("SPECIAL FAILSAFE CHECK: Checking if temperature demo worked...")
                
                # Start the delayed check in a background thread
                import threading
                failsafe_thread = threading.Thread(target=delayed_emergency_check)
                failsafe_thread.daemon = True
                failsafe_thread.start()
                
            elif "pick up" in command.lower():
                # Format: "pick up {object}"
                target = command.lower().split("pick up ")[-1].strip()
                print(f"PICK UP COMMAND DETECTED! Target object: {target}")
                self.send_face_command("focused") # Face: Focus on new pick target

                # Set the current target for tracking purposes
                self.current_target = target
                
                self.measurement_buffer = []
                self.coordinates_sent = False
                print("Measurement buffer and coordinate sent flag reset.")

            else:
                print(f"Unknown command format: {command}")
                
        except zmq.error.Again:
            # No message available, normal operation
            pass
        except Exception as e:
            print(f"Error processing command: {e}")
            self.send_face_command("curious") # Face: curious on command processing error
            time.sleep(1.5)
            self.send_face_command("neutral")
        
        # Check if we need to run the temperature demo after stopping the main pipeline
        if hasattr(self, '_pending_temperature_demo') and self._pending_temperature_demo and self._device.isClosed():
            self._pending_temperature_demo = False
            self._run_temperature_demo()
            self.send_face_command("neutral") # Face: Neutral after pending demo

            # After temperature demo completes, restart listening for commands
            self._listen_for_next_command()
        
        if hasattr(self, '_nnManager'):
            newData, inNn = self._nnManager.parse()
            if newData is not None and not self.coordinates_sent:
                detections_received = len(newData)
                added_count = 0
                for detection in newData:
                    if hasattr(detection, 'spatialCoordinates') and self.current_target:
                        label_text = self._nnManager.getLabelText(detection.label)
                        if label_text.lower() == self.current_target.lower():
                            coords = detection.spatialCoordinates
                            measurement = {
                                'label': detection.label,
                                'label_text': label_text,
                                'confidence': detection.confidence,
                                'position': {
                                    'x': coords.x / 1000.0,
                                    'y': coords.y / 1000.0,
                                    'z': coords.z / 1000.0
                                }
                            }
                            if hasattr(detection, 'xmin') and hasattr(detection, 'xmax') and \
                               hasattr(detection, 'ymin') and hasattr(detection, 'ymax') and \
                               coords.z > 0: 

                                z_meters = coords.z / 1000.0

                                pixel_xmin = int(detection.xmin * self.nn_source_width)
                                pixel_ymin = int(detection.ymin * self.nn_source_height)
                                pixel_xmax = int(detection.xmax * self.nn_source_width)
                                pixel_ymax = int(detection.ymax * self.nn_source_height)

                                pixel_width = pixel_xmax - pixel_xmin
                                pixel_height = pixel_ymax - pixel_ymin

                                physical_width = (pixel_width * z_meters) / self.fx
                                physical_height = (pixel_height * z_meters) / self.fy

                                measurement['dimensions'] = {
                                    'width': physical_width,
                                    'height': physical_height
                                }

                            print(f"Adding measurement for target '{label_text}' to buffer. Buffer size: {len(self.measurement_buffer) + 1}")
                            self.measurement_buffer.append(measurement)
                            added_count += 1

                if detections_received > 0: 
                    print(f"Processed {detections_received} detections, added {added_count} matching target '{self.current_target}'. Current buffer size: {len(self.measurement_buffer)}")


        if len(self.measurement_buffer) >= self.max_buffer_size and not self.coordinates_sent:
            print(f"Buffer full ({len(self.measurement_buffer)} >= {self.max_buffer_size}) with measurements for target: '{self.current_target}'. Processing...")

            if self.measurement_buffer: 
                filtered_measurements = self.filter_measurements_iqr(self.measurement_buffer)

                if filtered_measurements:
                    mean_x = np.mean([m['position']['x'] for m in filtered_measurements])
                    mean_y = np.mean([m['position']['y'] for m in filtered_measurements])
                    mean_z = np.mean([m['position']['z'] for m in filtered_measurements])
                    
                    mean_w = np.mean([m['dimensions']['width'] for m in filtered_measurements if 'dimensions' in m]) if any('dimensions' in m for m in filtered_measurements) else 0.0
                    mean_h = np.mean([m['dimensions']['height'] for m in filtered_measurements if 'dimensions' in m]) if any('dimensions' in m for m in filtered_measurements) else 0.0

                    print(f"Publishing final mean values: X={mean_x:.5f}, Y={mean_y:.5f}, Z={mean_z:.5f}, W={mean_w:.5f}, H={mean_h:.5f}")
                    coord_str = f"{mean_x:.5f},{mean_y:.5f},{mean_z:.5f},{mean_w:.5f},{mean_h:.5f}"

                    try:
                        print("Waiting 1s for subscriber connection...")
                        time.sleep(1)
                        send_count = 3000
                        print(f"Sending coordinates {send_count} times...")
                        for i in range(send_count):
                            self.coord_socket.send_string(coord_str)
                            time.sleep(0.05)
                        print(f"Finished sending coordinates {send_count} times.")

                        self.send_face_command("happy")
                        time.sleep(1.5)
                        self.send_face_command("neutral") 
                        self.coordinates_sent = True 
                        self.measurement_buffer = [] 
                        print("Buffer cleared.")
                    except Exception as e:
                        print(f"Error sending coordinates via ZMQ: {e}")
                else:
                    print("No measurements remained after IQR filtering. Not sending coordinates.")
                    self.send_face_command("curious") 
                    time.sleep(1.5)
                    self.send_face_command("neutral")
            else:
                print("Buffer is full but contains no measurements (unexpected). Not sending coordinates.")
                self.send_face_command("curious")
                time.sleep(1.5)
                self.send_face_command("neutral")

    def stop(self, *args, **kwargs):
        self.send_face_command("neutral") # Ensure neutral face on stop
        # Terminate speech process if running
        if hasattr(self, 'speech_process') and self.speech_process is not None:
            try:
                os.killpg(os.getpgid(self.speech_process.pid), signal.SIGTERM)
                print("Speech process terminated")
            except Exception as e:
                print(f"Error terminating speech process: {e}")
                
        # Terminate robot process if running
        if hasattr(self, 'robot_process') and self.robot_process is not None:
            try:
                os.killpg(os.getpgid(self.robot_process.pid), signal.SIGTERM)
                print("Robot process terminated")
            except Exception as e:
                print(f"Error terminating robot process: {e}")
                
        # Terminate temperature process if running
        if hasattr(self, 'temperature_process') and self.temperature_process is not None:
            try:
                os.killpg(os.getpgid(self.temperature_process.pid), signal.SIGTERM)
                print("Temperature process terminated")
            except Exception as e:
                print(f"Error terminating temperature process: {e}")

        # Terminate face process if running
        if hasattr(self, 'face_process') and self.face_process is not None:
            try:
                os.killpg(os.getpgid(self.face_process.pid), signal.SIGTERM)
                print("Face interface process terminated")
            except Exception as e:
                print(f"Error terminating face interface process: {e}")

        super().stop(*args, **kwargs)

        # Clean up face publisher socket
        if hasattr(self, 'face_publisher') and self.face_publisher:
            try:
                self.face_publisher.close()
                print("speech_demo: Face publisher socket closed.")
            except Exception as e:
                print(f"speech_demo: Error closing face publisher socket: {e}")
        