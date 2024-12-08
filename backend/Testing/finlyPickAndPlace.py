import numpy as np
import matplotlib.pyplot as plt
import os 
import zmq
import time

from ikpy.chain import Chain
from ikpy.utils import plot as plot_utils

import sys, time, math, array

import numpy as np
sys.path.append("./")
from backend.KoalbyHumanoid.Robot import Robot
from backend.KoalbyHumanoid.trajPlannerTime import TrajPlannerTime

from backend.Testing import finlyViaPoints as via

def find_file(filename, search_path="/home/finley"): 
    result = []    
    for root, dirs, files in os.walk(search_path):        
        if filename in files: 
            result.append(os.path.join(root, filename))    
    return result 
    
# Find all instances of your URDF file 
found_paths = find_file("FullAssemFIN.urdf")
print("Found URDF files at:", found_paths)

# If found, use the first instance
if found_paths: 
    urdf_path = found_paths[0] 

    left_leg_chain = Chain.from_urdf_file(
        urdf_path,
        base_elements=['left_shoulder1', 'left_shoulder_twist']
    )

# Edit to declare if you are testing the sim or the real robot
is_real = False

robot = Robot(is_real)

print("Setup Complete")

# positions

final_position=np.array([0.07089,  -0.26614,  .68187])

motor_angle_joint=np.array([0,0,0,0,0])

#Starting Angles

robot.motors[5].target = (math.radians(90), 'P')
robot.motors[6].target = (math.radians(90), 'P')
robot.motors[7].target = (math.radians(0), 'P')
robot.motors[8].target = (math.radians(0), 'P')
robot.motors[9].target = (math.radians(0), 'P')
robot.motors[10].target = (math.radians(0), 'P')

ik_solution_2=np.array([0,0,0,0,0,0,0])
prevTime = time.time()

simStartTime = time.time()

while time.time() - simStartTime < 2:
    time.sleep(0.01)
    robot.IMUBalance(0,0)
    robot.moveAllToTarget()

def setup_zmq_subscriber():
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect("tcp://localhost:5558")
    socket.setsockopt_string(zmq.SUBSCRIBE, "")
    return context, socket

# modify coordinates section
context, socket = setup_zmq_subscriber()
try:
    print("Waiting for coordinates from vision system...")
    # Wait for coordinates with timeout
    start_time = time.time()
    timeout = 180  # 3 minutes timeout
    
    while time.time() - start_time < timeout:
        try:
            coord_message = socket.recv_string(flags=zmq.NOBLOCK)
            mean_x, mean_y, mean_z = map(float, coord_message.split(','))
            print(f"Received coordinates: X={mean_x:.5f}, Y={mean_y:.5f}, Z={mean_z:.5f}")
            
            # Update leftArmTraj with the received coordinates
            leftArmTraj = [
                # time 
                [[0,0,0], [20,20,20]],
                #starting coordinates below (x,y,z)
                [[.49513,  -.04901, .28036],
                # ending coordinates (using received mean coordinates)
                [mean_x, mean_y, mean_z]],
                # velocity and acceleration (ignore)
                [[0,0,0], [0,0,0]],
                [[0,0,0], [0,0,0]]
            ]
            break
            
        except zmq.Again:
            time.sleep(0.1)  # Small sleep to prevent CPU spinning
            continue
        except Exception as e:
            print(f"Error receiving coordinates: {e}")
            break
    else:
        print("Timeout waiting for coordinates")
        # Use default coordinates if timeout
        leftArmTraj = [
            [[0,0,0], [20,20,20]],
            [[.49513,  -.04901, .28036],
             [.12938,  -.03073, .60344]],
            [[0,0,0], [0,0,0]],
            [[0,0,0], [0,0,0]]
        ]

finally:
    socket.close()
    context.term()

# get=np.array([.41263 +.02042,  -.01513 +.02647, .26667 -.02361])
# print(get)
final_position=left_leg_chain.forward_kinematics(ik_solution_2)
print(final_position)

# arred=np.array([ -3.29889867e-14,  1.33762582e+00 , 5.24790953e-01 ,-2.16606497e-02, 1.35522250e-02, -2.52929247e+00 , 0.00000000e+00])
# help=left_leg_chain.forward_kinematics(arred)
# print(help)

## EVEN TO RIGHT FOOT FORWARD
# rArm_tj = TrajPlannerTime(via.ra_grabCart[0], via.ra_grabCart[1], via.ra_grabCart[2], via.ra_grabCart[3])
lArm_tj_joint = TrajPlannerTime(leftArmTraj[0], leftArmTraj[1], leftArmTraj[2], leftArmTraj[3])

state = 0

startTime = time.time()

print("phase 2")

while time.time() - startTime < 20:
     
        target_position_task = lArm_tj_joint.getQuinticPositions(time.time() - startTime)
        target_position_2 = np.array([(target_position_task[0]), (target_position_task[1]), (target_position_task[2])])
        ik_solution = left_leg_chain.inverse_kinematics(target_position_2, initial_position=ik_solution_2 )
        ik_solution_2=ik_solution
        motor_angle_task=ik_solution

        robot.motors[5].target = (motor_angle_task[1], 'P')
        robot.motors[6].target = (motor_angle_task[2], 'P')
        robot.motors[7].target = (motor_angle_task[3], 'P')
        robot.motors[8].target = (motor_angle_task[4], 'P')
        robot.motors[9].target = (motor_angle_task[5], 'P')
        
        print(motor_angle_task)

        robot.IMUBalance(0, 0)
        robot.moveAllToTarget()
 