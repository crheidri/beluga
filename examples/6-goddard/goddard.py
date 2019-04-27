"""
Goddard Rocket Problem Example.
Comparison to Goddard example in for OpenGoddard
https://github.com/istellartech/OpenGoddard/blob/master/examples/04_Goddard_0knot.py
"""

import beluga
import logging
from math import pi, sqrt
import numpy as np

import matplotlib.pyplot as plt

ocp = beluga.OCP('goddard')

# Define independent variables
ocp.independent('t', 's')

# Define quantities used in the problem
ocp.quantity('drag', '1 * d_c * v**2 * exp(-h_c * (h - h_0) / h_0)')
ocp.quantity('g', 'g_0 * (h_0 / h)**2')

# Define equations of motion
ocp.state('h', 'v', 'm') \
   .state('v', '(thrust - drag)/m - g', 'm/s') \
   .state('m', '-thrust/c', 'kg')

# Define controls
ocp.control('thrust', '1')

# Define constants' numerical values
g_0 = 1.0

h_0 = 1.0
v_0 = 0.0
m_0 = 1.0

t_c = 3.5
h_c = 500
v_c = 620
m_c = 0.6

tar_m_f = m_0 * m_c
c = 0.5 * sqrt(g_0 * h_0)
d_c = 0.5 * v_c * m_0 / g_0
thrust_max = t_c * g_0 * m_0

# Define constants
ocp.constant('g_0', g_0, '1')  # Gravity at surface

ocp.constant('t_c', t_c, '1')      # Constant for computing max thrust
ocp.constant('h_c', h_c, '1')      # Constant for height
ocp.constant('v_c', v_c, '1')      # Constant for velocity
ocp.constant('m_c', m_c, '1')      # Terminal mass fraction

ocp.constant('c', c, '1')          # Thrust to fuel ratio
ocp.constant('d_c', d_c, '1')      # Drag scaling
ocp.constant('thrust_max', thrust_max, '1')  # Max thrust

# Define constants for BCs
ocp.constant('h_0', h_0, '1')
ocp.constant('v_0', v_0, '1')
ocp.constant('m_0', m_0, '1')

ocp.constant('v_f', v_0, '1')
ocp.constant('m_f', tar_m_f, '1')

# Define smoothing constant
ocp.constant('eps', 0.01, '1')

# Define costs
ocp.terminal_cost('-h', '1')
# ocp.path_cost('-eps*cos(u)', '1')

# Define constraints
ocp.constraints() \
    .initial('h - h_0', '1') \
    .initial('v - v_0', '1') \
    .initial('m - m_0', '1') \
    .path('thrust', '1', lower=0, upper=thrust_max, activator='eps', method='epstrig') \
    .terminal('v - v_f', '1') \
    .terminal('m - m_f', '1')


ocp.scale(m=1, s=1, kg=1, rad=1, nd=1)

bvp_solver = beluga.bvp_algorithm('spbvp', algorithm='armijo', num_arcs=4)

guess_maker = beluga.guess_generator(
    'auto',
    start=[h_0, v_0, m_0],    # Starting values for states in order
    costate_guess=-0.0001,
    control_guess=[pi/3],
    time_integrate=0.1,
)

continuation_steps = beluga.init_continuation()

continuation_steps.add_step() \
    .num_cases(3) \
    .const('v_f', 0)

continuation_steps.add_step() \
    .num_cases(3, spacing='log') \
    .const('m_f', tar_m_f)

continuation_steps.add_step() \
    .num_cases(10, spacing='log') \
    .const('eps', 0.000005)

beluga.add_logger(logging_level=logging.DEBUG, display_level=logging.DEBUG)

sol_set = beluga.solve(
    ocp=ocp,
    method='indirect',
    bvp_algorithm=bvp_solver,
    steps=continuation_steps,
    guess_generator=guess_maker,
    autoscale=False,
    save='goddard.beluga',
)

# Plot Results
sol = sol_set[-1][-1]

plt.figure(1)
plt.plot(sol.t, sol.y[:, 0])
plt.xlabel('Time [s]')
plt.ylabel('Altitude [nd]')
plt.title('Altitude Profile')
plt.grid('on')

plt.figure(2)
plt.plot(sol.t, sol.y[:, 1])
plt.xlabel('Time [s]')
plt.ylabel('Velocity [nd]')
plt.title('Velocity Profile')
plt.grid('on')

plt.figure(3)
plt.plot(sol.t, sol.y[:, 2])
plt.xlabel('Time [s]')
plt.ylabel('Mass [nd]')
plt.title('Mass Profile')
plt.grid('on')

plt.figure(4)
plt.plot(sol.t, thrust_max*(np.sin(sol.u[:, 0]) + 1)/2, label='Thrust')
plt.plot(sol.t, 1 * d_c * sol.y[:, 1]**2 * np.exp(-h_c * (sol.y[:, 0] - h_0) / h_0), label='Drag')
plt.xlabel('Time [s]')
plt.ylabel('Force [nd]')
plt.title('Forces')
plt.grid('on')
plt.legend()
plt.show()

