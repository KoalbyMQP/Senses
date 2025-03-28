from typing import Callable
import asyncio
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

    def add_listener(self, listener: Callable):
        self.listeners.append(listener)



class Depthai(Target):
    def __init__(self, robot: Robot):
        super().__init__(robot)
        self.robot = robot
        self._task = None
        self._stop_event = asyncio.Event()

    async def _depthai_worker(self):
        try:
            await asyncio.to_thread(depthai_demo)
        except asyncio.CancelledError:
            print("Depthai task was cancelled")
        finally:
            print("Depthai worker finished")

    async def run(self):
        self._stop_event.clear()
        self._task = asyncio.create_task(self._depthai_worker())

    async def shutdown(self, beat):
        print("Shutting down Depthai")
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                print("Depthai task cancellation complete")
