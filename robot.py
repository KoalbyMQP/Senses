##Future implementation needed. This will be where the target / user code is selected, and subsequently run. 

## Current target: voice_helper.sh

from typing import Callable
import asyncio
from multiprocessing import Process
from cyberonics_py import Robot, Device, Target
from cyberonics_py.graphics import Button, GraphicCell
##from Vision.depthai_demo import main as depthai_demo
import subprocess
import os


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

    def _run(self):
        #Set the script path
        print("Running shell script")
        script_path = os.path.join(os.path.dirname(__file__), "Vision", "voice_helper.sh")
        #run a subprocess
        #.sh scripts may not be executable, so but "bash" path to the script
        self.process = subprocess.run(
            ["bash", script_path], 
            cwd="~/cyberonics/usr/local/cyberonics/projects/RtQVAWsRG2lTVrSkx9L0/Vision")


    async def _shutdown(self, beat):
        if self.process:
            self.process.terminate()
            self.process.join()
            self.process = None
