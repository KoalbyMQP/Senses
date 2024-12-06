import sys, time, math

import numpy as np 
sys.path.append("./")
from backend.KoalbyHumanoid.Robot import Robot
from backend.KoalbyHumanoid.trajPlannerTime import TrajPlannerTime
from backend.Testing import assistWalkViaPoints as via
from coppeliasim_zmqremoteapi_client import RemoteAPIClient as sim
from backend.KoalbyHumanoid.Config import Joints
import copy

WAIST_OFFSET = 7 
ANKLE_OFFSET = -7 - WAIST_OFFSET
RIGHT_ROTATOR_OFFET = 5
LEFT_ROTATOR_OFFET = -5
LEFT_ABD_OFFSET = -3
RIGHT_ABD_OFFSET = 3



# Applies the given offset as a vector to the given trajectory
def applyOffsets(trajectory, offset):
    trajectory = copy.deepcopy(trajectory)

    for i in range(len(trajectory[1])):
        for j in range(len(trajectory[1][i])):
            trajectory[1][i][j] += math.radians(offset[j])

    return trajectory
    
# Creates and returns the trajectories for each of the joints
def createTrajectories(rightLeg, leftLeg, rightArm, leftArm):

    # Applies static offsets to joint poisitions (used for tweaking trajectories)
    rightOffset = [RIGHT_ABD_OFFSET, RIGHT_ROTATOR_OFFET, WAIST_OFFSET, 0, -ANKLE_OFFSET]
    leftOffset = [LEFT_ABD_OFFSET, LEFT_ROTATOR_OFFET, -WAIST_OFFSET, 0, ANKLE_OFFSET]
    rightArmOffset = [0, 0, 0, -5, -5]
    rightLeg = applyOffsets(rightLeg, rightOffset)
    leftLeg = applyOffsets(leftLeg, leftOffset)
    rightArm = applyOffsets(rightArm, rightArmOffset)

    # Generates trajectories
    rightLeg_tj = TrajPlannerTime(rightLeg[0], rightLeg[1], rightLeg[2], rightLeg[3])
    leftLeg_tj  = TrajPlannerTime(leftLeg[0],  leftLeg[1],  leftLeg[2],  leftLeg[3])
    rightArm_tj = TrajPlannerTime(rightArm[0], rightArm[1], rightArm[2], rightArm[3])
    leftArm_tj  = TrajPlannerTime(leftArm[0],  leftArm[1],  leftArm[2],  leftArm[3])

    return rightLeg_tj, leftLeg_tj, rightArm_tj, leftArm_tj

