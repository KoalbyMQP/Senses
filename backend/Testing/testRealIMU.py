import sys
sys.path.append(".")
import time
import math
from backend.KoalbyHumanoid.IMU import IMU

print("Initializing...")

imu = IMU(True)

print("pitch yaw roll accelX accelY accelZ")
while True:
    data = imu.getData() # use imu.getDataRaw() for raw imu readings that are not relative to the imu's initial orientation
    angleData = data[:3]
    accelData = data[3:] 
    
    # print("{:0.2f} {:0.2f} {:0.2f} {:0.2f} {:0.2f} {:0.2f}".format(*[math.degrees(x) for x in angleData], *accelData))
    # time.sleep(0.01)
    
    # To have print update the same line in the console:
    print("{:0.2f} {:0.2f} {:0.2f} {:0.2f} {:0.2f} {:0.2f}".format(*[math.degrees(x) for x in angleData], *accelData), end="")
    print("                         \r", end="")