import numpy as np
## Defines the TrajPlanner class
# Calculates trajectories for different degrees and relevant coefficients
class TrajPlannerTime():    

    # Constructor
    def __init__(self,setPointTimes,angles,vels,accels):
        self.setPointTimes = setPointTimes
        self.angles = angles
        self.vels = vels
        self.accels = accels

        self.coeffsArray = self.genCoeffsArray()
        

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
    
    def genCoeffsArray(self):
        coeffsArray = np.zeros((len(self.angles[0]), len(self.angles)-1, 6))
        for pointNum in range(len(self.angles)-1):
            for jointNum in range(len(self.angles[0])):
              ##  print(jointNum)
                coeffsArray[jointNum][pointNum] = np.transpose(self.calcQuinticCoeff(self.setPointTimes[pointNum][jointNum],self.setPointTimes[pointNum+1][jointNum], self.angles[pointNum][jointNum], self.angles[pointNum+1][jointNum], self.vels[pointNum][jointNum], self.vels[pointNum+1][jointNum], self.accels[pointNum][jointNum], self.accels[pointNum+1][jointNum]))
        return coeffsArray

    def getQuinticPositions(self, time):
        coeffsSets = np.zeros(len(self.angles[0]))
        for jointNum, coeffSet in enumerate(coeffsSets):
            ##print(jointNum)
            coeffSet = int(coeffSet)
            while coeffSet+1 < len(self.setPointTimes)-1 and time >= self.setPointTimes[coeffSet+1][jointNum]:
                coeffsSets[jointNum] += 1
                coeffSet += 1

        poses = np.zeros(len(self.angles[0]))
        for jointNum in range(len(self.angles[0])):
            coeffs = self.coeffsArray[jointNum][int(coeffsSets[jointNum])]
            poses[jointNum] = sum([coeff*time**index for index, coeff in enumerate(coeffs)])
           ## print(poses)
        return(poses)