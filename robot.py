import subprocess
from typing import Callable
import asyncio
from multiprocessing import Process
from cyberonics_py import Robot, Device, Target
from cyberonics_py.graphics import Button, GraphicCell
from Vision.depthai_demo import main as depthai_demo
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
        # Correct the path to depthai_demo.py
        command = [
            "python3","-m", "/home/finley/cyberonics/usr/local/cyberonics/projects/RtQVAWsRG2lTVrSkx9LO/Vision/depthai_demo", "-cnn", "yolo-v3-tiny-tf", "-s", "color"
        ]
        # Use subprocess to execute the command
        try:
            self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = self.process.communicate()
            # If there's any error in running the process
            if self.process.returncode != 0:
                print(f"Error running depthai_demo.py: {stderr.decode()}")
                raise Exception(f"Failed to run depthai_demo.py")
            print(stdout.decode())  # Optionally, you can print the output if needed
            return self.process
        except Exception as e:
            print(f"Error occurred: {e}")
            raise
    async def _shutdown(self, beat):
        if self.process:
            self.process.terminate()
            self.process.wait()  # Wait for the process to fully terminate
            self.process = None
