from cyberonics_py import Robot, Device
from targets import depthai
class Finley(Robot):
    def __init__(self):
        self.control_cell = ControlCell()
        super.__init__([self.control_cell], [depthai])



class ControlCell(Device):
    def __init__(self):

        self.listeners: [Callable] = []

        def button_pressed():
            print("Button pressed!")
            for listener in self.listeners:
                listener()

        button = Button(text="Press me", onclick=button_pressed)
        super().__init__(graphic_cell=GraphicCell([button]))

    def add_listener(self, listener: Callable):
        self.listeners.append(listener)