#!/usr/bin/env python3

print("===== FINLY TEMPERATURE CHECK SCRIPT STARTED =====")

import numpy as np
import matplotlib.pyplot as plt
import sys, time, math, array
import zmq
import argparse
from ikpy.chain import Chain
from ikpy.utils import plot as plot_utils
sys.path.append("./")
from backend.KoalbyHumanoid.Robot import Robot
from backend.KoalbyHumanoid.trajPlannerTime import TrajPlannerTime
from backend.Testing import finlyViaPoints as via
import os
import subprocess

# Parse arguments
parser = argparse.ArgumentParser(description='Temperature check robot movement')
parser.add_argument('--test', action='store_true', help='Run with test coordinates instead of waiting for ZMQ')
parser.add_argument('--coords', type=str, default="0.49076,-0.08197,0.76541", 
                    help='Comma-separated coordinates to use when testing (default: "0.49076,-0.08197,0.76541")')
args = parser.parse_args()

# Use test coordinates if specified
if args.test:
    print(f"Running in test mode with coordinates: {args.coords}")
    final_points = np.array([float(x) for x in args.coords.split(',')])
    print(f"Test coordinates parsed: {final_points}")
else:
    # ZMQ setup
    print("Setting up ZMQ communication for temperature check robot movement...")
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect("tcp://localhost:5560")
    socket.setsockopt_string(zmq.SUBSCRIBE, "")
    socket.setsockopt(zmq.RCVTIMEO, 120000)  # 120-second timeout 
    print("ZMQ connection established to port 5560 for forehead coordinates")

    # Give some time for the connection to establish
    print("Waiting for connection to establish...")
    time.sleep(2)

    # Try to receive coordinates from the temperature demo
    print("Waiting for forehead coordinates from thermometer demo (timeout: 120s)...")
    try:
        message = socket.recv_string()
        print(f"Raw message received: {message}")   
        
        try:
            coordinates = [float(x) for x in message.split(',')]
            final_points = np.array(coordinates)
            print(f"Successfully parsed coordinates: {final_points}")
        except Exception as e:
            print(f"Error parsing coordinate string: {e}")
            print(f"Using default coordinates instead")
            final_points = np.array([0.49076, -0.08197, 0.76541])  # Default coordinates if parsing fails
    except zmq.Again:
        print("Timeout waiting for coordinates, using default values")
        final_points = np.array([0.49076, -0.08197, 0.76541])  # Default coordinates if none received
    except Exception as e:
        print(f"Error receiving coordinates: {e}")
        import traceback
        traceback.print_exc()
        final_points = np.array([0.49076, -0.08197, 0.76541])  # Default coordinates if error
    finally:
        print("Closing ZMQ socket...")
        socket.close()
        context.term()
        print("ZMQ socket closed")

def find_file(filename, search_path="/home/finley"): 
    result = []    
    for root, dirs, files in os.walk(search_path):        
        if filename in files: 
            result.append(os.path.join(root, filename))    
    return result 
    
# Find all instances of your URDF file 
found_paths = find_file("FullAssemFIN_straight_2025_5.urdf")
print("Found URDF files at:", found_paths)

# If found, use the first instance
if found_paths: 
    urdf_path = found_paths[0] 

    left_leg_chain = Chain.from_urdf_file(
    urdf_path,
    base_elements=['shoulder1_left', 'shoulder1_left'],
    active_links_mask=[False, True, True, True, True, True, True, True]
)

    camera = Chain.from_urdf_file(
    urdf_path,
    base_elements=['neck', 'neck']   
)

camera_angles=np.array([0,0,0,0])
camera_frame_transformation=camera.forward_kinematics(camera_angles)

# sim or real robot
is_real = False
robot = Robot(is_real)
print("Temperature Check Setup Complete")

# Set starting angles
robot.motors[5].target = (math.radians(0), 'P')
robot.motors[6].target = (math.radians(0), 'P')
robot.motors[7].target = (math.radians(0), 'P')
robot.motors[8].target = (math.radians(0), 'P')
robot.motors[9].target = (math.radians(0), 'P')
robot.motors[10].target = (math.radians(0), 'P')

ik_solution_2=np.array([0,0,0,0,0,0,0,0])
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
    [[.50575,  -.006620, .28607],
   [x_coord, y_coord, z_coord] ],
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
    robot.motors[5].target = (motor_angle_task[1], 'P')
    robot.motors[6].target = (motor_angle_task[2], 'P')
    robot.motors[7].target = (motor_angle_task[3], 'P')
    robot.motors[8].target = (motor_angle_task[4], 'P')
    robot.motors[9].target = (motor_angle_task[5], 'P')
    
    # Move the robot
    robot.moveAllToTarget()
    time.sleep(0.01)

print("Reached forehead position. Holding for temperature measurement...")
# Hold at forehead position for 3 seconds
time.sleep(3)

# Run temperature script as a subprocess outside of virtual environment
print("Running temperature measurement script...")
temp_script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../Gripper/thermometer/getTemp_MLX90614.py")
temp_script_path = os.path.normpath(temp_script_path)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
print(f"Temperature script path: {temp_script_path}")

# Create a temporary shell script
temp_shell_script = "/tmp/temperature_measure.sh"
with open(temp_shell_script, "w") as f:
    f.write(f"""#!/bin/bash
echo "Starting temperature measurement..."
export PYTHONPATH="{project_root}:$PYTHONPATH"
cd {os.path.dirname(temp_script_path)}
python3 {os.path.basename(temp_script_path)}
""")
os.chmod(temp_shell_script, 0o755)

try:
    # Launch in a new terminal window
    temp_process = subprocess.Popen(
        f"lxterminal --geometry=80x24 -e 'bash -c \"{temp_shell_script}; exec bash\"'",
        shell=True,
        preexec_fn=os.setsid
    )
    
    # Give it some time to run
    print("Waiting for temperature measurement to complete...")
    time.sleep(5)
    
    # Check if output file exists and read it
    if os.path.exists("/tmp/temperature_output.txt"):
        with open("/tmp/temperature_output.txt", "r") as output_file:
            temperature_output = output_file.read()
            print(f"Temperature script output: {temperature_output}")
        
        # Save temperature to file
        with open("Gripper/thermometer/temperature.txt", "w") as temp_file:
            temp_file.write(temperature_output)
        
        print("Temperature data saved to temperature.txt")
    else:
        print("Temperature output file not found")
        
    # Check exit code
    if os.path.exists("/tmp/temperature_exit_code.txt"):
        with open("/tmp/temperature_exit_code.txt", "r") as code_file:
            exit_code = code_file.read().strip()
            print(f"Temperature script exit code: {exit_code}")
            
except Exception as e:
    print(f"Error running temperature script: {e}")

print("Temperature check movement complete.") 

# # Return to starting position
# print("Returning to starting position...")
# robot.motors[5].target = (math.radians(0), 'P')
# robot.motors[6].target = (math.radians(0), 'P')
# robot.motors[7].target = (math.radians(0), 'P')
# robot.motors[8].target = (math.radians(0), 'P')
# robot.motors[9].target = (math.radians(0), 'P')
# robot.motors[10].target = (math.radians(0), 'P')

# returnTime = time.time()
# while time.time() - returnTime < 3:
#     robot.moveAllToTarget()
#     time.sleep(0.01)
