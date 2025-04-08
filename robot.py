from typing import Callable
import asyncio
from multiprocessing import Process
from cyberonics_py import Robot, Device, Target
from cyberonics_py.graphics import Button, GraphicCell
from Vision.depthai_demo import main as depthai_demo


# from .targets import Depthai
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

    def listen(self, listener: Callable):
        self.listeners.append(listener)



class Depthai(Target):
    def __init__(self, robot: Robot):
        super().__init__("Depthai", robot)
        self.process = None

    def _run(self) -> Process:
        self.process = Process(target=depthai_demo, args=["-cnn", "yolo-v3-tiny-tf", "-s", "color"])
        self.process.start()
        return self.process

    async def _shutdown(self, beat):
        if self.process:
            self.process.terminate()
            self.process.join()
            self.process = None
