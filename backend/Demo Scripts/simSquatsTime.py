import sys, time, math 
sys.path.append("./")
from backend.KoalbyHumanoid.Robot import Robot
from backend.KoalbyHumanoid import trajPlannerTime

is_real = False

robot = Robot(is_real)

print("Setup Complete")

squatTime = 2.5
squatAngle = 45
setPointsTimes = [[0, 0, 0, 0],[squatTime, squatTime, squatTime, squatTime], [squatTime*2, squatTime*2, squatTime*2, squatTime*2]]
setPointsAngles = [[0, 0, 0, 0], [math.radians(squatAngle), math.radians(-2*squatAngle), math.radians(-squatAngle), math.radians(squatAngle)], [0, 0, 0, 0]]
setPointsVels = [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
setPointsAccels = [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
tjTime = trajPlannerTime.TrajPlannerTime(setPointsTimes, setPointsAngles, setPointsVels, setPointsAccels)

robot.motors[1].target = (math.radians(80), 'P')
robot.motors[6].target = (math.radians(-80), 'P')

simStartTime = time.time()
while time.time() - simStartTime < 5:
    robot.IMUBalance(0,0)
    robot.moveAllToTarget()
while True:
    startTime = time.time()
    while time.time() - startTime < squatTime*2:
        robot.IMUBalance(0,0)
        point = tjTime.getQuinticPositions(time.time() - startTime)
        robot.motors[17].target = (point[0], 'P')
        robot.motors[18].target = (point[1], 'P')
        robot.motors[19].target = (point[2], 'P')
        robot.motors[0].target = (point[3], 'P')

        robot.motors[22].target = (-point[0], 'P')
        robot.motors[23].target = (-point[1], 'P')
        robot.motors[24].target = (-point[2], 'P')
        robot.motors[5].target = (-point[3], 'P')

        robot.moveAllToTarget()
        # print(time.time() - loopTime)

