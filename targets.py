from cyberonics_py import Robot, Device, Target
from cyberonics_py.graphics import Graphic, Button, GraphicCell
from Vision.depthai_demo import main as depthai_demo


import asyncio

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
