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
            
            print("Step 2: Temperature demo started in new terminal")
            # Skip the poll check - assume it's running regardless of poll result
            
            # Create a socket for receiving coordinates from the temperature demo
            coord_receiver = self.context.socket(zmq.SUB)
            coord_receiver.connect("tcp://localhost:5560")
            coord_receiver.setsockopt_string(zmq.SUBSCRIBE, "")
            coord_receiver.setsockopt(zmq.RCVTIMEO, 120000)  # 120-second timeout
            
            print("Step 3: Waiting for forehead coordinates from temperature demo...")
            try:
                # Wait for coordinates from the demo
                coordinates_str = coord_receiver.recv_string()
                print(f"Step 4: Received coordinates from thermometer demo: {coordinates_str}")
                
                # After receiving coordinates, try ALL methods to move the robot
                print("Step 5: Received coordinates, now trying multiple methods to move the robot...")
                
                # METHOD 1: Try creating and running a script in a new terminal
                print("METHOD 1: Launching temperature check script in new terminal...")
                temp_robot_path = os.path.join(project_root, "backend", "Testing", "finlyTemperatureCheck.py")
                
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
                
                # METHOD 3: Emergency direct method - Run the robot movement code directly in this process
                print("METHOD 3: Emergency direct method - Running robot movement directly...")
                self._emergency_direct_robot_movement(coordinates_str)
                    
            except zmq.error.Again:
                print("Timeout waiting for coordinates from temperature demo")
            except Exception as e:
                print(f"Error in temperature demo process: {e}")
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
                
                # SPECIAL FAILSAFE: If for some reason the above doesn't trigger the robot,
                # directly try to move robot with default coordinates after a delay
                def delayed_emergency_check():
                    import threading
                    import time
                    
                    # Wait 20 seconds to see if normal methods work
                    time.sleep(20)
                    
                    print("SPECIAL FAILSAFE CHECK: Checking if temperature demo worked...")
                    
                    # If robot process hasn't been started, trigger emergency method with default coordinates
                    if not hasattr(self, 'robot_process') or self.robot_process is None:
                        print("FAILSAFE ACTIVATED: No robot process detected, using emergency method")
                        default_coordinates = "0.49076,-0.08197,0.76541"
                        self._emergency_direct_robot_movement(default_coordinates)
                
                # Start the delayed check in a background thread
                import threading
                failsafe_thread = threading.Thread(target=delayed_emergency_check)
                failsafe_thread.daemon = True
                failsafe_thread.start()
                
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
                    width_values = [m['dimensions']['width'] for m in filtered_measurements if 'dimensions' in m and 'width' in m['dimensions']]
                    
                    if width_values:
                        mean_width = np.mean(width_values)
                        print(f"Publishing final mean coordinates with width: {mean_x:.5f}, {mean_y:.5f}, {mean_z:.5f}, width: {mean_width:.5f}")
                        coord_str = f"{mean_x:.5f},{mean_y:.5f},{mean_z:.5f},{mean_width:.5f}"
                    else:
                        print(f"Publishing final mean coordinates (no width available): {mean_x:.5f}, {mean_y:.5f}, {mean_z:.5f}")
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

    def _emergency_direct_robot_movement(self, coordinates_str):
        """
        Direct execution of robot temperature check functionality in case all other methods fail.
        This bypasses the finlyTemperatureCheck.py script completely and runs the functionality directly.
        """
        print("=== EMERGENCY DIRECT ROBOT MOVEMENT ===")
        try:
            # Parse the coordinates
            coords = [float(x) for x in coordinates_str.split(',')]
            print(f"Using coordinates: {coords}")
            final_points = np.array(coords)
            
            # Import required modules
            from backend.KoalbyHumanoid.Robot import Robot
            from backend.KoalbyHumanoid.trajPlannerTime import TrajPlannerTime
            from ikpy.chain import Chain
            
            # Find URDF file
            def find_file(filename, search_path="/home/finley"): 
                result = []    
                for root, dirs, files in os.walk(search_path):        
                    if filename in files: 
                        result.append(os.path.join(root, filename))    
                return result 
                
            # Find all instances of URDF file 
            found_paths = find_file("FinleyJNEWARMS_2024_2.urdf")
            print("Found URDF files at:", found_paths)
            
            if not found_paths:
                print("ERROR: Could not find URDF file!")
                return
                
            # Use the first instance
            urdf_path = found_paths[0] 
            
            left_leg_chain = Chain.from_urdf_file(
                urdf_path,
                base_elements=['shoulder1_left', 'shoulder1_left'],
                active_links_mask=[False, True, True, True, True, True, True]
            )
            
            camera = Chain.from_urdf_file(
                urdf_path,
                base_elements=['neck', 'neck']   
            )
            
            camera_angles=np.array([0,0,0,0])
            camera_frame_transformation=camera.forward_kinematics(camera_angles)
            
            # Initialize robot
            is_real = True
            robot = Robot(is_real)
            print("Robot initialized")
            
            # Set starting angles
            robot.motors[5].target = (math.radians(0), 'P')
            robot.motors[6].target = (math.radians(0), 'P')
            robot.motors[7].target = (math.radians(0), 'P')
            robot.motors[8].target = (math.radians(0), 'P')
            robot.motors[9].target = (math.radians(0), 'P')
            robot.motors[10].target = (math.radians(0), 'P')
            
            ik_solution_2 = np.array([0,0,0,0,0,0,0])
            prevTime = time.time()
            simStartTime = time.time()
            
            # Wait for robot to reach starting position
            while time.time() - simStartTime < 2:
                time.sleep(0.01)
                robot.moveAllToTarget()
            
            # Transform the coordinates from camera frame to robot frame
            B = np.array([[final_points[0]], [final_points[2]], [final_points[1]], [1]])
            A = camera_frame_transformation
            C = np.dot(A, B)
            print(f"Transformed forehead coordinates: {C}")
            
            # Extract scalar values from the numpy array for formatting
            x_coord = float(C[0][0])
            y_coord = float(C[1][0])
            z_coord = float(C[2][0])
            
            # Set up trajectory for moving to forehead
            leftArmTraj = [
                [[0,0,0], [20,20,20]],
                [[.49076, -.08197, .76541],
                 [x_coord, y_coord, z_coord]],
                [[0,0,0], [0,0,0]],
                [[0,0,0], [0,0,0]]
            ]
            
            print(f"Moving robot arm to forehead coordinates: {x_coord:.4f}, {y_coord:.4f}, {z_coord:.4f}")
            
            lArm_tj_joint = TrajPlannerTime(leftArmTraj[0], leftArmTraj[1], leftArmTraj[2], leftArmTraj[3])
            state = 0
            startTime = time.time()
            
            print("Beginning movement to forehead position...")
            
            # Movement to forehead position
            while time.time() - startTime < 20:
                target_position_task = lArm_tj_joint.getQuinticPositions(time.time() - startTime)
                target_position_2 = np.array([(target_position_task[0]), (target_position_task[1]), (target_position_task[2])])
                ik_solution = left_leg_chain.inverse_kinematics(target_position_2, initial_position=ik_solution_2)
                ik_solution_2 = ik_solution
                motor_angle_task = ik_solution
                
                # Set motor targets exactly as in the original file
                robot.motors[5].target = (-motor_angle_task[1], 'P')
                robot.motors[6].target = (motor_angle_task[2], 'P')
                robot.motors[7].target = (-motor_angle_task[3], 'P')
                robot.motors[8].target = (motor_angle_task[4], 'P')
                robot.motors[9].target = (motor_angle_task[5], 'P')
                
                # Move the robot
                robot.moveAllToTarget()
                time.sleep(0.01)
            
            print("Reached forehead position. Holding for temperature measurement...")
            # Hold at forehead position for 3 seconds
            time.sleep(3)
            
            # Return to starting position
            print("Returning to starting position...")
            robot.motors[5].target = (math.radians(0), 'P')
            robot.motors[6].target = (math.radians(0), 'P')
            robot.motors[7].target = (math.radians(0), 'P')
            robot.motors[8].target = (math.radians(0), 'P')
            robot.motors[9].target = (math.radians(0), 'P')
            robot.motors[10].target = (math.radians(0), 'P')
            
            returnTime = time.time()
            while time.time() - returnTime < 3:
                robot.moveAllToTarget()
                time.sleep(0.01)
                
            print("Temperature check movement complete.")
            return True
        except Exception as e:
            print(f"Error in direct robot movement: {e}")
            import traceback
            traceback.print_exc()
            return False 