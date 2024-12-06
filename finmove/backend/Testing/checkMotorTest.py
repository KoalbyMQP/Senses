
import sys
sys.path.append("./")
import math
from backend.KoalbyHumanoid.Robot import Robot
from backend.KoalbyHumanoid.Config import Joints

robot = Robot(True)

while True:
    robot.checkMotors()

# robot.motors[19].target = (math.radians(2), 'P')
# robot.moveAllToTarget()