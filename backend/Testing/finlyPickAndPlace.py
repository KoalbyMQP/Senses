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
# context = zmq.Context()
# socket = context.socket(zmq.SUB)
# socket.connect("tcp://localhost:5559")
# socket.setsockopt_string(zmq.SUBSCRIBE, "")
# socket.setsockopt(zmq.RCVTIMEO, 180000)  

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
print("Setup Complete")

# Try to receive coordinates from with timeout
# try:
#     message = socket.recv_string()
#     coordinates = [float(x) for x in message.split(',')]
#     final_points = np.array(coordinates)
#     print(f"Received coordinates: {final_points}")
# except zmq.Again:
#     print("Timeout waiting for coordinates, using default values")
#     final_points = np.array([0, 0, 0])
# except Exception as e:
#     print(f"Error receiving coordinates: {e}")
#     final_points = np.array([0, 0, 0])
# finally:
#     socket.close()
#     context.term()

# positions
final_position = np.array([0.07089, -0.26614, .68187])
motor_angle_joint = np.array([0,0,0,0,0])

#Starting Angles            
robot.motors[5].target = (math.radians(0), 'P')
robot.motors[6].target = (math.radians(0), 'P')
robot.motors[7].target = (math.radians(0), 'P')
robot.motors[8].target = (math.radians(0), 'P')
robot.motors[9].target = (math.radians(0), 'P')
robot.motors[10].target = (math.radians(0), 'P')

ik_solution_2 = np.array([0,0,0,0,0,0,0])
prevTime = time.time()
simStartTime = time.time()

while time.time() - simStartTime < 2:
    time.sleep(0.01)
    #robot.IMUBalance(0,0)
    robot.moveAllToTarget()

# B = np.array([[final_points[0]], [final_points[2]], [final_points[1]], [1]])
# A = camera_frame_transformation
# C = np.dot(A, B)
# print(C)

# leftArmTraj = [
#     [[0,0,0], [20,20,20]],
#     [[.49076, -.08197, .76541],
#      [C[0], C[1], C[2]]],
#     [[0,0,0], [0,0,0]],
#     [[0,0,0], [0,0,0]]
# ]

# final_position = left_leg_chain.forward_kinematics(ik_solution_2)
# print(final_position)

# lArm_tj_joint = TrajPlannerTime(leftArmTraj[0], leftArmTraj[1], leftArmTraj[2], leftArmTraj[3])
state = 0
startTime = time.time()

print("phase 2")

currentAngleTest=0

while time.time() - startTime < 20:
        currentAngleTest=int(time.time()-startTime)*2
        # target_position_task = lArm_tj_joint.getQuinticPositions(time.time() - startTime)
        # target_position_2 = np.array([(target_position_task[0]), (target_position_task[1]), (target_position_task[2])])
        # ik_solution = left_leg_chain.inverse_kinematics(target_position_2, initial_position=ik_solution_2)
        # ik_solution_2 = ik_solution
        # motor_angle_task = ik_solution

        # robot.motors[5].target = (motor_angle_task[1], 'P')
        # robot.motors[6].target = (motor_angle_task[2], 'P')
        # robot.motors[7].target = (motor_angle_task[3], 'P')
        # robot.motors[8].target = (motor_angle_task[4], 'P')
        # robot.motors[9].target = (motor_angle_task[5], 'P')
        
        # print(motor_angle_task)
        
        robot.motors[5].target = (math.radians(currentAngleTest), 'P')
        robot.motors[6].target = (math.radians(0), 'P')
        robot.motors[7].target = (math.radians(0), 'P')
        robot.motors[8].target = (math.radians(0), 'P')
        robot.motors[9].target = (math.radians(0), 'P')
        robot.motors[10].target = (math.radians(0), 'P')
        

        #robot.IMUBalance(0, 0)
        robot.moveAllToTarget()
