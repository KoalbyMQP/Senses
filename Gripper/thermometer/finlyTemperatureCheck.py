import os
import numpy as np
import matplotlib.pyplot as plt
from ikpy.chain import Chain
from ikpy.utils import plot as plot_utils
import sys, time, math, array
import zmq
import subprocess
import logging
from datetime import datetime

sys.path.append("./")

from backend.KoalbyHumanoid.Robot import Robot
from backend.KoalbyHumanoid.trajPlannerTime import TrajPlannerTime
from backend.Testing import finlyViaPoints as via

log_filename = f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
log_filepath = os.path.join(os.path.dirname(__file__), log_filename)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO) 

fh = logging.FileHandler(log_filepath)
fh.setLevel(logging.INFO)


ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)

logger.addHandler(fh)
logger.addHandler(ch)

def find_file(filename, search_path="/home/finley"):
    logger.info(f"Searching for file '{filename}' in '{search_path}'")
    result = []
    for root, dirs, files in os.walk(search_path):
        if filename in files:
            result.append(os.path.join(root, filename))
    if not result:
        logger.error(f"URDF file '{filename}' not found in search path '{search_path}'!")
        sys.exit(1) 
    return result

# Find all instances of your URDF file
found_paths = find_file("FullAssemFIN_straight_2025_5.urdf")
logger.info(f"Found URDF files at: {found_paths}")
urdf_path = found_paths[0]
logger.info(f"Using URDF: {urdf_path}")

# Creating URDF chain for left arm
logger.info("Creating left arm kinematic chain from URDF...")
left_arm_chain = Chain.from_urdf_file(
    urdf_path,
    base_elements=['shoulder1_left', 'shoulder1_left'] 
)
logger.info(f"Left arm chain links (as defined): {[link.name for link in left_arm_chain.links]}")

# creating URDF chain for camera
logger.info("Creating camera kinematic chain from URDF...")
camera = Chain.from_urdf_file(
    urdf_path,
    base_elements=['neck', 'neck'] 
)
logger.info(f"Camera chain links (as defined): {[link.name for link in camera.links]}")

#forward kinematics for camera chain
camera_angles=np.array([0,0,0,0])
logger.info(f"Calculating camera forward kinematics with angles: {camera_angles}")
camera_frame_transformation=camera.forward_kinematics(camera_angles)
logger.info(f"Camera transformation matrix:\n{camera_frame_transformation}")

# Edit to declare if you are testing the sim or the real robot
is_real = True
logger.info(f"Initializing Robot (is_real={is_real})...")
robot = Robot(is_real)
logger.info("Robot Setup Complete")

# positions
#Starting Agnles
logger.info("Setting initial target motor angles to zero...")
# robot.motors[25].target = (math.radians(0), 'P')
# robot.motors[26].target = (math.radians(0), 'P')
# robot.motors[27].target = (math.radians(0), 'P')
robot.motors[5].target = (math.radians(0), 'P')
robot.motors[6].target = (math.radians(0), 'P')
robot.motors[7].target = (math.radians(0), 'P')
robot.motors[8].target = (math.radians(0), 'P')
robot.motors[9].target = (math.radians(0), 'P')
robot.motors[10].target =(math.radians(0), 'P')
ik_solution_2=np.array([0,0,0,0,0,0,0,0])
logger.info(f"Initial IK guess (ik_solution_2) set to: {ik_solution_2}")

# centering all angles to zero
logger.info("Moving robot to initial zero position...")
prevTime = time.time()
simStartTime = time.time()
while time.time() - simStartTime < 2:
    time.sleep(0.01)
    #robot.IMUBalance(0,0)
    robot.moveAllToTarget()
logger.info("Robot centered.")
    
# Attempt to receive coordinates from demo
logger.info("Setting up ZMQ subscriber for coordinates...")
context_zmq = zmq.Context()
coord_sub = context_zmq.socket(zmq.SUB)
coord_sub.setsockopt_string(zmq.SUBSCRIBE, "")
coord_sub.connect("tcp://localhost:5560")

