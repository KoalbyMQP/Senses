import sys, time, math

import numpy as np 
sys.path.append("./")
from backend.KoalbyHumanoid.Robot import Robot
from backend.KoalbyHumanoid import trajPlannerPose
from backend.KoalbyHumanoid.Config import Joints
import matplotlib.pyplot as plt
from backend.KoalbyHumanoid.Plotter import Plotter

# Edit to declare if you are testing the sim or the real robot
setPoints = [[0,  0], [math.radians(80), math.radians(-80)], [math.radians(0), math.radians(0)]]
tj = trajPlannerPose.TrajPlannerPose(setPoints)
traj = tj.getCubicTraj(10, 100)

is_real = False

robot = Robot(is_real)

print("Setup Complete")

robot.motors[1].target = (math.radians(80), 'P')
robot.motors[6].target = (math.radians(-80), 'P')
robot.moveAllToTarget()

prevTime = time.time()

simStartTime = time.time()

while time.time() - simStartTime < 10:
    loopStartTime = time.time()
    time.sleep(0.01)
    robot.updateRobotCoM()
    robot.updateBalancePoint()
    # robot.IMUBalance(0,0)
    # print(robot.VelBalance(robot.leftFootBalancePoint))
    print("Error: ", robot.leftFootBalancePoint - robot.CoM)
    print("BP: ", robot.balancePoint)
    robot.moveAllToTarget()

while True:
    startTime = time.time()
    for point in traj:
        time.sleep(0.01)
        robot.updateRobotCoM()
        robot.updateBalancePoint()
        # robot.IMUBalance(0,0)  
        # robot.VelBalance(robot.leftFootBalancePoint)
        robot.moveAllToTarget()
        robot.motors[0].target = (point[1], 'P')
        robot.motors[5].target = (point[2], 'P')
        print("Error: ", robot.leftFootBalancePoint - robot.CoM)
        while time.time() - startTime < point[0]:
            time.sleep(0.01)
            robot.updateRobotCoM() 
            robot.updateBalancePoint()
            # robot.IMUBalance(0,0)
            # robot.VelBalance(robot.leftFootBalancePoint)
            robot.moveAllToTarget()
            print("Error: ", robot.leftFootBalancePoint - robot.CoM)
