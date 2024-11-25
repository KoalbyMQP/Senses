from depthai_sdk import OakCamera

with OakCamera() as oak:
    color = oak.create_camera('color')
    nn = oak.create_nn('yolov8n_coco_640x352', color)
    nn.config_nn(resize_mode='stretch')
    oak.visualize([nn.out.main, nn.out.passthrough], fps=True)
    oak.start(blocking=True)