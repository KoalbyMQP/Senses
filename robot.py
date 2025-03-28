from typing import Callable

from cyberonics_py import Robot, Device
from cyberonics_py.graphics import Button, GraphicCell

from targets import Depthai
class Finley(Robot):
    def __init__(self):
        self.control_cell = ControlCell()
        super().__init__([self.control_cell], [Depthai(self)])



class ControlCell(Device):
    def __init__(self):

        self.listeners: [Callable] = []

        def button_pressed():
            print("Button pressed!")
            for listener in self.listeners:
                listener()

        button = Button(text="Press me", onclick=button_pressed)
        super().__init__(properties=[], graphic_cell=GraphicCell([button]))

    def add_listener(self, listener: Callable):
        self.listeners.append(listener)