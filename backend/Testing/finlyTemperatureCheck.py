#!/usr/bin/env python3
import numpy as np
import matplotlib.pyplot as plt
import sys, time, math, array
import zmq
from ikpy.chain import Chain
from ikpy.utils import plot as plot_utils
sys.path.append("./")
from backend.KoalbyHumanoid.Robot import Robot
from backend.KoalbyHumanoid.trajPlannerTime import TrajPlannerTime
from backend.Testing import finlyViaPoints as via
import os

# ZMQ setup
context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect("tcp://localhost:5560")
socket.setsockopt_string(zmq.SUBSCRIBE, "")
socket.setsockopt(zmq.RCVTIMEO, 30000)  # 30-second timeout

def find_file(filename, search_path="/home/finley"): 
    result = []    
    for root, dirs, files in os.walk(search_path):        
        if filename in files: 
            result.append(os.path.join(root, filename))    
    return result 
    
# Find all instances of your URDF file 
found_paths = find_file("FinleyJNEWARMS_2024_2.urdf")
print("Found URDF files at:", found_paths)

# If found, use the first instance
if found_paths: 
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

# sim or real robot
is_real = True
robot = Robot(is_real)
print("Temperature Check Setup Complete")

# Try to receive coordinates from the temperature demo
try:
    print("Waiting for forehead coordinates from temperature demo...")
    message = socket.recv_string()
    coordinates = [float(x) for x in message.split(',')]
    final_points = np.array(coordinates)
    print(f"Received forehead coordinates: {final_points}")
except zmq.Again:
    print("Timeout waiting for coordinates, using default values")
    final_points = np.array([0.49076, -0.08197, 0.76541])  # Default coordinates if none received
except Exception as e:
    print(f"Error receiving coordinates: {e}")
    final_points = np.array([0.49076, -0.08197, 0.76541])  # Default coordinates if error
finally:
    socket.close()
    context.term()

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

# Set up trajectory for moving to forehead
leftArmTraj = [
    [[0,0,0], [20,20,20]],
    [[.49076, -.08197, .76541],
     [C[0], C[1], C[2]]],
    [[0,0,0], [0,0,0]],
    [[0,0,0], [0,0,0]]
]

print(f"Moving robot arm to forehead coordinates: {C[0]:.4f}, {C[1]:.4f}, {C[2]:.4f}")

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