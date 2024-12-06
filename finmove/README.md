# RaspberryPi-Code_23-24
## Raspberry Pi Side of Koalby/Ava

### Install and Use
1. Download and install the latest versions of CoppeliaSim, Git, and Python for your OS
    1. CoppeliaSim: https://coppeliarobotics.com/
    2. Git: https://git-scm.com/downloads/
    3. Python: https://www.python.org/downloads/
2. Clone this GitHub repository
    1. https://github.com/KoalbyMQP/RaspberryPi-Code_23-24
3. Switch to the dev branch of this repository
4. Install all Python packages in requirements.txt found in the root folder of this repository
    1. pip install -r requirements.txt
5. Open CoppeliaSim
    1. For Ubuntu and macOS, you may have to open CoppeliaSim through terminal if not working
6. Open wanted scene in CoppeliaSim
    1. Our scenes are located at RaspberryPi-Code_23-24/backend/KoalbyHumanoid/Simulation Files
    2. In CoppeliaSim: File → Open scene... → (select the scene file) → Open
7. Run the Python script corresponding to what you want to happen in the scene
    1. Our demo scripts are located at RaspberryPi-Code_23-24/backend/Demo Scripts
    2. Make sure to run any scripts locally and from the root folder of this repository

### Programs
- KoalbyHumanoid
  - Simulation Files
    - Finly_Updated_URDF.ttt - CoppeliaSim model of Finley
    - gyro.lua - code for gyroscope sensor in CoppeliaSim
  - Config.py: Robot configuration (links and motors)
  - Motor.py: RealMotor and SimMotor classes to get/set motor positions
  - PID.py: PID class to calculate output based on error
  - Plotter.py: plots points in 3D space using matplotlib
  - poe.py: Product-of-Exponentials code (https://en.wikipedia.org/wiki/Product_of_exponentials_formula)
  - Robot.py: RealRobot and SimRobot classes to control the entire robot
  - trajPlanner.py: Basic Trajectory Planner (like from RBE 3001)
- Simulation
  - sim.py: python API to CoppeliaSim
  - simConst.py: CoppeliaSim constants
  - simpleTest.py: Simple script to test connection between python and CoppeliaSim (current non-functional)
- Testing: various test scripts
  - initRobot: initializes a RealRobot object
  - initSim: initalizes the simulation (connects python to CoppeliaSim)
  - simMotionTest: testing balancing while standing and bending over
  - trajplannertest: tests the trajPlanner class in the KoalbyHumanoid package

## Branches (Update as new branches are made)
### main
Ready to deploy for good production codebase on Ava's Raspberry Pi
### dev
Ready to test development codebase on Ava's Raspberry Pi
### sim
Simulation development codebase