# Loop until we get the coordinates from ZMQ
logger.info("Waiting for coordinates from ZMQ on tcp://localhost:5560...")
final_points = None
while True:
    poller = zmq.Poller()
    poller.register(coord_sub, zmq.POLLIN)                      
    socks = dict(poller.poll(1000))  # wait 1000 ms for a message
    if coord_sub in socks and socks[coord_sub] == zmq.POLLIN:
        coord_str = coord_sub.recv_string(zmq.NOBLOCK)
        logger.info(f"Received string from ZMQ: '{coord_str}'")
        try:
            coord_vals = [float(val) for val in coord_str.split(",")]
            if len(coord_vals) < 3:
                logger.warning(f"Not enough coordinate values received ({len(coord_vals)}), waiting for valid coordinates...")
                continue
            final_points = np.array(coord_vals[:3]) 
            logger.info(f"Received coordinates from speech demo (camera frame): {final_points}")
            break
        except Exception as e:
            logger.error(f"Error parsing coordinates '{coord_str}' from speech demo: {e}")
            logger.warning("Waiting for valid coordinates...")
    else:
        logger.debug("No coordinates received yet, continuing to wait...") 

# Apply camera frame transformation to final_points
# NEGATIVE X AND NEGATIVE Z FOR CURRENT URDF 
logger.info(f"Transforming camera coordinates {final_points} to robot base frame...")
B = np.array([[final_points[0]], [-final_points[1]], [-final_points[2]], [1]]) 
C = np.dot(camera_frame_transformation, B)
target_x_traj = C[0][0] 
target_y_traj = C[1][0]
target_z_traj = C[2][0]
logger.info(f"Final target coordinates (robot base frame) calculated in C: X={target_x_traj:.5f}, Y={target_y_traj:.5f}, Z={target_z_traj:.5f}")

logger.info("Setting up original trajectory definition...")
leftArmTraj = [
    [[0,0,0], [20,20,20]], 
    [[.50575,  -.006620, .28607],
     [target_x_traj,  target_y_traj, target_z_traj] ], 
    [[0,0,0], [0,0,0]],
    [[0,0,0], [0,0,0]]  
]
logger.info(f"Trajectory Start Pos: {leftArmTraj[1][0]}")
logger.info(f"Trajectory End Pos: {leftArmTraj[1][1]}")

lArm_tj_joint = TrajPlannerTime(leftArmTraj[0], leftArmTraj[1], leftArmTraj[2], leftArmTraj[3])
startTime = time.time() 
target_orientation_z=[1, 0, 0]
Angle =0
lastAngle=0

# open gripper
logger.info("Starting 'open gripper' phase...")
start_time_gripper_open = time.time()
while time.time() - start_time_gripper_open < 4:
        Angle=Angle+.1
        # robot.motors[27].target = (math.radians(Angle), 'P')
        # logger.debug(f"Gripper Open Angle Target (rad): {math.radians(Angle)}")
        #robot.IMUBalance(0, 0)
        # robot.moveAllToTarget()
        time.sleep(0.01) 
        lastAngle=Angle
logger.info(f"'Open gripper' phase complete. Last angle: {lastAngle}")

# move gripper 
logger.info("Starting main movement loop (using original trajectory)...")
start_time_move = time.time()
movement_duration = 20 
while time.time() - start_time_move < movement_duration:
        elapsed_time = time.time() - start_time_move
        target_position_task = lArm_tj_joint.getQuinticPositions(elapsed_time)
        target_position_2 = np.array([(target_position_task[0]), (target_position_task[1]), (target_position_task[2])])
        logger.debug(f"Move Time: {elapsed_time:.2f}s, Target Task Space Pos: {target_position_2}")
        
        try:
            ik_solution = left_arm_chain.inverse_kinematics(target_position_2, initial_position=ik_solution_2 )
            logger.debug(f"IK Solution (rad): {ik_solution}")
            ik_solution_2=ik_solution 
            motor_angle_task=ik_solution 
            
            motor_targets = {
                5: motor_angle_task[1],
                6: motor_angle_task[2],
                7: motor_angle_task[3],
                8: motor_angle_task[4],
                9: motor_angle_task[5]
            }
            robot.motors[5].target = (motor_angle_task[1], 'P')
            robot.motors[6].target = (motor_angle_task[2], 'P')
            robot.motors[7].target = (motor_angle_task[3], 'P')
            robot.motors[8].target = (motor_angle_task[4], 'P')
            robot.motors[9].target = (motor_angle_task[5], 'P')
            logger.debug(f"Sending motor targets (rad): {motor_targets}")
            # logger.info(f"Raw IK solution being used for motor targets: {motor_angle_task}") # Added for extra info
            
            turnPosition=target_position_2 
            turnAngles=motor_angle_task    
            
            #robot.IMUBalance(0, 0)
            robot.moveAllToTarget()
        except ValueError as e:
            logger.error(f"IK failed for position {target_position_2}: {e}")
            time.sleep(0.01)
            continue 
            
        time.sleep(0.01) 

