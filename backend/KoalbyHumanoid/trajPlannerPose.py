import numpy as np
## Defines the TrajPlanner class
# Calculates trajectories for different degrees and relevant coefficients
class TrajPlannerPose():    

    # Constructor
    def __init__(self, setpoints):
        self.setpoints = np.array(setpoints)
    

    ## N Trajectory Methods

    # Given the time between setpoints, number of points between
    # waypoints, and degree of path, returns the Nth degree trajectory
    # travelTime [int] - time between setPoints
    # pointsNum [int] - number of waypoints between setpoints
    # degreeN [int] - degree to calculate trajectory for must be off
    def getNTraj(self, travelTime, pointsNum, degreeN):
        setPoints = self.setpoints
        numJoints = setPoints.shape[1]
        wayPointsList = np.zeros([((setPoints.shape)[0]-1)*(pointsNum+1)+1, numJoints+1])
        # Loops through each joint
        for i in range(numJoints):
            count = 0
            # Loops through each setPoint
            for j in range ((setPoints.shape)[0]-1):
                # Calculates coeffs for given setPoint for given joint
                coeff = self.calcNCoeff(0, travelTime, setPoints[j,i], setPoints[j+1,i], degreeN)
                # Appends the starting setPoint to list
                wayPointsList[count,1:] = setPoints[j,:]
                count = count + 1
                # Calculates and appends all wayPoints between current
                # setPoint and next
                wayPointsList[count:count+pointsNum,i+1] = np.transpose(self.calcNTraj(travelTime, pointsNum, coeff, degreeN))
                count = count + pointsNum
            
            # Appends the final setPoint to list
            wayPointsList[count,1:] = setPoints[(setPoints.shape)[0]-1,:]
        
        # Calculates time for each point to travel
        time = np.transpose(np.linspace(0, travelTime*((setPoints.shape)[0]-1), num=(wayPointsList.shape)[0]))
        # Adds the time to the list
        wayPointsList[:,0] = time
        return wayPointsList

    # Given the time between setpoints, number of points between
    # waypoints, polynomial coefficients and degree of path, returns 
    # the Nth degree trajectory wayPoints for single pair of setPoints
    # travelTime [int] - time between setPoints
    # pointsNum [int] - number of waypoints between setpoints
    # coeff [N+1 doubles] - polynomial coefficients for trajectory
    # degreeN [int] - degree to calculate trajectory for must be off
    def calcNTraj(self, travelTime, pointsNum, coeff, degreeN):
        waypoints = np.zeros([pointsNum, 1])
        # Calculates difference in time for each wayPoint
        times = np.linspace(0,travelTime,num=pointsNum+2)
        # Loops through wayPoints between setPoints
        for i in range(1,pointsNum+1):
            # Extracts current relevant time from array
            t = times[i]
            wayPoint = 0
            # Loops through to calculate Nth polynomial calcs
            for j in range(degreeN+1):
                # Calculates part of the wayPoint from polynomial
                wayPoint = wayPoint + coeff[j]*t**j
            
            # Appends calculated point to list
            waypoints[i-1,0] = wayPoint
        return waypoints

    # Given the initial time, final time, initial position, final
    # position, and degree of path, returns Nth degree polynomial 
    # coefficients
    # t0 [double] - start time of setPoint
    # tf [double] - end time of setPoint
    # p0 [double] - position of current setPoint
    # pf [double] - position of next setPoint
    # degreeN [int] - degree to calculate trajectory for must be off
    def calcNCoeff(self, t0, tf, p0, pf, degreeN):
        matrixParams = [t0, tf]
        coeffMatrix = np.zeros([degreeN+1,degreeN+1])         
        rowNum = 0
        # Goes through matrix parameters
        for i in range(2):
            # Sets parameter
            currentParam = matrixParams[i]
            # Resets previous exponent list to zeros
            preExponents = np.zeros([degreeN+1,1])
            # Sets multiplied list to zeros
            multiplied = np.zeros([degreeN+1,1])
            # Resets number of columns to skip to 1
            skipColumns = 1
            # Loops through each column of matrix
            for j in range(degreeN+1):
                # Sets previous exponents to be increasing by 1
                preExponents[j] = j+1
                # Sets multiplied list to 1
                multiplied[j] = 1
            
            # Loops through each row for given parameter
            for j in range(int((degreeN+1)/2)):
                # Loops through each column, skipping given amount
                for k in range(skipColumns-1,degreeN+1):
                    # Calculates current matrix index
                    coeffMatrix[rowNum,k] = multiplied[k]*currentParam**(preExponents[k]-1)
                    # Sets previous exponent to the current for next
                    preExponents[k] = preExponents[k]-1
                    # Sets multiplied to to the current for next time
                    multiplied[k] = preExponents[k]*multiplied[k]
                
                rowNum = rowNum + 1
                skipColumns = skipColumns + 1
        
        qs = np.vstack(np.zeros([degreeN+1,1]))
        qs[0] = p0
        # Sets pf to proper position for mulitplication
        qs[int((degreeN+1)/2)] = pf
        # Gets coefficients by division of matricies
        coeff = np.linalg.lstsq(coeffMatrix,qs,rcond=None)
        return coeff[0]

    ## Quintic Trajectory Methods

    # Given the time between setpoints, and number of points between
    # waypoints, returns the quintic trajectory
    # travelTime [int] - time between setPoints
    # pointsNum [int] - number of waypoints between setpoints
    def getQuinticTraj(self, travelTime, pointsNum):
        setPoints = self.setpoints
        numJoints = setPoints.shape[1]
        wayPointsList = np.zeros([((setPoints.shape)[0]-1)*(pointsNum+1)+1, numJoints+1])
        # Loops through each joint
        for i in range(numJoints):
            count = 0
            # Loops through each setPoint
            for j in range(1,(setPoints.shape)[0]):
                # Calculates coeffs for given setPoint for given joint
                coeff = self.calcQuinticCoeff(0, travelTime, setPoints[j-1,i], setPoints[j,i], 0, 0, 0, 0)
                # Appends the starting setPoint to list
                wayPointsList[count,1:] = setPoints[j-1,:]
                count = count + 1
                # Calculates and appends all wayPoints between current
                # setPoint and next
                wayPointsList[count:count+pointsNum,i+1] = np.transpose(self.calcQuinticTraj(travelTime, pointsNum, coeff))
                count = count + pointsNum
            
            # Appends the final setPoint to list
            wayPointsList[count,1:] = setPoints[(setPoints.shape)[0]-1,:]
        
        # Calculates time for each point to travel
        time = np.transpose(np.linspace(0, travelTime*((setPoints.shape)[0]-1), num=(wayPointsList.shape)[0]))
        # Adds the time to the list
        wayPointsList[:,0] = time
        return wayPointsList
    
    # Given the time between setpoints, number of points between
    # waypoints, and polynomial coefficients, returns the quintic 
    # trajectory of wayPoints for a single pair of setPoints
    # travelTime [int] - time between setPoints
    # pointsNum [int] - number of waypoints between setpoints
    # coeff [N+1 doubles] - polynomial coefficients for trajectory
    def calcQuinticTraj(self, travelTime, pointsNum, coeff):
        waypoints = np.zeros([pointsNum, 1])
        # Calculates difference in time for each wayPoint
        times = np.linspace(0,travelTime,num=pointsNum+2)
        # Loops through wayPoints between setPoints
        for k in range(1,pointsNum+1):
            # Extracts current relevant time from array
            t = times[k]
            # Calculates the wayPoint from polynomial coeffs and
            # appends to list
            waypoints[k-1] = coeff[0] + coeff[1]*t + coeff[2]*t**2 + coeff[3]*t**3 + coeff[4]*t**4 + coeff[5]*t**5
        return waypoints
    

    # Given the initial time, final time, initial position, final
    # position, initial velocity, final velocity, initial acceleration,
    # and final acceleration, returns quintic polynomial coefficients
    # t0 [double] - start time of setPoint
    # tf [double] - end time of setPoint
    # p0 [double] - position of current setPoint
    # pf [double] - position of next setPoint
    # v0 [double] - starting velocity of setPoint
    # vf [double] - velocity at next setPoint
    # a0 [double] - starting acceleration of setPoint
    # af [double] - acceleration at next setPoint
    def calcQuinticCoeff(self, t0, tf, p0, pf, v0, vf, a0, af):
        # Known system of equations as matrix for a quintic trajectory
        coeffMatrix = [[1, t0, t0**2, t0**3, t0**4, t0**5],
                       [0, 1, 2*t0, 3*t0**2, 4*t0**3, 5*t0**4],
                       [0, 0, 2, 6*t0, 12*t0**2, 20*t0**3],
                       [1, tf, tf**2, tf**3, tf**4, tf**5],
                       [0, 1, 2*tf, 3*tf**2, 4*tf**3, 5*tf**4],
                       [0, 0, 2, 6*tf, 12*tf**2, 20*tf**3]]
        # Inputs to use for solving coefficients
        qs = np.vstack([p0, v0, a0, pf, vf, af])
        # Gets coefficients by division of matricies
        coeff = np.linalg.lstsq(coeffMatrix,qs,rcond=None)
        return coeff[0]

    ## Cubic Trajectory Methods

    # Given the time between setpoints, and number of points between
    # waypoints, returns the cubic trajectory
    # travelTime [int] - time between setPoints
    # pointsNum [int] - number of waypoints between setpoints
    def getCubicTraj(self, travelTime, pointsNum):
        setPoints = self.setpoints
        numJoints = setPoints.shape[1]
        wayPointsList = np.zeros([((setPoints.shape)[0]-1)*(pointsNum+1)+1, numJoints+1])
        # Loops through each joint
        for i in range(numJoints):
            count = 0
            # Loops through each setPoint
            for j in range(1,(setPoints.shape)[0]):
                # Calculates coeffs for given setPoint for given joint
                coeff = self.calcCubicCoeff(0, travelTime, setPoints[j-1,i], setPoints[j,i], 0, 0)
                # Appends the starting setPoint to list
                wayPointsList[count,1:] = setPoints[j-1,:]
                count = count + 1
                # Calculates and appends all wayPoints between current
                # setPoint and next
                wayPointsList[count:count+pointsNum,i+1] = np.transpose(self.calcCubicTraj(travelTime, pointsNum, coeff))
                count = count + pointsNum
            
            # Appends the final setPoint to list
            wayPointsList[count,1:] = setPoints[(setPoints.shape)[0]-1,:]
        
        # Calculates time for each point to travel
        time = np.transpose(np.linspace(0, travelTime*((setPoints.shape)[0]-1), num=(wayPointsList.shape)[0]))
        # Adds the time to the list
        wayPointsList[:,0] = time
        return wayPointsList

    # Given the time between setpoints, number of points between
    # waypoints, and polynomial coefficients, returns the cubic
    # trajectory of wayPoints for a single pair of setPoints
    # travelTime [int] - time between setPoints
    # pointsNum [int] - number of waypoints between setpoints
    # coeff [N+1 doubles] - polynomial coefficients for trajectory
    def calcCubicTraj(self, travelTime, pointsNum, coeff):
        waypoints = np.zeros([pointsNum, 1])
        # Calculates difference in time for each wayPoint
        times = np.linspace(0,travelTime,num=pointsNum+2)
        # Loops through wayPoints between setPoints
        for k in range(1,pointsNum+1):
            # Extracts current relevant time from array
            t = times[k]
                # Calculates the wayPoint from polynomial coeffs and
            # appends to list
            waypoints[k-1] = coeff[0] + coeff[1]*t + coeff[2]*t**2 + coeff[3]*t**3
        return waypoints
    

    # Given the initial time, final time, initial position, final
    # position, initial velocity, and final velocity, returns cubic 
    # polynomial coefficients
    # t0 [double] - start time of setPoint
    # tf [double] - end time of setPoint
    # p0 [double] - position of current setPoint
    # pf [double] - position of next setPoint
    # v0 [double] - starting velocity of setPoint
    # vf [double] - velocity at next setPoint
    def calcCubicCoeff(self, t0, tf, p0, pf, v0, vf):
        # Known system of equations as matrix for a cubic trajectory
        coeffMatrix = [[1, t0, t0**2, t0**3],
                       [0, 1, 2*t0, 3*t0**2],
                       [1, tf, tf**2, tf**3],
                       [0, 1, 2*tf, 3*tf**2]]
        # Inputs to use for solving coefficients
        qs = np.vstack([p0, v0, pf, vf])
        # Gets coefficients by division of matricies
        coeff = np.linalg.lstsq(coeffMatrix,qs,rcond=None)
        return coeff[0]
    
    def getPositions(self, setPointTimes, angles, vels, accels, time):
        coeffsArray = np.zeros((len(angles[0]), len(angles)-1, 6))
        for pointNum in range(len(angles)-1):
            for jointNum in range(len(angles[0])):
                coeffsArray[jointNum][pointNum] = np.transpose(self.calcQuinticCoeff(setPointTimes[pointNum][jointNum],setPointTimes[pointNum+1][jointNum], angles[pointNum][jointNum], angles[pointNum+1][jointNum], vels[pointNum][jointNum], vels[pointNum+1][jointNum], accels[pointNum][jointNum], accels[pointNum+1][jointNum]))


        coeffsSets = [0, 0, 0]
        for jointNum, coeffSet in enumerate(coeffsSets):
            while coeffSet+1 < len(setPointTimes)-1 and time >= setPointTimes[coeffSet+1][jointNum]:
                coeffsSets[jointNum] += 1
                coeffSet += 1

        poses = np.zeros(len(angles))

        for jointNum in range(len(angles[0])):
            coeffs = coeffsArray[jointNum][coeffsSets[jointNum]]
            poses[jointNum] = sum([coeff*time**index for index, coeff in enumerate(coeffs)])
            
        return(poses)