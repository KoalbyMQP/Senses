import sys
sys.path.append(".")

from backend.KoalbyHumanoid.Robot import Robot
import time

# Initialize real robot and send to home position
robot = Robot(True)
motor = robot.getMotor(5) # Right ankle

# Get position (should be around 0.0)
print(motor.get_position())

# Set position
motor.set_position(20)
time.sleep(1.5)
print(motor.get_position())

# Turn torque off
robot.shutdown()
time.sleep(10)
while True:
    print(motor.get_position())