logger.info(f"Main movement complete after {time.time() - start_time_move:.2f} seconds.")
logger.info(f"Final position reached (intended): {turnPosition}")
logger.info(f"Final joint angles from IK (intended, degrees): {np.degrees(turnAngles)}")


logger.info("Starting orientation phase...")
target_position_2=turnPosition 

try:

    ik_solution = left_arm_chain.inverse_kinematics(
        target_position_2, 
        target_orientation=target_orientation_z, 
        orientation_mode="Z", 
        initial_position=ik_solution_2 
    )
    logger.info(f"IK solution for orientation found (rad): {ik_solution}")
    logger.info(f"IK solution for orientation found (deg): {np.degrees(ik_solution)}")

    leftArmTraj = [
        [[0,0,0,0,0], [20,20,20,20,20]],
        [[motor_angle_task[1],motor_angle_task[2],motor_angle_task[3],motor_angle_task[4],motor_angle_task[5] ],
         [ik_solution[1], ik_solution[2], ik_solution[3],ik_solution[4],ik_solution[5]]] ,
        [[0,0,0,0,0], [0,0,0,0,0]],
        [[0,0,0,0,0], [0,0,0,0,0]]
    ]
    logger.info(f"Orientation Traj Start Angles (deg): {np.degrees(leftArmTraj[1][0])}")
    logger.info(f"Orientation Traj End Angles (deg): {np.degrees(leftArmTraj[1][1])}")

    lArm_tj_joint = TrajPlannerTime(leftArmTraj[0], leftArmTraj[1], leftArmTraj[2], leftArmTraj[3])
    startTime = time.time() 
    orient_duration = 10 
    logger.info(f"Starting orientation movement loop ({orient_duration}s)... Note: Motor commands are commented out.")
    
    # while time.time() - startTime < orient_duration:
    #     target_position_joint = lArm_tj_joint.getQuinticPositions(time.time() - startTime)
    #     logger.debug(f"Orient Time: {(time.time() - startTime):.2f}s, Target Joint Angles (deg): {np.degrees(target_position_joint)}")
    #     # Original motor mapping commented out
    #     # robot.motors[5].target = (target_position_joint[0], 'P')
    #     # robot.motors[6].target = (target_position_joint[1], 'P')
    #     # robot.motors[7].target = (target_position_joint[2], 'P')
    #     # robot.motors[8].target = (target_position_joint[3], 'P')
    #     # robot.motors[9].target = (target_position_joint[4], 'P')
    #     # robot.IMUBalance(0, 0)
    #     # robot.moveAllToTarget()
    #     time.sleep(0.01) 
    # logger.info("Orientation movement loop finished (if uncommented).")

    logger.warning("Orientation movement code is currently commented out. Skipping execution.")

except ValueError as e:
    logger.error(f"IK failed during orientation phase for position {target_position_2}: {e}")
except Exception as e:
    logger.error(f"An unexpected error occurred during orientation phase: {e}")

startTime = time.time() 

# close gripper 
logger.info("Starting 'close gripper' phase...")
start_time_gripper_close = time.time()
while time.time() - start_time_gripper_close < 8:
        lastAngle=lastAngle-.1
        # robot.motors[27].target = (math.radians(lastAngle), 'P')
        # logger.debug(f"Gripper Close Angle Target (rad): {math.radians(lastAngle)}")
        #robot.IMUBalance(0, 0)
        # robot.moveAllToTarget()
        time.sleep(0.01) 
logger.info(f"'Close gripper' phase complete. Last angle: {lastAngle}")

logger.info("Movement sequence potentially finished.")
logger.info("Reached forehead position. Holding for temperature measurement...")
# Hold at forehead position for 3 seconds
time.sleep(3)

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
    # Launch in a new terminal window
    temp_process = subprocess.Popen(
        f"lxterminal --geometry=80x24 -e 'bash -c \"{temp_shell_script}; exec bash\"'",
        shell=True,
        preexec_fn=os.setsid
    )

    # Give it some time to run
    print("Waiting for temperature measurement to complete...")
    time.sleep(5)

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

logger.info("Temperature check sequence complete.")

def send_speech_control_command(command):
    logger.info(f"Sending speech control command: '{command}'")
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.connect("tcp://localhost:5561")
    time.sleep(0.2) 
    try:
        socket.send_string(command)
        logger.info(f"Command '{command}' sent successfully.")
    except Exception as e:
        logger.error(f"Failed to send command '{command}': {e}")
    finally:
        socket.close()
        context.term()


send_speech_control_command("resume")

logger.info("Script finished.")


