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
socket.connect("tcp://localhost:5559")
socket.setsockopt_string(zmq.SUBSCRIBE, "")
socket.setsockopt(zmq.RCVTIMEO, 180000)  

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

    left_arm_chain = Chain.from_urdf_file(
        urdf_path,
        base_elements=['shoulder1_left', 'shoulder1_left'],
        active_links_mask=[False, True, True, True, True, True, True, True]
    )

    camera = Chain.from_urdf_file(
        urdf_path,
        base_elements=['neck', 'neck']   
    )

camera_angles = np.array([0,0,0,0])
camera_frame_transformation = camera.forward_kinematics(camera_angles)

# sim or real robot
is_real = True
robot = Robot(is_real)
print("Setup Complete")

# Try to receive coordinates with timeout
try:
    message = socket.recv_string()
    coordinates = [float(x) for x in message.split(',')]
    final_points = np.array(coordinates)
    print(f"Received coordinates: {final_points}")
except zmq.Again:
    print("Timeout waiting for coordinates, using default values")
    final_points = np.array([0, 0, 0])
except Exception as e:
    print(f"Error receiving coordinates: {e}")
    final_points = np.array([0, 0, 0])
finally:
    socket.close()
    context.term()

# Initialize robot to starting position
# Starting Angles for arm
robot.motors[5].target = (math.radians(0), 'P')
robot.motors[6].target = (math.radians(0), 'P')
robot.motors[7].target = (math.radians(0), 'P')
robot.motors[8].target = (math.radians(0), 'P')
robot.motors[9].target = (math.radians(0), 'P')
robot.motors[10].target = (math.radians(0), 'P')

# Initialize gripper position - make sure it's open to start
robot.motors[27].target = (math.radians(60), 'P')  # Set gripper to open position

ik_solution_2=np.array([0,0,0,0,0,0,0,0])
prevTime = time.time()
simStartTime = time.time()

# Allow time for initial positioning
while time.time() - simStartTime < 2:
    time.sleep(0.01)
    #robot.IMUBalance(0,0)
    robot.moveAllToTarget()

# Transform coordinates from camera frame to robot frame
# Note the coordinate system as described: Positive X is left, Z through robot, positive Y is up
# So: X→X, Y→Z, Z→Y ?
B = np.array([[final_points[0]], [final_points[2]], [final_points[1]], [1]])
A = camera_frame_transformation
C = np.dot(A, B)
print("Target position in robot frame:", C)

# Define trajectory from current position to target position
leftArmTraj = [
    [[0,0,0], [20,20,20]],
    [[.49076, -.08197, .76541],  # Starting position
     [C[0], C[1], C[2]]],        # Target position (from camera)
    [[0,0,0], [0,0,0]],
    [[0,0,0], [0,0,0]]
]

# Create trajectory planner
lArm_tj_joint = TrajPlannerTime(leftArmTraj[0], leftArmTraj[1], leftArmTraj[2], leftArmTraj[3])
state = 0
startTime = time.time()

print("Phase 1: Moving arm to target position")

# Phase 1: Move arm to target position
while time.time() - startTime < 20:
    target_position_task = lArm_tj_joint.getQuinticPositions(time.time() - startTime)
    target_position_2 = np.array([(target_position_task[0]), (target_position_task[1]), (target_position_task[2])])
    ik_solution = left_arm_chain.inverse_kinematics(target_position_2, initial_position=ik_solution_2)
    ik_solution_2 = ik_solution
    motor_angle_task = ik_solution

    robot.motors[5].target = (motor_angle_task[1], 'P')  # Using positive angles as in new code
    robot.motors[6].target = (motor_angle_task[2], 'P')
    robot.motors[7].target = (motor_angle_task[3], 'P')
    robot.motors[8].target = (motor_angle_task[4], 'P')
    robot.motors[9].target = (motor_angle_task[5], 'P')
    
    print(motor_angle_task)

    #robot.IMUBalance(0, 0)
    robot.moveAllToTarget()
    
    # Check if we're close enough to target to stop early
    if time.time() - startTime > 5:  # At least move for 5 seconds
        # Calculate error
        current_pos = left_arm_chain.forward_kinematics(motor_angle_task)[:3, 3]
        target_pos = np.array([C[0][0], C[1][0], C[2][0]])
        error = np.linalg.norm(current_pos - target_pos)
        
        if error < 0.05:  # If within 5cm of target
            print("Reached target position early")
            break

# Save the final position for orientation phase
target_position_2 = target_position_2
turnPosition = target_position_2
turnAngles = motor_angle_task

# Phase 2: Orient the gripper for grasping
print("Phase 2: Orienting gripper")

# Set orientation to align gripper with object
target_orientation_z = [1, 0, 0]  # Adjust based on your gripper orientation needs
ik_solution_oriented = left_arm_chain.inverse_kinematics(
    target_position_2, 
    target_orientation=target_orientation_z, 
    orientation_mode="Z", 
    initial_position=ik_solution_2
)

# Create a trajectory from current orientation to desired orientation
leftArmTraj = [
    [[0,0,0,0,0], [10,10,10,10,10]],
    [[motor_angle_task[1], motor_angle_task[2], motor_angle_task[3], motor_angle_task[4], motor_angle_task[5]],
     [ik_solution_oriented[1], ik_solution_oriented[2], ik_solution_oriented[3], ik_solution_oriented[4], ik_solution_oriented[5]]],
    [[0,0,0,0,0], [0,0,0,0,0]],
    [[0,0,0,0,0], [0,0,0,0,0]]
]

lArm_tj_joint = TrajPlannerTime(leftArmTraj[0], leftArmTraj[1], leftArmTraj[2], leftArmTraj[3])

startTime = time.time()
while time.time() - startTime < 5:  # Shorter time for orientation phase
    target_position_joint = lArm_tj_joint.getQuinticPositions(time.time() - startTime)

    robot.motors[5].target = (target_position_joint[0], 'P')
    robot.motors[6].target = (target_position_joint[1], 'P')
    robot.motors[7].target = (target_position_joint[2], 'P')
    robot.motors[8].target = (target_position_joint[3], 'P')
    robot.motors[9].target = (target_position_joint[4], 'P')
    
    #robot.IMUBalance(0, 0)
    robot.moveAllToTarget()

# Phase 3: Close the gripper to grasp object
print("Phase 3: Closing gripper to grasp object")

# Start from current gripper position
gripperAngle = 60  # Open position
startTime = time.time()

# Gradually close the gripper
while time.time() - startTime < 5:  # 5 seconds to close
    gripperAngle = max(0, 60 - (60 * (time.time() - startTime) / 5))  # Linear decrease to closed position
    robot.motors[27].target = (math.radians(gripperAngle), 'P')
    
    #robot.IMUBalance(0, 0)
    robot.moveAllToTarget()
    time.sleep(0.01)

print("Pick and place operation complete")