import dataclasses
from typing import Dict, Optional, Set, Tuple, cast

import jax
import numpy as onp
from jax import numpy as jnp
from overrides import overrides

from .. import _types as types
from .._factors import FactorBase, LinearFactor
from .._variables import RealVectorVariable, VariableBase
from ._factor_graph_base import FactorGraphBase
from ._linear_factor_graph import LinearFactorGraph


@dataclasses.dataclass(frozen=True)
class FactorGraph(FactorGraphBase[FactorBase, VariableBase]):
    """General nonlinear factor graph."""

    # Use default object hash rather than dataclass one
    __hash__ = object.__hash__

    def solve(
        self,
        initial_assignments: Optional[types.VariableAssignments] = None,
    ) -> types.VariableAssignments:

        # Define variables for local perturbations
        variable: VariableBase
        delta_variables = tuple(
            variable.local_delta_variable for variable in self.variables
        )

        # Make default initial assignments if unavailable
        if initial_assignments is None:
            initial_assignments = types.VariableAssignments.create_default(
                self.variables
            )
        assert set(initial_assignments.variables) == set(self.variables)

        # Run some Gauss-Newton iterations
        # for i in range(10):
        for i in range(10):
            print("Running GN step")
            print(
                onp.sum(
                    [
                        (f.scale_tril_inv @ f.compute_error(assignments)) ** 2
                        for f in self.factors
                    ]
                )
            )
            assignments = self._gauss_newton_step(assignments, delta_variables)

        return assignments

    @jax.partial(jax.jit, static_argnums=(0, 2))
    def _gauss_newton_step(
        self,
        assignments: types.VariableAssignments,
        delta_variables: Tuple[RealVectorVariable, ...],
    ) -> types.VariableAssignments:
        print("Linearizing....")
        # Linearize factors
        from tqdm.auto import tqdm

        linearized_factors = [
            LinearFactor.linearize_from_factor(factor, assignments)
            for factor in tqdm(self.factors)
        ]

        print("Solving...")
        # Solve for deltas
        delta_from_variable: types.VariableAssignments = (
            LinearFactorGraph().with_factors(*linearized_factors).solve()
        )

        print("Updating...")
        # Update assignments
        assignments = {
            variable: variable.add_local(
                x=value, local_delta=delta_from_variable[variable.local_delta_variable]
            )
            for variable, value in assignments.items()
        }

        print("Done!")
        return assignments
