import matplotlib.pyplot as plt

class Plotter():
    def __init__(self, plotCounter, shouldDisplay):
        self.fig = plt.figure()
        self.Xs = []
        self.Ys = []
        self.Zs = []
        self.ax = self.fig.add_subplot(1, 1, 1, projection="3d")
        self.plotCounter = plotCounter
        self.plotCalls = 0
        self.shouldDisplay = shouldDisplay

    def addPoint(self, point):
        self.plotCalls += 1
        self.Xs.append(point[0])
        self.Ys.append(point[1])
        self.Zs.append(point[2])
        if self.shouldDisplay and self.plotCalls == self.plotCounter:
            self.plotCalls = 0
            self.ax.clear()
            self.ax.plot(self.Xs, self.Ys, self.Zs)
            plt.pause(0.00001)