import numpy as np
import matplotlib.pyplot as plt
from ikpy.chain import Chain
from ikpy.utils import plot as plot_utils
import sys, time, math, array
import numpy as np
sys.path.append("./")
from backend.KoalbyHumanoid.Robot import Robot


# Edit to declare if you are testing the sim or the real robot
is_real = True
robot = Robot(is_real)
print("Setup Complete")
robot.motors[27].target = (math.radians(60), 'P')
print("targeted")
prevTime = time.time()
simStartTime = time.time()
while time.time() - simStartTime < 2:
    time.sleep(0.01)
    #robot.IMUBalance(0,0)
    robot.moveAllToTarget()

print("closed")