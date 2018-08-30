# pylint: skip-file
# flake8: noqa


import numpy
import array
import math
import cmath

from math import pi
from numba import cuda, $precision
from numba.cuda.random import $random_gen_type$precision

from typing import MutableSequence, Sequence, Any, Tuple

$globals


@cuda.jit(device=True)
# @cuda.jit
$initialize


@cuda.jit(device=True)
# @cuda.jit
$cool


@cuda.jit(device=True)
# @cuda.jit
$generate_next


@cuda.jit(device=True)
# @cuda.jit
$evaluate


@cuda.jit(device=True)
# @cuda.jit
$acceptance_func


$empty_state


@cuda.jit
def simulated_annealing(max_steps, initial_temp, rands, states, values):
    tx = cuda.threadIdx.x
    ty = cuda.blockIdx.x
    bw = cuda.blockDim.x
    thread_id = tx + ty * bw

    if thread_id >= states.size:
        return

    step = 0
    rand_gen_idx = 0
    random_values = cuda.local.array($dim, dtype=$precision)
    while(rand_gen_idx < $dim):
        random_values[rand_gen_idx] = $random_gen_type$precision(rands, thread_id)
        rand_gen_idx += 1
    rand_gen_idx = 0

    state = states[thread_id]
    initialize(state, random_values)
    energy = evaluate(state)

    temperature = initial_temp
    while(step < max_steps and temperature > 0):
        while(rand_gen_idx < $dim):
            random_values[rand_gen_idx] = $random_gen_type$precision(rands, thread_id)
            rand_gen_idx += 1
        rand_gen_idx = 0

        new_state = numpy.copy(state)
        generate_next(state, new_state, random_values)
        new_energy = evaluate(new_state)
        if acceptance_func(energy, new_energy, temperature):
            state = new_state
            energy = new_energy

        temperature = cool(initial_temp, temperature, step)
        step += 1

    states[thread_id] = state
    values[thread_id] = energy
    cuda.syncthreads()