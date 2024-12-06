import sys
import time
import math
import numpy as np

import backend.KoalbyHumanoid.Config as Config
import modern_robotics as mr
from backend.KoalbyHumanoid.Link import Link
from backend.KoalbyHumanoid.PID import PID
from backend.KoalbyHumanoid.ArduinoSerial import ArduinoSerial
from backend.KoalbyHumanoid.Motor import Motor
from coppeliasim_zmqremoteapi_client import RemoteAPIClient
from backend.KoalbyHumanoid import poe as poe
from backend.KoalbyHumanoid.IMU import IMU
from backend.KoalbyHumanoid.Electromagnet import Electromagnet

TIME_BETWEEN_MOTOR_CHECKS = 2

class Robot():

    
    # Initialization methods

    def __init__(self, is_real):
        self.remotehost = '192.168.1.15'
        self.remoteport = 23000
        self.is_real = is_real
        if self.is_real:
            self.client = None
            self.sim = None
            self.client_id = None
            self.arduino_serial_init()
            self.motors = self.real_motors_init()
            
            self.imuPIDX = PID(0.2,0,0.1) # 1
            self.imuPIDZ = PID(0.25,0.0,0.0075)
            
            self.electromagnet = Electromagnet()
        else:
            self.checkCoppeliaSimResponding()

            self.client = RemoteAPIClient(host=self.remotehost, port=self.remoteport)
            self.sim = self.client.require('sim')
            self.motorMovePositionScriptHandle = self.sim.getScript(self.sim.scripttype_childscript, self.sim.getObject("./chest_respondable"))
            self.motors = self.sim_motors_init()
            
            self.imuPIDX = PID(0.3,0.005,0.1)
            self.imuPIDZ = PID(0.25,0.0,0.0075)

        self.lastMotorCheck = time.time()

        self.imu = IMU(self.is_real, sim=self.sim)
        self.CoM = np.array([0, 0, 0])
        self.ang_vel = [0, 0, 0]
        self.last_vel = [0, 0, 0]
        self.ang_accel = [0, 0, 0]
        self.balancePoint = np.array([0, 0, 0])
        self.rightFootBalancePoint = np.array([0, 0, 0])
        self.leftFootBalancePoint = np.array([0, 0, 0])
        self.primitives = []
        self.chain = self.chain_init()
        self.links = self.links_init()
        self.PID = PID(0.25,0.1,0)
        # self.imuPIDX = PID(0.3,0.005,0.1)
        # self.imuPIDZ = PID(0.25,0.0,0.0075)
        self.PIDVel = PID(0.0,0,0)
        self.VelPIDX = PID(0.002, 0, 0)
        self.VelPIDZ = PID(0.009, 0.0005, 0.0015)
        # self.trackSphere = self.sim.getObject("./trackSphere")
        # self.sim.setObjectColor(self.trackSphere, 0, self.sim.colorcomponent_ambient_diffuse, (0,0,1))
        if(not is_real):
            self.sim.startSimulation()
        # self.sim.startSimulation()
        print("Robot Created and Initialized")

    def checkCoppeliaSimResponding(self):
        client = RemoteAPIClient(host=self.remotehost, port=self.remoteport)
        client._send({'func': '', 'args': ['']})
        if (client.socket.poll(1000) == 0):
            raise Exception("CoppeliaSim is not responding. Restart CoppeliaSim and try again.")
        else:
            client.__del__()

    def arduino_serial_init(self):
        self.arduino_serial = ArduinoSerial()
        self.initHomePos() # This initializes the robot with all the initial motor positions

    def chain_init(self):
        chain = {
            self.motors[24].name:self.motors[23],
            self.motors[23].name:self.motors[22],
            self.motors[22].name:self.motors[21],
            self.motors[21].name:self.motors[20],
            self.motors[20].name:self.motors[10],

            self.motors[19].name:self.motors[18],
            self.motors[18].name:self.motors[17],
            self.motors[17].name:self.motors[16],
            self.motors[16].name:self.motors[15],
            self.motors[15].name:self.motors[10],

            self.motors[10].name:self.motors[13],
            self.motors[13].name:self.motors[12],
            self.motors[12].name:self.motors[14],
            self.motors[14].name:self.motors[11],
            self.motors[11].name:"base",

            self.motors[4].name:self.motors[3],
            self.motors[3].name:self.motors[2],
            self.motors[2].name:self.motors[1],
            self.motors[1].name:self.motors[0],
            self.motors[0].name:"base",

            self.motors[9].name:self.motors[8],
            self.motors[8].name:self.motors[7],
            self.motors[7].name:self.motors[6],
            self.motors[6].name:self.motors[5],
            self.motors[5].name:"base"
        }
        return chain
    
    def links_init(self):
        links = list()
        for linksConfig in Config.links:
            link = Link(linksConfig[0], linksConfig[1])
            links.append(link)
        return links

    def sim_motors_init(self):
        motors = list()
        for motorConfig in Config.motors:
            print("Beginning to stream", motorConfig[3])
            handle = self.sim.getObject("/" + motorConfig[3])
            motor = Motor(False, motorConfig[0], motorConfig[3], motorConfig[6], motorConfig[7], pidGains=motorConfig[5], sim=self.sim, handle=handle)
            motor.theta = motor.get_position()
            motor.name = motorConfig[3]
            motors.append(motor)
        return motors
    
    def real_motors_init(self):
        motors = list()
        for motorConfig in Config.motors:
            motor = Motor(True, motorConfig[0], motorConfig[3], motorConfig[6], motorConfig[7], angle_limit=motorConfig[1], serial=self.arduino_serial)
            motors.append(motor)
        return motors
    
    # Motor Control Methods

    def getMotor(self, key):
        for motor in self.motors:
            if motor.motor_id == key:
                return motor

    def moveTo(self, motor, position):
        motor.move(position)
        
    def moveToTarget(self, motor):
        motor.move(motor.target)

    def moveAllTo(self, position):
        for motor in self.motors:
            motor.move(position)

    def moveAllToTarget(self):
        if self.is_real:
            for motor in self.motors:
                time.sleep(0.01)
                motor.move(motor.target)
        else:
            # joint = self.locate(self.motors[19])
            # self.sim.setObjectPosition(self.trackSphere,(joint[0][3]/1000,joint[2][3]/-1000,joint[1][3]/1000),self.sim.getObject("./Chest_respondable"))
            self.sim.callScriptFunction('setJointAngles', self.motorMovePositionScriptHandle,[motor.handle for motor in self.motors], [motor.target[0] for motor in self.motors])
            # for motor in self.motors:
            #     motor.move(motor.target)

    def initHomePos(self):
        if self.is_real:
            self.arduino_serial.send_command("1")
            time.sleep(2)

    def readBatteryLevel(self):
        if self.is_real:
            self.arduino_serial.send_command("30")
            return self.arduino_serial.read_line()

    def shutdown(self):
        if self.is_real:
            self.arduino_serial.send_command("100")
            
    # Controls/Kinematics/Dynamics methods

    def updateRobotCoM(self):
        rightArm = self.updateRightArmCoM()
        leftArm = self.updateLeftArmCoM()
        torso = self.updateTorsoCoM()
        rightLeg = self.updateRightLegCoM()
        leftLeg = self.updateLeftLegCoM()
        chestMass = 618.15
        chest = [0, 71.83, 54.35]
        rightArmMass = 524.11
        leftArmMass = 524.11
        torsoMass = 434.67
        rightLegMass = 883.81
        leftLegMass = 889.11
        massSum = rightArmMass+leftArmMass+torsoMass+chestMass
        CoMx = rightArm[0] * rightArmMass + leftArm[0] * leftArmMass + torso[0]*torsoMass + chest[0]*chestMass + rightLeg[0]*rightLegMass + leftLeg[0]*leftLegMass
        CoMy = rightArm[1] * rightArmMass + leftArm[1] * leftArmMass + torso[1]*torsoMass + chest[1]*chestMass + rightLeg[1]*rightLegMass + leftLeg[1]*leftLegMass
        CoMz = rightArm[2] * rightArmMass + leftArm[2] * leftArmMass + torso[2]*torsoMass + chest[2]*chestMass + rightLeg[2]*rightLegMass + leftLeg[2]*leftLegMass
        self.CoM = [CoMx / massSum, CoMy / massSum, CoMz / massSum]
        return self.CoM

    def updateRightArmCoM(self):
        motorList = [self.motors[0], self.motors[1], self.motors[2], self.motors[3], self.motors[4]]
        linkList = [self.links[0], self.links[1], self.links[2], self.links[3], self.links[4]]
        return poe.calcLimbCoM(motorList, linkList)
    
    def updateLeftArmCoM(self):
        motorList = [self.motors[5], self.motors[6], self.motors[7], self.motors[8], self.motors[9]]
        linkList = [self.links[5], self.links[6], self.links[7], self.links[8], self.links[9]]
        return poe.calcLimbCoM(motorList, linkList)
    
    def updateTorsoCoM(self):
        motorList = [self.motors[11], self.motors[13], self.motors[10], self.motors[12], self.motors[14]]
        linkList = [self.links[11], self.links[13], self.links[10], self.links[12], self.links[14]]
        return poe.calcLimbCoM(motorList, linkList)
    
    def updateRightLegCoM(self):
        motorList = [self.motors[15], self.motors[16], self.motors[17], self.motors[18], self.motors[19]]
        linkList = [self.links[15], self.links[16], self.links[17], self.links[18], self.links[19]]
        #print(poe.calcLegCoM(self, motorList))
        return poe.calcLegCoM(self, motorList, linkList)

    def updateLeftLegCoM(self):
        motorList = [self.motors[20], self.motors[21], self.motors[22], self.motors[23], self.motors[24]]
        linkList = [self.links[20], self.links[21], self.links[22], self.links[23], self.links[24]]
        #print(poe.calcLegCoM(self, motorList))
        return poe.calcLegCoM(self, motorList, linkList)
      
    def locate(self, motor):
        slist = []
        thetaList = []
        M = motor.M
        slist.append(motor.twist)
        thetaList.append(motor.get_position())
        next = self.chain[motor.name]
        while next != "base":
            slist.append(next.twist)
            thetaList.append(next.get_position())
            next = self.chain[next.name]            
        slist.reverse()
        thetaList.reverse()
        # print(thetaList)
        location = mr.FKinSpace(M,np.transpose(slist),thetaList)
        return location
    
    def locatePolygon(self):
        slist = []
        thetaList = []
        locations = []
        rightAnkleM = [[1,0,0,-43.49],[0,1,0,659.84],[0,0,1,70.68],[1,0,0,0]]
        leftAnkleM = [[1,0,0,43.49],[0,1,0,659.84],[0,0,1,70.68],[1,0,0,0]]
        rightAnkleMotor = self.motors[Config.Joints.Right_Ankle_Joint.value]
        leftAnkleMotor = self.motors[Config.Joints.Left_Ankle_Joint.value]
        Ms = [rightAnkleM, leftAnkleM]
        ankleMotors = [rightAnkleMotor, leftAnkleMotor]
        for i in range(len(ankleMotors)):
            motor = ankleMotors[i]
            M = Ms[i]
            slist.append(motor.twist)
            thetaList.append(motor.get_position())
            next = self.chain[motor.name]
            while next != "base":
                slist.append(next.twist)
                thetaList.append(next.get_position())
                next = self.chain[next.name]         
            slist.reverse()
            thetaList.reverse()
            # print(thetaList)
            locations.append(mr.FKinSpace(M,np.transpose(slist),thetaList)[0:3,3])
        return locations
    
    def updateBalancePoint(self):
        rightAnkle = self.locate(self.motors[Config.Joints.Right_Ankle_Joint.value])
        leftAnkle = self.locate(self.motors[Config.Joints.Left_Ankle_Joint.value])
        rightAnkleToSole = np.array([[1,0,0,-24.18],[0,1,0,-35],[0,0,1,29.14],[0,0,0,1]])
        leftAnkleToSole = np.array([[1,0,0,24.18],[0,1,0,-35],[0,0,1,29.14],[0,0,0,1]])
        rightSole = np.matmul(rightAnkle,rightAnkleToSole)
        leftSole = np.matmul(leftAnkle,leftAnkleToSole)
        rightPolyCoords = rightSole[0:3,3]
        leftPolyCoords = leftSole[0:3,3]
        self.rightFootBalancePoint = rightPolyCoords
        self.leftFootBalancePoint = leftPolyCoords
        centerPoint = (rightPolyCoords+leftPolyCoords)/2
        self.balancePoint = centerPoint
        # self.sim.setObjectPosition(self.trackSphere,(self.balancePoint[0]/1000,-self.balancePoint[2]/1000,self.balancePoint[1]/1000),self.sim.getObject("./Chest_respondable"))
        return centerPoint
    
    def IK(self, motor, T, thetaGuess):
        """Computes the Inverse Kinematics from the Body Frame to the desired end effector motor

        Args:
            eeMotor (SimMotor): Motor you want to calculate IK towards
            T (4x4 Matrix): The desired final 4x4 matrix depicting the final position and orientation
        """
        Slist = []
        Slist.append(motor.twist)
        next = self.chain[motor.name]
        while next != "base":
            Slist.append(next.twist)
            next = self.chain[next.name]
        Slist.reverse()
        M = motor.home
        eomg = 0.01
        ev = 0.01
        return (mr.IKinSpace(Slist, M, T, thetaGuess, eomg, ev))

    # methods to balance (unassisted standing)

    def IMUBalance(self, Xtarget, Ztarget):
        data = self.imu.getData()

        xRot = data[0]
        zRot = data[2]
        Xerror = Xtarget - xRot
        Zerror = Ztarget - zRot
        self.imuPIDX.setError(Xerror)
        self.imuPIDZ.setError(Zerror)
        newTargetX = self.imuPIDX.calculate()
        newTargetZ = self.imuPIDZ.calculate()
        # print(math.degrees(newTargetX), math.degrees(newTargetZ))
        self.motors[13].target = (newTargetZ, 'P')
        self.motors[10].target = (newTargetX, 'P')

        self.checkMotorsAtInterval(TIME_BETWEEN_MOTOR_CHECKS)

    def VelBalance(self, balancePoint):
        balanceError = balancePoint - self.CoM
        Xerror = balanceError[0]
        Zerror = balanceError[2]
        self.VelPIDX.setError(Xerror)
        self.VelPIDZ.setError(Zerror)
        newTargetX = self.VelPIDX.calculate()
        newTargetZ = self.VelPIDZ.calculate()
        self.motors[13].target = (newTargetX, 'V')
        self.motors[10].target = (-newTargetZ, 'V')
        return balanceError

    def balanceAngle(self):
        balanceError = self.balancePoint - self.CoM
        
        # targetTheta = math.atan2(staticCoM[1] - staticKickLoc[1], staticCoM[2] - staticKickLoc[2])
        # kickMotorPos = self.locate(self.motors[Config.Joints.Left_Thigh_Kick_Joint.value])
        # currTheta = math.atan2(self.CoM[1] - kickMotorPos[1], self.CoM[2] - kickMotorPos[2])
        # thetaError = targetTheta - currTheta
        # self.PID.setError(thetaError)
        # newTarget = self.PID.calculate()

        self.PIDVel.setError(balanceError[2])
        newTarget = self.PIDVel.calculate()
        
        self.motors[10].target = (-0.000001*newTarget, 'V')
        
        # self.motors[22].target = (0.001*newTarget, 'V')
        # # self.motors[24].target = (-10, 'V')
        # self.motors[17].target = (-0.001*newTarget, 'V')
        # self.motors[19].target = (10, 'V')
        # self.IMUBalance(0, 0)
        return balanceError

    def balanceAngleOLD(self):
        # targetZ = 88
        # zError = targetZ - self.CoM[2]
        # target = 0.11
        # self.locate(self.motors[Config.Joints.Left_Ankle_Joint.value])*ankleL_to_sole
        staticCoM = [-9.2, -487.6, 90.5]
        staticKickLoc = [93.54, -209.39, 41.53]
        targetTheta = math.atan2(staticCoM[1] - staticKickLoc[1], staticCoM[2] - staticKickLoc[2])
        kickMotorPos = self.locate(self.motors[Config.Joints.Left_Thigh_Kick_Joint.value])
        currTheta = math.atan2(self.CoM[1] - kickMotorPos[1], self.CoM[2] - kickMotorPos[2])
        thetaError = targetTheta - currTheta
        # print(math.degrees(targetTheta), math.degrees(currTheta), thetaError, self.CoM)
        # print(self.CoM)
        # print(math.degrees(self.motors[22].target), math.degrees(self.motors[22].target), math.degrees(self.motors[17].target), math.degrees(self.motors[19].target))
        self.PID.setError(thetaError)
        newTarget = self.PID.calculate()
        
        self.motors[22].target = (-newTarget, 'P')
        self.motors[24].target = (-newTarget, 'P')
        self.motors[17].target = (newTarget, 'P')
        self.motors[19].target = (newTarget, 'P')
        self.IMUBalance(0, 0)
        return thetaError
    
    def decodeError(self, errorNum : int):
        errorNum = int(errorNum)
        errorDict = { 1: "Exceed Input Voltage Limit",
                      2: "Exceed Allow POT Limit",
                      4: "Exceed Temperature Limit",
                      8: "Invalid Packet (8)",
                      9: "Invalid Packet (9)",
                      16: "Overload Detected",
                      32: "Driver Fault Detected",
                      64: "EEP REG Distorted",
                      255: "No Communication"}
                      
        if(errorNum in errorDict.keys()):
            return errorDict[errorNum]
        else:
            return errorNum
    
    # If continuously called, checks motor statuses at the given interval (in seconds)
    def checkMotorsAtInterval(self, interval):
        if(time.time() > self.lastMotorCheck + interval):
            self.lastMotorCheck = time.time()
            self.checkMotors()

    # Checks the status of all motors
    def checkMotors(self):
        if(not self.is_real):
            return
        
        self.arduino_serial.send_command("50") # Check motors command

        while True:
            line = self.arduino_serial.read_line()
            if(line == "END" or line == None):
                return
            
            msg = line.split(" ")
            if(len(msg) >= 3):
                print(f"Error: {self.decodeError(msg[1])}, Motor: {msg[0]}, Angle: {msg[2]}")
            else:
                print(line)