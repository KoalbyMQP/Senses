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
urdf_path = found_paths[0]

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
is_real = True
robot = Robot(is_real)
print("Setup Complete")
# positions
#Starting Agnles
# robot.motors[25].target = (math.radians(0), 'P')
# robot.motors[26].target = (math.radians(0), 'P')
# robot.motors[27].target = (math.radians(0), 'P')
robot.motors[5].target = (math.radians(0), 'P')
robot.motors[6].target = (math.radians(0), 'P')
robot.motors[7].target = (math.radians(0), 'P')
robot.motors[8].target = (math.radians(0), 'P')
robot.motors[9].target = (math.radians(0), 'P')
robot.motors[10].target =(math.radians(0), 'P')
ik_solution_2=np.array([0,0,0,0,0,0,0,0])

# centering all angles to zero
prevTime = time.time()
simStartTime = time.time()
while time.time() - simStartTime < 2:
    time.sleep(0.01)
    #robot.IMUBalance(0,0)
    robot.moveAllToTarget()
    
# Attempt to receive coordinates from speech demo for hand movement
context_zmq = zmq.Context()
coord_sub = context_zmq.socket(zmq.SUB)
coord_sub.setsockopt_string(zmq.SUBSCRIBE, "")
coord_sub.connect("tcp://localhost:5559")

# Loop until we get the coordinates from ZMQ
print("Waiting for coordinates from ZMQ...")
while True:
    poller = zmq.Poller()
    poller.register(coord_sub, zmq.POLLIN)                      
    socks = dict(poller.poll(1000))  # wait 1000 ms for a message
    if coord_sub in socks and socks[coord_sub] == zmq.POLLIN:
        coord_str = coord_sub.recv_string(zmq.NOBLOCK)
        try:
            coord_vals = [float(val) for val in coord_str.split(",")]
            if len(coord_vals) < 3:
                print("Not enough coordinate values received, waiting for valid coordinates...")
                continue
            final_points = np.array(coord_vals[:3])
            print("Received coordinates from speech demo:", final_points)
            break
        except Exception as e:
            print("Error parsing coordinates from speech demo:", e)
            print("Waiting for valid coordinates...")
    else:
        print("No coordinates received yet, continuing to wait...")

# Apply camera frame transformation to final_points
# NEGATIVE X AND NEGATIVE Z FOR CURRENT URDF
B = np.array([[-final_points[0]], [final_points[1]], [-final_points[2]], [1]])
C = np.dot(camera_frame_transformation, B)

leftArmTraj = [
    [[0,0,0], [20,20,20]],
    [[.50575,  -.006620, .28607],
   [C[0],  C[1], C[2] + 0.4 ]],
    [[0,0,0], [0,0,0]],
    [[0,0,0], [0,0,0]]
]

lArm_tj_joint = TrajPlannerTime(leftArmTraj[0], leftArmTraj[1], leftArmTraj[2], leftArmTraj[3])
startTime = time.time()
target_orientation_z=[1, 0, 0]
Angle =0
lastAngle=0

# open gripper

while time.time() - startTime < 4:
        Angle=Angle+.1
        # robot.motors[27].target = (math.radians(Angle), 'P')
        # #robot.IMUBalance(0, 0)
        # robot.moveAllToTarget()
        # lastAngle=Angle
startTime = time.time()

# move gripper
while time.time() - startTime < 20:
        target_position_task = lArm_tj_joint.getQuinticPositions(time.time() - startTime)
        target_position_2 = np.array([(target_position_task[0]), (target_position_task[1]), (target_position_task[2])])
        ik_solution = left_arm_chain.inverse_kinematics(target_position_2, initial_position=ik_solution_2 )
        ik_solution_2=ik_solution
        motor_angle_task=ik_solution
        robot.motors[5].target = (motor_angle_task[1], 'P')
        robot.motors[6].target = (motor_angle_task[2], 'P')
        robot.motors[7].target = (motor_angle_task[3], 'P')
        robot.motors[8].target = (motor_angle_task[4], 'P')
        robot.motors[9].target = (motor_angle_task[5], 'P')
        print(motor_angle_task)
        turnPosition=target_position_2
        turnAngles=motor_angle_task
        #robot.IMUBalance(0, 0)
        robot.moveAllToTarget()

# attempt to orientate
target_position_2=turnPosition
ik_solution = left_arm_chain.inverse_kinematics(target_position_2, target_orientation=target_orientation_z, orientation_mode="Z", initial_position=ik_solution_2 )
leftArmTraj = [
    [[0,0,0,0,0], [20,20,20,20,20]],
    [[motor_angle_task[1],motor_angle_task[2],motor_angle_task[3],motor_angle_task[4],motor_angle_task[5] ],
   [ik_solution[1], ik_solution[2], ik_solution[3],ik_solution[4],ik_solution[5]]] ,
    [[0,0,0,0,0], [0,0,0,0,0]],
    [[0,0,0,0,0], [0,0,0,0,0]]
]
lArm_tj_joint = TrajPlannerTime(leftArmTraj[0], leftArmTraj[1], leftArmTraj[2], leftArmTraj[3])
startTime = time.time()
while time.time() - startTime < 10:
        target_position_joint = lArm_tj_joint.getQuinticPositions(time.time() - startTime)
        # robot.motors[5].target = (target_position_joint[0], 'P')
        # robot.motors[6].target = (target_position_joint[1], 'P')
        # robot.motors[7].target = (target_position_joint[2], 'P')
        # robot.motors[8].target = (target_position_joint[3], 'P')
        # robot.motors[9].target = (target_position_joint[4], 'P')
        
       # robot.IMUBalance(0, 0)
        # robot.moveAllToTarget()   
        
startTime = time.time()
# close gripper
while time.time() - startTime < 8:
        lastAngle=lastAngle-.1
        # robot.motors[27].target = (math.radians(lastAngle), 'P')
        # #robot.IMUBalance(0, 0)
        # robot.moveAllToTarget()