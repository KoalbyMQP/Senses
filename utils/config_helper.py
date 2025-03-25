from pathlib import Path
from depthai_sdk.managers import ArgsManager
from depthai_helpers.config_manager import ConfigManager, DEPTHAI_VIDEOS
from depthai_sdk import downloadYTVideo

def prepareConfManager(in_args):
    confManager = ConfigManager(in_args)
    confManager.linuxCheckApplyUsbRules()
    if not confManager.useCamera:
        video = str(confManager.args.video)
        if video.startswith('https'):
            confManager.args.video = str(downloadYTVideo(video, DEPTHAI_VIDEOS))
            print("Youtube video downloaded.")
        if not Path(confManager.args.video).exists():
            raise ValueError("Path {} does not exists!".format(confManager.args.video))
    return confManager