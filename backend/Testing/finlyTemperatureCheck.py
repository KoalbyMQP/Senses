import os
import numpy as np
import matplotlib.pyplot as plt
from ikpy.chain import Chain
from ikpy.utils import plot as plot_utils
import sys, time, math, array
import zmq
import subprocess

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
is_real = False
robot = Robot(is_real)
print("Setup Complete")
# positions
#Starting Agnles
robot.motors[25].target = (math.radians(0), 'P')
robot.motors[26].target = (math.radians(0), 'P')
robot.motors[27].target = (math.radians(0), 'P')
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
    
# Attempt to receive coordinates from thermometer demo via ZMQ
print("Attempting to receive coordinates from thermometer demo...")
context_zmq = zmq.Context()
coord_sub = context_zmq.socket(zmq.SUB)
coord_sub.setsockopt_string(zmq.SUBSCRIBE, "")
coord_sub.connect("tcp://localhost:5560")  # Connect to the port where demo.py is sending coordinates
poller = zmq.Poller()
poller.register(coord_sub, zmq.POLLIN)
print("Waiting for coordinates (timeout in 10 seconds)...")
socks = dict(poller.poll(10000))  # wait 10 seconds for a message

if coord_sub in socks and socks[coord_sub] == zmq.POLLIN:
    coord_str = coord_sub.recv_string(zmq.NOBLOCK)
    try:
        coord_vals = [float(val) for val in coord_str.split(",")]
        if len(coord_vals) < 3:
            raise ValueError("Not enough coordinate values received!")
        final_points = np.array(coord_vals[:3])
        print("Received coordinates from thermometer demo:", final_points)
    except Exception as e:
        print("Error parsing coordinates from thermometer demo, using default coordinates. Error:", e)
        final_points = np.array([0, 0, -0.3])
else:
    print("Warning: No coordinates received from thermometer demo, using default coordinates.")
    final_points = np.array([0, 0, -0.3])

# Apply camera frame transformation to final_points
B = np.array([[final_points[0]], [final_points[1]], [final_points[2]], [1]])
C = np.dot(camera_frame_transformation, B)

leftArmTraj = [
    [[0,0,0], [20,20,20]],
    [[.50575,  -.006620, .28607],
   [C[0],  C[1], C[2]] ],
    [[0,0,0], [0,0,0]],
    [[0,0,0], [0,0,0]]
]

lArm_tj_joint = TrajPlannerTime(leftArmTraj[0], leftArmTraj[1], leftArmTraj[2], leftArmTraj[3])
startTime = time.time()
target_orientation_z=[1, 0, 0]

print("Moving arm to temperature check position...")

# Move arm to target position
while time.time() - startTime < 20:
        target_position_task = lArm_tj_joint.getQuinticPositions(time.time() - startTime)
        target_position_2 = np.array([(target_position_task[0]), (target_position_task[1]), (target_position_task[2])])
        ik_solution = left_arm_chain.inverse_kinematics(target_position_2, initial_position=ik_solution_2)
        ik_solution_2=ik_solution
        motor_angle_task=ik_solution
        robot.motors[5].target = (motor_angle_task[1], 'P')
        robot.motors[6].target = (motor_angle_task[2], 'P')
        robot.motors[7].target = (motor_angle_task[3], 'P')
        robot.motors[8].target = (motor_angle_task[4], 'P')
        robot.motors[9].target = (motor_angle_task[5], 'P')
        turnPosition=target_position_2
        turnAngles=motor_angle_task
        #robot.IMUBalance(0, 0)
        robot.moveAllToTarget()

