import sys, time, math 
sys.path.append("./")
from backend.KoalbyHumanoid.Robot import Robot
from backend.KoalbyHumanoid import trajPlannerPose
from backend.KoalbyHumanoid.Config import Joints
import matplotlib.pyplot as plt
from backend.KoalbyHumanoid.Plotter import Plotter

# Edit to declare if you are testing the sim or the real robot
is_real = True

robot = Robot(is_real)

print("Setup Complete")

# from backend.KoalbyHumanoid import poe
# x = 0
# y = 0
# z = 0
# T = [[1, 0, 0, x], [0, 1, 0, y], [0, 0, 1, z], [0, 0, 0, 1]]

# setPoints = [[0,  0], [math.radians(90), math.radians(-90)], [math.radians(0), math.radians(0)]]
# setPoints = [[0,  0], [math.radians(80), math.radians(-80)], [math.radians(0), math.radians(0)]]
# tj = trajPlannerPose.TrajPlannerNew(setPoints)
# traj = tj.getCubicTraj(30, 100)
# plotter = Plotter(10, True)

robot.motors[1].target = (math.radians(-80), 'P') # right abductor
robot.motors[6].target = (math.radians(80), 'P') # left abductor
# robot.motors[13].target = (0.1, 'P')
# robot.motors[3].target = math.radians(90)
# robot.motors[8].target = math.radians(90)
# robot.motors[14].target = (0, 'P')
# robot.motors[17].target = math.radians(90)
# robot.motors[22].target = math.radians(90)

robot.motors[17].target = (math.radians(15), 'P') # right kick
robot.motors[18].target = (math.radians(-22), 'P') # Right knee
robot.motors[19].target = (math.radians(0), 'P') # right ankle

robot.motors[20].target = (math.radians(5), 'P')
robot.motors[22].target = (math.radians(-15), 'P') # left kick
robot.motors[23].target = (math.radians(-20), 'P') # left knee
robot.motors[24].target = (math.radians(0), 'P') # left ankle

#robot.motors[1].target = (math.radians(75), 'P') # right arm abductor
#robot.motors[2].target = (math.radians(-45), 'P')

robot.motors[10].target = (math.radians(20), 'P')
# angles = poe.calcLegChainIK(robot, T, True)[0]
# print(angles)

#robot.motors[17].target = math.radians(-45)
#robot.motors[22].target = math.radians(45)
prevTime = time.time()
#robot.motors[0].target = -math.radians(90)

##Robot Motor Positions to hold the cart
# robot.motors[0].target = (30, 'P')
# robot.motors[3].target = (60, 'P')
# motorsIndex = [19, 18, 17, 16, 15, 20, 21, 22, 23, 24]

# for i in range(len(angles)):
#     robot.motors[motorsIndex[i]].target = (angles[i], 'P')

robot.moveAllToTarget()

time.sleep(1)

exit()
simStartTime = time.time()
print("Starting Loop")
while time.time() - simStartTime < 300:
    robot.IMUBalance(0,0)
    # robot.moveAllToTarget()
    #robot.moveToTarget(robot.motors[10])
    #time.sleep(0.01)
    #robot.moveToTarget(robot.motors[13])

exit()
while True:
    # errorData = []
    # timeData = []
    # startTime = time.time()
    robot.IMUBalance(0,0)
    robot.moveAllToTarget()
   
    
    continue

    for point in traj:
        time.sleep(0.01)
        # print(robot.locatePolygon())
        robot.updateRobotCoM()
        # plotting stuff
        plotter.addPoint(robot.CoM)
        # robot.balanceAngle()
        # plotting stuff
        # errorData.append(robot.balanceAngle())
        # timeData.append(time.time() - simStartTime)
        #print(robot.motors[0].prevError, robot.motors[0].effort)
        robot.moveAllToTarget()
        #print(robot.CoM)

        # print(point)
        robot.motors[0].target = (point[1], 'P')
        # robot.motors[3].target += math.radians(2)
        robot.motors[5].target = (point[2], 'P')
        # robot.motors[8].target += math.radians(2)
        #print(math.degrees(robot.motors[0].target))
        while time.time() - startTime < point[0]:
            time.sleep(0.01)
            robot.updateRobotCoM() 
            # plotting stuff
            plotter.addPoint(robot.CoM)
            # robot.balanceAngle()
            # plotting stuff
            # errorData.append(robot.balanceAngle())
            # timeData.append(time.time() - simStartTime)
            #print(robot.motors[0].prevError, robot.motors[0].effort)
            robot.moveAllToTarget()
            #print(robot.locate(robot.motors[22]))
            #print(robot.CoM)
print("done")

plt.plot(timeData,errorData)
plt.show()
exit(0)



startTime = time.time()
for point in traj:
    motorsTarget = point[1]
    #print(motorsTarget)
    tarTime = point[0]
    curTime = time.time()
    while curTime - startTime <= tarTime:
        robot.motors[Joints.Right_Shoulder_Rotator_Joint.value].move(motorsTarget)
        curTime = time.time()
        # print(curTime - startTime)

exit(0)

xData = list()
yData = list()
startTime = time.time()
while time.time() - startTime < 5:
    # robot.motors[Joints.Right_Thigh_Kick_Joint.value].45move(90)
    # robot.motors[Joints.Right_Knee_Joint.value].move(-90)
    # robot.motors[Joints.Right_Ankle_Joint.value].move(0)
    motorsTarget = 0
    robot.moveAllTo(motorsTarget)
    xData.append(time.time() - startTime)
    yData.append(motorsTarget - robot.motors[Joints.Lower_Torso_Side2Side_Joint.value].get_position())
    #print(robot.motors[Joints.Right_Knee_Joint.value].get_position())

plt.plot(xData, yData)
#plt.plot(xData, yData*0)
plt.title("Lower Torso - P: 10, I: 0, D: 50")
plt.xlabel("Time (seconds)")
plt.ylabel("Position Error (radians)")
plt.grid()
plt.show()


"""
Old Code, using for potential reference. Delete when robust traj planner is created

res = vrep.simx_return_novalue_flag
while res != vrep.simx_return_ok:
    res, data = vrep.simxGetObjectPosition(client_id, robot.motors[15].handle, robot.motors[8].handle, vrep.simx_opmode_streaming)

#home: 0  -10  10
moveRightLeg(robot, client_id, -90, -90, -90, 4)"""
