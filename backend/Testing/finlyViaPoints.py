"""
FOR DESIGN TEAM

This file is to log the via points of the trajectories for the demo in effort to clean up the main code.
Angles are in radians and can be calculated using the MATLAB scripts found in backend>KoalbyHumanoid>MATLAB Scripts.

Format of each list goes as follows:
    [0]: list of t_f for each via point
    [1]: list of joint angles (rad)
    [2]: list of joint velocities through each via_point (v_f)
    [3]: list of joint accelerations through each via point (a_f)
"""
"""
leftArmTraj = [
    [[0,0,0,0,0,0], [8,8,8,8,8,8]],
    [[ 0,  0, 0, 0,  0,  0] ,
     [0, -1.78570351, -2.43228545,  1.18197416,
 -2.60911091,  0]],
    [[0,0,0,0,0,0],  [0,0,0,0,0,0]],
    [[0,0,0,0,0,0], [0,0,0,0,0,0]]
]
"""
leftArmTraj = [
    [[0,0,0], [20,20,20]],
    [[0.384131,  -0.04549,  0.74864],
     [0.3,  -0.1549,  .74864]],
    [[0,0,0], [0,0,0]],
    [[0,0,0], [0,0,0]]
]