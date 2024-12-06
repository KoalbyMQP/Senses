import numpy as np

class PID():
    def __init__(self, kP, kI, kD):
        self.kP = kP
        self.kD = kD
        self.kI = kI
        self.error = 0
        self.prevError = 0
        self.errorMemory = 10
        self.errorList = np.zeros(self.errorMemory)
        self.errorIndex = 0
        self.output = 0

    def setError(self, error):
        self.error = error
        self.errorList[self.errorIndex] = error
        self.errorIndex += 1
        self.errorIndex %= self.errorMemory
    
    def calculate(self):
        errorChange = self.error-self.prevError
        self.output = self.kP*self.error + self.kD*errorChange + self.kI*sum(self.errorList)
        self.prevError = self.error
        return self.output