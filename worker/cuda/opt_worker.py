# pylint: disable=E1101

import sys
import traceback
import numpy as np
import uuid

from numba.cuda.random import create_xoroshiro128p_states
from pyhocon import ConfigTree
from typing import Dict, Any, Tuple, Type, NamedTuple

from .modulegenerator import ModuleGenerator


class OptResult(NamedTuple):
    values: np.ndarray
    states: np.ndarray
    failure: Tuple[Type[Exception], Exception, str]

# TODO: add this to the model documentation
# Numba(like cuRAND) uses the Box - Muller transform 
# <https://en.wikipedia.org/wiki/Box%E2%80%93Muller_transform> to generate 
# normally distributed random numbers from a uniform generator. However,
# Box - Muller generates pairs of random numbers, and the current implementation
# only returns one of them. As a result, generating normally distributed values
# is half the speed of uniformly distributed values.


class OptimizationWorker():

    def __init__(self, conf: ConfigTree) -> None:
        self.conf = conf['optimization']
        self.gen = ModuleGenerator(template_file=conf['cuda.template_path'])
        self.opt_configuration = None
        self.opt_module = None
        self.id = str(uuid.uuid4())


    def compile_model(self, model: Dict[str, Any]):
        self.opt_configuration = self._extract_opt_configuration(model)
        self.opt_module = self.gen.cuda_module(self.opt_configuration)

    async def run(self, opt_params):
        try:
            assert self.opt_module is not None

            dimensions: int = int(self.opt_configuration['dim'])
            precision = np.float64 if self.opt_configuration['precision'] == 'float64' else np.float32
            rng_states = create_xoroshiro128p_states(dimensions, seed=1)

            values = np.array([0.0] * dimensions, dtype=precision)
            states = np.array([self.opt_module.state_shape()] *
                              dimensions, dtype=precision)

            max_steps = opt_params.get(
                'max_steps', self.conf['defaults.max_steps'])
            initial_temp = opt_params.get(
                'initial_temp', self.conf['defaults.initial_temp'])
            blocks_per_grid = opt_params.get(
                'blocks_per_grid', self.conf['defaults.blocks_per_grid'])
            grids_per_block = opt_params.get(
                'grids_per_block', self.conf['defaults.grids_per_block'])

            self.opt_module.simulated_annealing[blocks_per_grid, grids_per_block](
                max_steps, initial_temp, rng_states, states)
            
            return OptResult(values, states, None)
        except:
            type_, value_, traceback_ = sys.exc_info()
            return OptResult(None, None, (type_, value_, traceback.format_tb(traceback_)))

    def _extract_opt_configuration(self, model: Dict[str, Any]) -> Dict[str, str]:
        opt_configuration = {}

        random_distribution = model['distribution']

        if random_distribution == 'uniform':
            opt_configuration['random_gen_type'] = 'xoroshiro128p_uniform_'
        elif random_distribution == 'normal':
            opt_configuration['random_gen_type'] = 'xoroshiro128p_normal_'
        else:
            raise AssertionError('Unknown random distribution type: ' + random_distribution)

        opt_configuration['precision'] = model['precision']
        opt_configuration['dim'] = str(model['dimensions'])
        opt_configuration['globals'] = model['globals']
        opt_configuration['cool'] = model['functions']['cool']
        opt_configuration['initialize'] = model['functions']['initialize']
        opt_configuration['generate_next'] = model['functions']['generate_next']
        opt_configuration['evaluate'] = model['functions']['evaluate']
        opt_configuration['acceptance_func'] = model['functions']['acceptance_func']
        opt_configuration['state_shape'] = model['functions']['state_shape']

        return opt_configuration
        