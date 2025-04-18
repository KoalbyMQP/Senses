import numpy as np
import matplotlib.pyplot as plt
from ikpy.chain import Chain
from ikpy.utils import plot as plot_utils
import sys, time, math, array
import numpy as np
sys.path.append("./")
from backend.KoalbyHumanoid.Robot import Robot
from backend.KoalbyHumanoid.trajPlannerTime import TrajPlannerTime
from backend.Testing import finlyViaPoints as via
is_real = False
robot = Robot(is_real)
print("Setup Complete")
robot.motors[25].target = (math.radians(0), 'P')
robot.motors[26].target = (math.radians(0), 'P')
robot.motors[27].target = (math.radians(0), 'P')
robot.motors[5].target = (math.radians(0), 'P')
robot.motors[6].target = (math.radians(0), 'P')
robot.motors[7].target = (math.radians(0), 'P')
robot.motors[8].target = (math.radians(0), 'P')
robot.motors[9].target = (math.radians(0), 'P')
robot.motors[10].target =(math.radians(0), 'P')
# centering all angles to zero
simStartTime = time.time()
while time.time() - simStartTime < 2:
    time.sleep(0.01)
    #robot.IMUBalance(0,0)
    robot.moveAllToTarget()
leftArmTraj = [
    [[0,0,0,0,0],[5,5,5,5,5],[10,10,10,10,10],[15,15,15,15,15]],
    [
    [0,0,0,0,0],
    [0,90,0,0,0],
    [90,0,0,0,0],
    [-117,-103,0,-53,45]
    ] ,
    [[0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0]],
    [[0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0]]
]
lArm_tj_joint = TrajPlannerTime(leftArmTraj[0], leftArmTraj[1], leftArmTraj[2], leftArmTraj[3])
startTime = time.time()
while time.time() - startTime < 20:
    target_position_joint = lArm_tj_joint.getQuinticPositions(time.time() - startTime)
    robot.motors[5].target = (target_position_joint[0], 'P')
    robot.motors[6].target = (target_position_joint[1], 'P')
    robot.motors[7].target = (target_position_joint[2], 'P')
    robot.motors[8].target = (target_position_joint[3], 'P')
    robot.motors[9].target = (target_position_joint[4], 'P')
    #robot.IMUBalance(0,0)
    robot.moveAllToTarget()
