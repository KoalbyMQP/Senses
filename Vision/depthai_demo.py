#!/usr/bin/env python3
import sys
import platform
from depthai_sdk.managers import ArgsManager
from depthai_helpers.supervisor import Supervisor
import signal
from utils.error_utils import component_check

args = ArgsManager.parseArgs()

@component_check("depthai_demo")
def main():
    try:
        if args.noSupervisor:
            if args.guiType == "qt":
                from runners.run_qt import runQt
                runQt()
            else:
                args.guiType = "cv"
                from runners.run_cv import runOpenCv
                runOpenCv()
        else:
            s = Supervisor()
            if args.guiType != "cv":
                available = s.checkQtAvailability()
                if args.guiType == "qt" and not available:
                    raise RuntimeError("QT backend is not available, run with --guiType cv")
                if args.guiType == "auto" and platform.machine() == "aarch64":
                    args.guiType = "cv"
                elif available:
                    args.guiType = "qt"
                else:
                    args.guiType = "cv"
            s.runDemo(args)
    except KeyboardInterrupt:
        sys.exit(0)

if __name__ == "__main__":
    main()