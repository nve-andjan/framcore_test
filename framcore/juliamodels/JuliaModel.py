"""Manage Julia environment and usage of juliacall."""

import importlib
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from framcore import Base

os.environ["JULIA_SSL_CA_ROOTS_PATH"] = ""
os.environ["SSL_CERT_FILE"] = ""


def _is_url(url_string: str) -> bool:
    """
    Check if a string is a valid url.

    Args:
        url_string (str): Strong to be validated.

    Returns:
        bool: True if valid as a url, False if invalid.

    """
    try:
        result = urlparse(url_string)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


class JuliaModel(Base):
    """Class for running julia code with juliacall."""

    ENV_NAME: str = "julia_env"  # Used to let each model define their own project/environment to avoid overwriting.
    _jl = None

    def __init__(
        self,
        env_path: Path | str | None = None,
        depot_path: Path | str | None = None,
        julia_path: Path | str | None = None,
        dependencies: list[str | tuple[str, str | None]] | None = None,
        skip_install_dependencies: bool = False,
    ) -> None:
        """
        Initialize management of Julia model, environment and dependencies.

        The three parameters env_path, depot_path and julia_path sets environment variables for locations of your Julia
        environment, packages and language.
            - If user has not specified locations, the default is to use the current python/conda environment.
            - If a system installation of Python is used, the default is set to the current user location.

        Args:
            env_path (Path | str | None, optional): Path to location of Julia environment. If it doesnt exist it will be
                                                    created. Defaults to None.
            depot_path (Path | str | None, optional): Path to location where JuliaCall shoult install package
                                                      dependencies. Defaults to None.
            julia_path (Path | str | None, optional): Path to Julia language location. Will be installed here if it
                                                      doesnt exist. Defaults to None.
            dependencies (list[str] | None, optional): List of dependencies of the model. The strings in the list can be
                                                       either urls or Julia package names.. Defaults to None.

        """
        self._check_type(env_path, (Path, str, type(None)))
        self._check_type(depot_path, (Path, str, type(None)))
        self._check_type(julia_path, (Path, str, type(None)))
        self._check_type(dependencies, (list, str, type(None)))
        self._check_type(skip_install_dependencies, bool)

        self._env_path = env_path
        self._depot_path = depot_path
        self._julia_path = julia_path
        self._dependencies = dependencies if dependencies else []
        self._skip_install_dependencies = skip_install_dependencies

        self._jlpkg = None
        self._initialize_julia()

    def _initialize_julia(self) -> None:
        """Initialize Julia language, package depot, and environment with JuliaCall."""
        if self._jl is not None:
            return

        # figure out what kind of environment we are in
        prefix = sys.prefix if sys.prefix != sys.base_prefix else os.getenv("CONDA_PREFIX")
        # we have python system installation
        project = Path("~/.julia").expanduser() if prefix is None else prefix

        self._env_path = str(Path(project) / "julia_envs" / self.ENV_NAME) if not self._env_path else str(self._env_path)
        self._depot_path = str(Path(project) / "julia_pkgs") if not self._depot_path else str(self._depot_path)

        os.environ["PYTHON_JULIAPKG_PROJECT"] = self._env_path
        os.environ["JULIA_DEPOT_PATH"] = self._depot_path
        if self._julia_path:  # If Julia path is not set, let JuliaCall handle defaults.
            os.environ["PYTHON_JULIAPKG_EXE"] = str(self._julia_path)

        juliacall = importlib.import_module("juliacall")
        JuliaModel._jl = juliacall.Main
        self._jlpkg = juliacall.Pkg

        self._jlpkg.activate(str(self._env_path))

        if not self._skip_install_dependencies:
            self._install_dependencies()

        # Print sysimage Julia
        try:
            path_sysimage = self._jl.seval("unsafe_string(Base.JLOptions().image_file)")
            message = f"path_sysimage: {path_sysimage}"
            self.send_debug_event(message)
        except Exception:
            pass

    def _install_dependencies(self) -> None:
        """Install dependencies."""
        # if (Path(self._env_path) / Path("Manifest.toml")).exists():
        #    print("Manifest found, assuming environment is already initialized.")
        #    return

        url_tuples = [p for p in self._dependencies if isinstance(p, tuple) and _is_url(p[0])]
        urls = [p for p in self._dependencies if isinstance(p, str) and _is_url(p)]
        dev_paths = [p for p in self._dependencies if isinstance(p, str) and Path(p).exists()]
        pkg_names = [p for p in self._dependencies if isinstance(p, str) and not _is_url(p) and not Path(p).exists()]

        unknowns = [p for p in self._dependencies if not (p in url_tuples or p in urls or p in pkg_names or p in dev_paths)]

        if unknowns:
            messages = []
            for p in unknowns:
                messages.append(
                    (
                        f"Unsupported julia package definition: '{p}' of type '{type(p)}' is not supported. "
                        "Must be defined as either str or tuple[str, str | None]"
                    ),
                )
            message = "\n".join(messages)
            raise ValueError(message)

        self._jl.seval("using Pkg")

        pkg_spec_vector = self._jl.seval("x = Pkg.PackageSpec[]")

        for url, rev in url_tuples:
            self._jl.seval(f'push!(x, Pkg.PackageSpec(url="{url}", rev="{rev}"))')

        for url in urls:
            self._jl.seval(f'push!(x, Pkg.PackageSpec(url="{url}))"')

        for pkg_name in pkg_names:
            self._jl.seval(f'push!(x, Pkg.PackageSpec(name="{pkg_name}"))')

        self._jlpkg.add(pkg_spec_vector)

        for dev_path in dev_paths:
            self._jl.seval(f'Pkg.develop(path="{dev_path}")')

    def _run(self, julia_code: str) -> None:
        """Run a string of julia code wich is supposed to start running the Julia Model in the given environment."""
        self._jl.seval(julia_code)
