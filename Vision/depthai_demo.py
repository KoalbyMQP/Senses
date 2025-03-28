#!/usr/bin/env python3

"""
DepthAI Demo Application
========================

This is the main entry point for the DepthAI demo application.
It detects the GUI type (Qt or OpenCV) and launches the appropriate demo.
"""

import sys
import os
import platform
from depthai_sdk.managers import ArgsManager

def main():
    args = ArgsManager.parseArgs()
    
    # Determine which GUI type to use
    gui_type = args.guiType
    
    if gui_type == "qt":
        from runners.run_qt import runQt
        runQt()
    else:
        # Default to OpenCV interface
        from runners.run_cv import runOpenCv
        runOpenCv()

if __name__ == "__main__":
    if sys.version_info[0] < 3:
        raise Exception("Must be using Python 3")
    
    # Make sure modules are in path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.append(current_dir)
    
    # Run Jetson-specific setup if needed
    if platform.machine() == 'aarch64':  # Jetson
        os.environ['OPENBLAS_CORETYPE'] = "ARMV8"
    
    main()