"""Definition of Solver interface."""

import pickle
from abc import ABC, abstractmethod
from copy import deepcopy
from pathlib import Path

from framcore import Base, Model
from framcore.solvers import SolverConfig


class Solver(Base, ABC):
    """Solver inteface class."""

    _FILENAME_MODEL = "model.pickle"
    _FILENAME_SOLVER = "solver.pickle"

    def solve(self, model: Model) -> None:
        """Solve the models. Use folder to write results."""
        self._check_type(model, Model)

        config = self.get_config()

        folder = config.get_solve_folder()

        assert folder is not None, "use Solver.get_config().set_solve_folder(folder)"

        Path.mkdir(folder, parents=True, exist_ok=True)

        self._solve(folder, model)

        with Path.open(folder / self._FILENAME_MODEL, "wb") as f:
            pickle.dump(model, f)

        c = deepcopy(self)
        c.get_config().set_solve_folder(None)
        with Path.open(folder / self._FILENAME_SOLVER, "wb") as f:
            pickle.dump(c, f)

    @abstractmethod
    def get_config(self) -> SolverConfig:
        """Return the solver's config object."""
        pass

    @abstractmethod
    def _solve(self, folder: Path, model: Model) -> None:
        """Solve the model inplace. Write to folder."""
        pass
