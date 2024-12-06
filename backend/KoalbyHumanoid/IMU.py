
import adafruit_bno055
import numpy as np
import math
from coppeliasim_zmqremoteapi_client import RemoteAPIClient

try:
    import board
except NotImplementedError:
    print("Failed to import board when not running on Raspberry Pi")

class IMU():
    def __init__(self, isReal, sim=None):
        self.isReal = isReal
        self.isConnected = True
        self.sim = sim
        
        if isReal:
            try:
                i2c = board.I2C()  # uses board.SCL and board.SDA
                self.sensor = adafruit_bno055.BNO055_I2C(i2c)
            except:
                print("No IMU detected, disabling IMU")
                self.isConnected = False

            # self.zero() # angles/accelerations that correspond to home position
    
    def zero(self):
        if self.isReal:
            self.zeroAngles = self.getDataRaw()
        else:
            raise NotImplementedError("IMU zero not implemented for simulation IMU")

    def getData(self):
        return self.getDataRaw()

    # x axis is toward Ava's Left, y axis is up, z axis is toward Ava's front, all from the center of Ava
    # getData returns [x angle (rad), y angle (rad), z angle (rad), x acceleration (m/s^2), y acceleration (m/s^2), z acceleration (m/s^2)]
    def getDataRaw(self): 
        if not self.isConnected:
            return [0, 0, 0, 0, 0, 0]
        if self.isReal:
            # in terms of right hand rule convention for positive directions:
            # sensor.euler returns: (yaw (opposite convention), roll (normal convention), pitch (opposite convention))
            # yaw is in range 0 to 360, roll is -90 to 90 (rolling the IMU 180 degrees results in the same roll reading), pitch is -180 to 180
            # sensor.acceleration returns: (x acceleration (normal convention), z acceleration (opposite convention), y acceleration (normal convention))
            yaw, roll, pitch = self.sensor.euler
            
            self.data = [ 
                math.radians(-pitch),
                math.radians(-(yaw if yaw <= 180 else yaw - 360)), # mapping from 0 to 360 to -180 to 180
                math.radians(roll),
                self.sensor.acceleration[0],
                -self.sensor.acceleration[2],
                self.sensor.acceleration[1]
                ]
        else:
            self.data = [self.sim.getFloatSignal("gyroX"),
            self.sim.getFloatSignal("gyroY"),
            self.sim.getFloatSignal("gyroZ"),
            self.sim.getFloatSignal("accelX"),
            self.sim.getFloatSignal("accelY"),
            self.sim.getFloatSignal("accelZ")]
            self.data = [0 if dataPoint==None else dataPoint for dataPoint in self.data]
        return self.data