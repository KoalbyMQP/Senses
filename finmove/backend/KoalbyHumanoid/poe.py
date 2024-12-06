import modern_robotics as mr
import numpy as np
import math
import sys
from backend.KoalbyHumanoid import Config
sys.path.append("./")

def rodriguez(twist, theta):
    # R = I + sin(theta) * [w] + (1-cos(theta)) * [w]^2
    I = np.eye(3)
    w = mr.VecToso3([twist[0], twist[1], twist[2]])
    w2 = np.matmul(w, w)
    R = I + math.sin(theta) * w + (1-math.cos(theta)) * w2
    return R

def ramirez(twist, theta):
    # p = (theta * I + (1 - cos(theta)) * [w] + (theta - sin(theta) * [w]^2) * v 
    I = np.eye(3)
    w = mr.VecToso3([twist[0], twist[1], twist[2]])
    w2 = np.matmul(w, w)
    v = np.vstack([twist[3], twist[4], twist[5]])
    p = np.matmul(theta * I + (1 - math.cos(theta)) * w + (theta - math.sin(theta) * w2), v)
    return p

def makeTMatrix(R, p):
    bottomRow = np.zeros([1,4])
    bottomRow[-1] = 1
    T = np.concatenate((np.concatenate((R,p),axis=1), bottomRow), axis=0)
    return T

def calcCoMtest(tList, massList):
    """will improve to use joint/link data from Config.py"""
    massSum = 618.15
    weightX = 0
    weightY = 618.15 * 71.83
    weightZ = 618.15 * 54.35
    for i in range(len(tList)):
        massSum += massList[i]
        weightX += tList[i][0,3] * massList[i]
        weightY += tList[i][1,3] * massList[i]
        weightZ += tList[i][2,3] * massList[i]
    return [weightX/massSum, weightY/massSum, weightZ/massSum]

def calcLimbCoM(motors, links):
    massSum = 0
    weightX = 0 
    weightY = 0
    weightZ = 0
    Slist = []
    thetaList = []
    for i in range(len(motors)):
        motor = motors[i]
        link = links[i]
        Slist.append(motor.twist)
        thetaList.append(motor.get_position())
        linkCoM = mr.FKinSpace(link.M, np.transpose(Slist), thetaList)
        weightX += linkCoM[0,3] * link.mass
        weightY += linkCoM[1,3] * link.mass
        weightZ += linkCoM[2,3] * link.mass
        massSum += link.mass
    return [weightX/massSum, weightY/massSum, weightZ/massSum]

def calcLegCoM(robot, motors, links):
    massSum = 0
    weightX = 0 
    weightY = 0
    weightZ = 0
    Slist = [robot.motors[11].twist, robot.motors[13].twist, robot.motors[10].twist, robot.motors[12].twist, robot.motors[14].twist]
    thetaList = [robot.motors[11].get_position(), robot.motors[13].get_position(), robot.motors[10].get_position(), robot.motors[12].get_position(), robot.motors[14].get_position()]
    for i in range(len(motors)):
        motor = motors[i]
        link = links[i]
        Slist.append(motor.twist)
        thetaList.append(motor.get_position())
        linkCoM = mr.FKinSpace(link.M, np.transpose(Slist), thetaList)
        weightX += linkCoM[0,3] * link.mass
        weightY += linkCoM[1,3] * link.mass
        weightZ += linkCoM[2,3] * link.mass
        massSum += link.mass
    return [weightX/massSum, weightY/massSum, weightZ/massSum]

def calcLegChainIK(robot, T, rightToLeft):
    Slist = Config.rightToLeftFootTwists[0]
    M = Config.rightToLeftFootTwists[1]
    thetaList = [robot.motors[19].get_position(), robot.motors[18].get_position(), robot.motors[17].get_position(), robot.motors[16].get_position(), robot.motors[15].get_position(), 
             robot.motors[20].get_position(), robot.motors[21].get_position(), robot.motors[22].get_position(), robot.motors[23].get_position(), robot.motors[24].get_position()]
    print(thetaList)
    thetaList = [math.radians(-20), math.radians(-40), math.radians(20), 0, 0, 
                0, 0, math.radians(-20), math.radians(40), math.radians(20)]
    if not rightToLeft:
        thetaList.reverse()
    eomg = 0.01
    ev = 0.001
    return mr.IKinSpace(np.transpose(Slist), M, T, thetaList, eomg, ev)
