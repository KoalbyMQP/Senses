import numpy as np
import matplotlib.pyplot as plt
from ikpy.chain import Chain
from ikpy.utils import plot as plot_utils

left_leg_chain = Chain.from_urdf_file(
        "backend/Testing/FullAssemFin.urdf",
    base_elements=['left_shoulder1', 'left_shoulder_twist']
)

target_positions = np.array([0.1, -0.01, -0.45])

ik_solution = left_leg_chain.inverse_kinematics(target_positions)
ik_solution_2=np.array([0,0,0,0,0,0,0])
print("Joint angles:", ik_solution)

real_frame = left_leg_chain.forward_kinematics(ik_solution)

fig, ax = plot_utils.init_3d_figure()

left_leg_chain.plot(ik_solution_2, ax)

ax.set_xlim([-1, 1])
ax.set_ylim([-1, 1])
ax.set_zlim([-1, 1])

plt.show()