# Orient the arm for temperature checking
target_position_2=turnPosition
ik_solution = left_arm_chain.inverse_kinematics(target_position_2, target_orientation=target_orientation_z, orientation_mode="Z", initial_position=ik_solution_2)
leftArmTraj = [
    [[0,0,0,0,0], [20,20,20,20,20]],
    [[motor_angle_task[1],motor_angle_task[2],motor_angle_task[3],motor_angle_task[4],motor_angle_task[5]],
   [ik_solution[1], ik_solution[2], ik_solution[3],ik_solution[4],ik_solution[5]]],
    [[0,0,0,0,0], [0,0,0,0,0]],
    [[0,0,0,0,0], [0,0,0,0,0]]
]
lArm_tj_joint = TrajPlannerTime(leftArmTraj[0], leftArmTraj[1], leftArmTraj[2], leftArmTraj[3])
startTime = time.time()
while time.time() - startTime < 10:
        target_position_joint = lArm_tj_joint.getQuinticPositions(time.time() - startTime)
        robot.motors[5].target = (target_position_joint[0], 'P')
        robot.motors[6].target = (target_position_joint[1], 'P')
        robot.motors[7].target = (target_position_joint[2], 'P')
        robot.motors[8].target = (target_position_joint[3], 'P')
        robot.motors[9].target = (target_position_joint[4], 'P')
       # robot.IMUBalance(0, 0)
        robot.moveAllToTarget()

# Print message that target has been reached
print("==============================================")
print("TARGET DESTINATION REACHED!")
print(f"Position at: X={C[0][0]:.4f}, Y={C[1][0]:.4f}, Z={C[2][0]:.4f}")
print("==============================================")
print("Temperature check can be performed now.")
print("==============================================")

# Run temperature script as a subprocess outside of virtual environment
print("Running temperature measurement script...")
temp_script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../Gripper/thermometer/getTemp_MLX90614.py")
temp_script_path = os.path.normpath(temp_script_path)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
print(f"Temperature script path: {temp_script_path}")

# Create a temporary shell script
temp_shell_script = "/tmp/temperature_measure.sh"
with open(temp_shell_script, "w") as f:
    f.write(f"""#!/bin/bash
echo "Starting temperature measurement..."
export PYTHONPATH="{project_root}:$PYTHONPATH"
cd {os.path.dirname(temp_script_path)}
python3 {os.path.basename(temp_script_path)} 
""")
os.chmod(temp_shell_script, 0o755)

try:
    # Run the shell script and capture its output
    result = subprocess.run([temp_shell_script], capture_output=True, text=True, check=True)
    print(f"Temperature script output: {result.stdout}")
    # Launch in a new terminal window
    temp_process = subprocess.Popen(
        f"lxterminal --geometry=80x24 -e 'bash -c \"{temp_shell_script}; exec bash\"'",
        shell=True,
        preexec_fn=os.setsid
    )

    # Save temperature to file
    with open("Gripper/thermometer/temperature.txt", "w") as temp_file:
        temp_file.write(result.stdout)
    print("Waiting for temperature measurement to complete...")
    time.sleep(5)

    print("Temperature data saved to temperature.txt")
except subprocess.CalledProcessError as e:
    # Check if output file exists and read it
    if os.path.exists("/tmp/temperature_output.txt"):
        with open("/tmp/temperature_output.txt", "r") as output_file:
            temperature_output = output_file.read()
            print(f"Temperature script output: {temperature_output}")
        
        # Save temperature to file
        with open("Gripper/thermometer/temperature.txt", "w") as temp_file:
            temp_file.write(temperature_output)
        
        print("Temperature data saved to temperature.txt")
    else:
        print("Temperature output file not found")
        
    # Check exit code
    if os.path.exists("/tmp/temperature_exit_code.txt"):
        with open("/tmp/temperature_exit_code.txt", "r") as code_file:
            exit_code = code_file.read().strip()
            print(f"Temperature script exit code: {exit_code}")
            
except Exception as e:
    print(f"Error running temperature script: {e}")
    print(f"Error output: {e.stderr}")

print("Temperature check movement complete.") 

# Hold position for 30 seconds
startTime = time.time()
print(f"Holding position for 30 seconds...")
while time.time() - startTime < 30:
    time.sleep(0.01)
    robot.moveAllToTarget()
    # Display remaining time every 5 seconds
    elapsed = time.time() - startTime
    if int(elapsed) % 5 == 0 and int(elapsed) > 0 and elapsed - int(elapsed) < 0.02:
        print(f"Remaining hold time: {30 - int(elapsed)} seconds")

print("Temperature check complete. Returning to home position.")



# Clean up ZMQ resources
coord_sub.close()
context_zmq.term()