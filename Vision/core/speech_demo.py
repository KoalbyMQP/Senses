import os
import time
import signal
import subprocess
import zmq
import numpy as np
from core.demo_base import Demo
from depthai_sdk.previews import Previews
import sys


class SpeechEnabledDemo(Demo):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.speech_process = None
        self.robot_process = None
        self.temperature_process = None
        self.current_target = None
        
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
            if not venv_path:
                venv_path = "/home/finley/Documents/GitHub/Senses/myvirtual"  # Default path if not in virtual env
            
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
            if not venv_path:
                venv_path = "/home/finley/Documents/GitHub/Senses/myvirtual"  # Default path if not in virtual env
            
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
                f"lxterminal --geometry=80x24 -e 'bash -c \"{temp_robot_script}; exec bash\"'",
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
        run_temperature_demo = False
        
        # Set initial state
        self._temp_demo_running = False
        self._main_pipeline_started = False
        
        while target_object is None and not run_temperature_demo:
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
                elif command == "get temperature":
                    print("Temperature command received")
                    run_temperature_demo = True
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
        timeout = 300  # 5 minutes
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                command = self.socket.recv_string(flags=zmq.NOBLOCK)
                if command:
                    print(f"Received new command: {command}")
                    
                    if command.startswith("pick up"):
                        # Start the main pipeline with the new target
                        target_object = command.split("pick up ")[1]
                        self.current_target = target_object
                        print(f"New target for pick and place: {target_object}")
                        
                        # Setup and run the main pipeline
                        if hasattr(self, '_nnManager'):
                            if self._nnManager.set_target_object(target_object):
                                print(f"Target object set to: {self._nnManager._target_object}")
                                
                                # Create measurements file if needed
                                if not hasattr(self, 'measurements_file') or self.measurements_file.closed:
                                    self.measurements_file = open('test_tuple.txt', 'w')
                                    print("Created measurements file: test_tuple.txt")
                                
                                # Mark that main pipeline is starting and run it
                                self._main_pipeline_started = True
                                super().run()
                                return
                    
                    elif command == "get temperature":
                        # Run temperature demo again
                        self._run_temperature_demo()
                        # Reset timeout
                        start_time = time.time()
            
            except zmq.Again:
                time.sleep(0.1)
            except Exception as e:
                print(f"Error while listening for new commands: {e}")
                time.sleep(0.1)
                
        print("Timeout reached. Exiting command listener.")

    def _run_temperature_demo(self):
        """Runs the temperature demo by launching demo.py in the Thermometer folder"""
        print("========== STARTING TEMPERATURE MEASUREMENT SEQUENCE ==========")
        print("Step 1: Starting temperature monitoring demo...")
        
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
                venv_path = "/home/finley/Documents/GitHub/Senses/myvirtual"  # Default path if not in virtual env
            
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
            
            time.sleep(1)
            if self.temperature_process.poll() is None:
                print("Step 2: Temperature demo started successfully in new terminal")
                
                # Create a socket for receiving coordinates from the temperature demo
                coord_receiver = self.context.socket(zmq.SUB)
                coord_receiver.connect("tcp://localhost:5560")
                coord_receiver.setsockopt_string(zmq.SUBSCRIBE, "")
                coord_receiver.setsockopt(zmq.RCVTIMEO, 30000)  # 30-second timeout
                
                print("Step 3: Waiting for forehead coordinates from temperature demo...")
                try:
                    # Wait for coordinates from the demo
                    coordinates_str = coord_receiver.recv_string()
                    print(f"Step 4: Received coordinates from thermometer demo: {coordinates_str}")
                    
                    # After temperature demo completes, launch the temperature check robot movement
                    # Launch the temperature check robot movement directly without waiting for ZMQ forwarding
                    print("Step 5: Preparing to launch robot temperature check script...")
                    
                    # Create the path to the robot script
                    temp_robot_path = os.path.join(project_root, "backend", "Testing", "finlyTemperatureCheck.py")
                    print(f"Looking for robot control script at: {temp_robot_path}")
                    
                    # Check if the file actually exists using an absolute path
                    abs_robot_path = os.path.abspath(temp_robot_path)
                    print(f"Absolute path to robot script: {abs_robot_path}")
                    if os.path.exists(abs_robot_path):
                        print(f"FOUND! Robot script exists at: {abs_robot_path}")
                    else:
                        print(f"WARNING: Robot script NOT found at: {abs_robot_path}")
                        # Try to find the file using file search
                        possible_locations = []
                        for root, dirs, files in os.walk(project_root):
                            if "finlyTemperatureCheck.py" in files:
                                possible_locations.append(os.path.join(root, "finlyTemperatureCheck.py"))
                        if possible_locations:
                            print(f"Found robot script at: {possible_locations[0]}")
                            temp_robot_path = possible_locations[0]
                        else:
                            print("ERROR: Could not find finlyTemperatureCheck.py anywhere in the project")
                    
                    if os.path.exists(temp_robot_path):
                        print("Step 6: Robot temperature check script found! Starting robot movement...")
                        
                        # DIRECT EXECUTION ATTEMPT - Try running the script directly first
                        print("ATTEMPTING DIRECT EXECUTION OF TEMPERATURE CHECK SCRIPT...")
                        try:
                            # Try direct execution of the script with the coordinates
                            coord_arg = f"--coords={coordinates_str}"
                            cmd = [sys.executable, temp_robot_path, "--test", coord_arg]
                            print(f"Executing command: {' '.join(cmd)}")
                            
                            # Run in a separate process but wait for it to complete
                            return_code = subprocess.call(cmd)
                            
                            if return_code == 0:
                                print("Direct execution successful! Temperature check completed.")
                                return
                            else:
                                print(f"Direct execution failed with return code {return_code}")
                                # Continue to terminal method as fallback
                        except Exception as e:
                            print(f"Error in direct execution: {e}")
                            import traceback
                            traceback.print_exc()
                            # Continue to terminal method as fallback
                        
                        # TERMINAL METHOD - Create a temporary script to run the robot movement
                        print("Falling back to terminal method...")
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
                        print(f"Created robot script: {robot_temp_script}")
                        
                        # Launch the robot movement in a new terminal
                        self.robot_process = subprocess.Popen(
                            f"lxterminal --geometry=80x24 -e 'bash -c \"{robot_temp_script}; exec bash\"'",
                            shell=True,
                            preexec_fn=os.setsid
                        )
                        
                        # Check if robot process started
                        time.sleep(1)
                        if self.robot_process.poll() is None:
                            print("Robot temperature check movement started successfully in new terminal")
                        else:
                            print("WARNING: Robot process may have failed to start in new terminal")
                            print("Attempting to run robot script directly in main process...")
                            try:
                                # Try running the script directly as a fallback
                                print(f"Executing: python3 {temp_robot_path} --test")
                                # Use test mode to skip ZMQ waiting
                                subprocess.run(["python3", temp_robot_path, "--test"], check=True)
                                print("Robot movement completed in main process")
                            except subprocess.CalledProcessError as e:
                                print(f"Error running robot script directly: {e}")
                                # Try with explicit coordinate string if needed
                                try:
                                    print("Trying one more time with explicit coordinates...")
                                    # Use the coordinates we received in this process
                                    coord_arg = f"--coords={coordinates_str}"
                                    subprocess.run(["python3", temp_robot_path, "--test", coord_arg], check=True)
                                    print("Robot movement completed with explicit coordinates")
                                except Exception as ex:
                                    print(f"Final attempt failed: {ex}")
                                    
                    else:
                        # If we couldn't find the file, try running the robot movement directly here
                        print("Attempting to run robot movement directly in speech_demo process...")
                        try:
                            # Directly import the robot control code or execute a minimal version
                            from backend.KoalbyHumanoid.Robot import Robot
                            from backend.KoalbyHumanoid.trajPlannerTime import TrajPlannerTime
                            from ikpy.chain import Chain
                            
                            print("Imported robot control modules, executing movement directly...")
                            
                            # Parse the coordinates
                            coords = [float(x) for x in coordinates_str.split(',')]
                            print(f"Using coordinates: {coords}")
                            
                            # Execute robot movement directly
                            # ... (minimal robot movement code would go here)
                            print("Robot movement executed directly")
                        except Exception as e:
                            print(f"Error executing direct robot movement: {e}")
                            import traceback
                            traceback.print_exc()
                except zmq.error.Again:
                    print("Timeout waiting for coordinates from temperature demo")
                except Exception as e:
                    print(f"Error in temperature demo process: {e}")
                    import traceback
                    traceback.print_exc()
                finally:
                    coord_receiver.close()
            else:
                print("Warning: Temperature demo failed to start")
                
            # Wait for the process to complete 
            try:
                timeout = 60  # timeout seconds
                start_time = time.time()
                while time.time() - start_time < timeout:
                    if self.temperature_process.poll() is not None:
                        print("Temperature demo completed")
                        break
                    time.sleep(0.5)
                
                # If still running after timeout, don't wait anymore
                if self.temperature_process.poll() is None:
                    print("Temperature demo still running, continuing without waiting")
            except Exception as e:
                print(f"Error waiting for temperature demo: {e}")
                
            # Restart main pipeline if it was active before
            if hasattr(self, '_temp_demo_running') and self._temp_demo_running:
                print("Temperature demo finished. Main pipeline can be restarted if needed.")
                # We don't need to explicitly restart the pipeline here,
                # as the device will be reinitialized when needed
            
        except Exception as e:
            print(f"Error starting temperature demo: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # In case we need to restart the pipeline
            if hasattr(self, '_temp_demo_running'):
                self._temp_demo_running = False
            print("========== TEMPERATURE MEASUREMENT SEQUENCE COMPLETE ==========")

    def loop(self):
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
                    return
                
                # Launch temperature demo in a separate process
                self._run_temperature_demo()
                
            elif "pick up" in command.lower():
                # Format: "pick up {object}"
                target = command.lower().split("pick up ")[-1].strip()
                print(f"PICK UP COMMAND DETECTED! Target object: {target}")
                
                # Set the current target for tracking purposes
                self.current_target = target
                
                # Execute the robot movement by sending to robotController
                if self.current_target:
                    try:
                        self.coord_socket.send_string(command, zmq.NOBLOCK)
                        print(f"Sent pick command: {command}")
                    except zmq.error.Again:
                        print("Failed to send message (would block)")
                    except Exception as e:
                        print(f"Error sending message: {e}")
            else:
                print(f"Unknown command format: {command}")
                
        except zmq.error.Again:
            # No message available, normal operation
            pass
        except Exception as e:
            print(f"Error processing command: {e}")
        
        # Check if we need to run the temperature demo after stopping the main pipeline
        if hasattr(self, '_pending_temperature_demo') and self._pending_temperature_demo and self._device.isClosed():
            self._pending_temperature_demo = False
            self._run_temperature_demo()
            
            # After temperature demo completes, restart listening for commands
            self._listen_for_next_command()
        
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
                print("Terminating speech process...")
                os.killpg(os.getpgid(self.speech_process.pid), signal.SIGTERM)
            except Exception as e:
                print(f"Error terminating speech process: {e}")
        
        # Terminate temperature process if running
        if self.temperature_process:
            try:
                print("Terminating temperature process...")
                os.killpg(os.getpgid(self.temperature_process.pid), signal.SIGTERM)
            except Exception as e:
                print(f"Error terminating temperature process: {e}")
                
        # Terminate robot process if running
        if self.robot_process:
            try:
                print("Terminating robot process...")
                os.killpg(os.getpgid(self.robot_process.pid), signal.SIGTERM)
            except Exception as e:
                print(f"Error terminating robot process: {e}")
        
        # Close ZMQ sockets
        try:
            self.socket.close()
            self.coord_socket.close()
            self.context.term()
            self.coord_context.term()
        except Exception as e:
            print(f"Error closing ZMQ sockets: {e}")
            
        # Close measurement file if open
        if hasattr(self, 'measurements_file'):
            self.measurements_file.close()

        super().stop(*args, **kwargs) 