def main():
    # Edit to declare if you are testing the sim or the real robot
    is_real = True

    robot = Robot(is_real)
    print("Setup Complete") 

    #Starting Angles

    # Right arm
    robot.motors[0].target = (math.radians(-20), 'P')
    robot.motors[1].target = (math.radians(-90), 'P')
    robot.motors[3].target = (math.radians(90), 'P') #pos
    robot.motors[4].target = (math.radians(-15), 'P')

    # Left Arm
    robot.motors[5].target = (math.radians(20), 'P')
    robot.motors[6].target = (math.radians(90), 'P')
    robot.motors[8].target = (math.radians(-90), 'P')#neg
    robot.motors[9].target = (math.radians(15), 'P') 

    # robot.motors[10].target = (math.radians(0), 'P')
    # robot.motors[13].target = (math.radians(0), 'P')

    # robot.motors[17].target = (math.radians(20), 'P') #5
    # robot.motors[18].target = (math.radians(20), 'P') #10
    # robot.motors[19].target = (math.radians(-20), 'P') # -5

    # robot.motors[22].target = (math.radians(-20), 'P') #-5
    # robot.motors[23].target = (math.radians(-20), 'P') #-10
    # robot.motors[24].target = (math.radians(20), 'P') #5

    robot.motors[25].target = (math.radians(20), 'P') # Head



    # robot.motors[10].target = (math.radians(-15), 'P')
    # robot.motors[10].target = (math.radians(-15), 'P')

    simStartTime = time.time()

    robot.electromagnet.turnOn()

    # while time.time() - simStartTime < 4:
    #     time.sleep(0.01)
    #     # robot.IMUBalance(0,0)
    #     robot.moveAllToTarget()
    #     robot.checkMotorsAtInterval(2)
        

    ## EVEN TO RIGHT FOOT FORWARD
    # rLeg_tj = TrajPlannerTime(via.rf_Even2Right[0], via.rf_Even2Right[1], via.rf_Even2Right[2], via.rf_Even2Right[3])
    # lLeg_tj = TrajPlannerTime(via.lf_Even2Right[0], via.lf_Even2Right[1], via.lf_Even2Right[2], via.lf_Even2Right[3])
    # rArm_tj = TrajPlannerTime(via.ra_leftDown[0], via.ra_leftDown[1], via.ra_leftDown[2], via.ra_leftDown[3])
    # lArm_tj = TrajPlannerTime(via.la_leftDown[0], via.la_leftDown[1], via.la_leftDown[2], via.la_leftDown[3])

    [rLeg_tj, lLeg_tj, rArm_tj, lArm_tj] = createTrajectories(
        via.rf_Even2Right, 
        via.lf_Even2Right, 
        via.ra_leftDown, 
        via.la_rightDown )
    
    initialPositioning = True

    # input()

    ##  Walking
    startTime = time.time()
    state = 0

    while True:
        currentTime = time.time() - startTime
        right_points = rLeg_tj.getQuinticPositions(currentTime)
        left_points = lLeg_tj.getQuinticPositions(currentTime)

        rArm_points = rArm_tj.getQuinticPositions(currentTime)
        lArm_points = lArm_tj.getQuinticPositions(currentTime)
        
        # # Right Arm
        # robot.motors[0].target = (rArm_points[0], 'P')
        # robot.motors[1].target = (rArm_points[1], 'P')
        # robot.motors[2].target = (rArm_points[2], 'P')
        # robot.motors[3].target = (rArm_points[3], 'P') #pos
        # robot.motors[4].target = (rArm_points[4], 'P')

        # # Left Arm
        # robot.motors[5].target = (lArm_points[0], 'P')
        # robot.motors[6].target = (lArm_points[1], 'P')
        # robot.motors[7].target = (lArm_points[2], 'P')
        # robot.motors[8].target = (lArm_points[3], 'P')#neg
        # robot.motors[9].target = (lArm_points[4], 'P') 
        
        # Right arm
        robot.motors[0].target = (math.radians(-20), 'P')
        robot.motors[1].target = (math.radians(-90), 'P') 
        robot. motors[3].target = (math.radians(90), 'P') #pos
        robot.motors[4].target = (math.radians(-15), 'P')

        # Left Arm
        robot.motors[5].target = (math.radians(20), 'P')
        robot.motors[6].target = (math.radians(90), 'P')
        robot.motors[8].target = (math.radians(-90), 'P')#neg
        robot.motors[9].target = (math.radians(15), 'P') 

        # Right Leg
        robot.motors[15].target = (right_points[0], 'P')
        robot.motors[16].target = (right_points[1], 'P')
        robot.motors[17].target = (right_points[2], 'P')
        robot.motors[18].target = (right_points[3], 'P')
        robot.motors[19].target = (right_points[4], 'P')

        # Left Leg
        robot.motors[20].target = (left_points[0], 'P')
        robot.motors[21].target = (left_points[1], 'P')
        robot.motors[22].target = (left_points[2], 'P')
        robot.motors[23].target = (left_points[3], 'P')
        robot.motors[24].target = (left_points[4], 'P')

        # robot.IMUBalance(0, 0)
        robot.moveAllToTarget()
        robot.checkMotorsAtInterval(2)

        if(initialPositioning):
            input()
            initialPositioning = False
            startTime = time.time()

        if(time.time() - startTime >= 3):
            match(state):
                case 0: 
                    ##ANGLES TO GO RIGHT TO LEFT
                    # rLeg_tj = TrajPlannerTime(via.rf_Right2Left[0], via.rf_Right2Left[1], via.rf_Right2Left[2], via.rf_Right2Left[3])
                    # lLeg_tj = TrajPlannerTime(via.lf_Right2Left[0], via.lf_Right2Left[1], via.lf_Right2Left[2], via.lf_Right2Left[3])
                    # rArm_tj = TrajPlannerTime(via.ra_leftDown[0], via.ra_leftDown[1], via.ra_leftDown[2], via.ra_leftDown[3])
                    # lArm_tj = TrajPlannerTime(via.la_leftDown[0], via.la_leftDown[1], via.la_leftDown[2], via.la_leftDown[3])
                    
                    [rLeg_tj, lLeg_tj, rArm_tj, lArm_tj] = createTrajectories(
                        via.rf_Right2Left, 
                        via.lf_Right2Left, 
                        via.ra_leftDown, 
                        via.la_leftDown )

                    startTime = time.time()
                    # print("Right To Left")
                    state = 1
                    
                case 1: ##Right to Left
                    ##ANGLES TO GO LEFT TO RIGHT
                    # rLeg_tj = TrajPlannerTime(via.rf_Left2Right[0], via.rf_Left2Right[1], via.rf_Left2Right[2], via.rf_Left2Right[3])
                    # lLeg_tj = TrajPlannerTime(via.lf_Left2Right[0], via.lf_Left2Right[1], via.lf_Left2Right[2], via.lf_Left2Right[3])
                    # rArm_tj = TrajPlannerTime(via.ra_rightDown[0], via.ra_rightDown[1], via.ra_rightDown[2], via.ra_rightDown[3])
                    # lArm_tj = TrajPlannerTime(via.la_rightDown[0], via.la_rightDown[1], via.la_rightDown[2], via.la_rightDown[3])
                    
                    [rLeg_tj, lLeg_tj, rArm_tj, lArm_tj] = createTrajectories(
                        via.rf_Left2Right, 
                        via.lf_Left2Right, 
                        via.ra_rightDown, 
                        via.la_rightDown )
                    
                    # print("Left To Right")
                    startTime = time.time()
                    state = 0

if(__name__ == "__main__"):
    main()