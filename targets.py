from cyberonics_py import Robot, Device, Graphic, Button, GraphicCell
from Vision.depthai_demo import main as depthai_demo


def depthai(robot: Robot):
    control_cell: 'ControlCell'  = robot.devices[0]

    def on_press():
        print("Button pressed!")

    control_cell.add_listener(on_press)
    depthai_demo()
