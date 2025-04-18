import os
import numpy as np
import matplotlib.pyplot as plt
from ikpy.chain import Chain
from ikpy.utils import plot as plot_utils
import sys, time, math, array
import zmq

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
found_paths = find_file("FullAssemFIN_straight_2025_5.urdf")
print("Found URDF files at:", found_paths)
urdf_path = "/Senses/backend/Testing/FullAssemFIN_straight_2025_5.urdf"

# Creating URDF chain for left arm
left_arm_chain = Chain.from_urdf_file(
    urdf_path,
    base_elements=['shoulder1_left', 'shoulder1_left']
)
# creating URDF chain for camera
camera = Chain.from_urdf_file(
    urdf_path,
    base_elements=['neck', 'neck']
)
#forward kinematics for camera chain
camera_angles=np.array([0,0,0,0])
camera_frame_transformation=camera.forward_kinematics(camera_angles)

# Edit to declare if you are testing the sim or the real robot
is_real = False
robot = Robot(is_real)
print("Setup Complete")
# positions
#Starting Agnles

prevTime = time.time()
simStartTime = time.time()
while time.time() - simStartTime < 2: #Waypoint 1 
    time.sleep(0.01)
    robot.motors[5].target = (math.radians(0), 'P')
    robot.motors[6].target = (math.radians(0), 'P')
    robot.motors[7].target = (math.radians(0), 'P')
    robot.motors[8].target = (math.radians(0), 'P')
    robot.motors[9].target = (math.radians(0), 'P')
    #robot.IMUBalance(0,0)
    robot.moveAllToTarget()


while time.time() - simStartTime < 2:#Waypoint 2
    time.sleep(0.01)
    robot.motors[5].target = (math.radians(0), 'P')
    robot.motors[6].target = (math.radians(90), 'P')
    robot.motors[7].target = (math.radians(0), 'P')
    robot.motors[8].target = (math.radians(0), 'P')
    robot.motors[9].target = (math.radians(0), 'P')
    robot.moveAllToTarget()


while time.time() - simStartTime < 2:#Waypoint 3
    time.sleep(0.01)
    robot.motors[5].target = (math.radians(90), 'P')
    robot.motors[6].target = (math.radians(0), 'P')
    robot.motors[7].target = (math.radians(0), 'P')
    robot.motors[8].target = (math.radians(0), 'P')
    robot.motors[9].target = (math.radians(0), 'P')
    robot.moveAllToTarget()

while time.time() - simStartTime < 2:#Waypoint 4
    time.sleep(0.01)
    robot.motors[5].target = (math.radians(-117), 'P')
    robot.motors[6].target = (math.radians(-103), 'P')
    robot.motors[7].target = (math.radians(0), 'P')
    robot.motors[8].target = (math.radians(-53), 'P')
    robot.motors[9].target = (math.radians(45), 'P')
    robot.moveAllToTarget()

# centering all angles to zero



# conversion of final points from camera coordinate systm to rorbot coordinate system 
# final_points=np.array([0, .3, 0])
# B=np.array([[final_points[0]],[final_points[1]],[final_points[2]],[1]])
# A= camera_frame_transformation
# final_points=np.array([0,0, 0])
# C = np.dot(A, B)




#leftArmTraj = [
   # [[0,0,0], [20,20,20]],
  #  [[.49076,  -.08197, .76541],
 #  [C[0],  C[1], C[2]] ],
 #   [[0,0,0], [0,0,0]],
#    [[0,0,0], [0,0,0]]
#]
