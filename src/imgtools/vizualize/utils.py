import os
from enum import Enum


class EnvironmentType(str, Enum):
    """
    Enumeration of different Python execution environments.

    Attributes
    ----------
    JUPYTER_NOTEBOOK : str
        Jupyter Notebook or Jupyter Lab.
    JUPYTER_QTCONSOLE : str
        Jupyter QtConsole.
    GOOGLE_COLAB : str
        Google Colaboratory (Cloud-based Jupyter).
    VSCODE_NOTEBOOK : str
        Jupyter Kernel running inside VSCode.
    IPYTHON_TERMINAL : str
        IPython interactive shell in a terminal.
    STANDARD_PYTHON : str
        Standard Python interpreter (script or REPL).
    """

    JUPYTER_NOTEBOOK = "jupyter-notebook"
    JUPYTER_QTCONSOLE = "jupyter-qtconsole"
    GOOGLE_COLAB = "google-colab"
    VSCODE_NOTEBOOK = "vscode-notebook"
    IPYTHON_TERMINAL = "ipython-terminal"
    STANDARD_PYTHON = "standard-python"

    @classmethod
    def detect(cls) -> "EnvironmentType":
        """
        Detect the current Python execution environment.

        Returns
        -------
        EnvironmentType
            The detected environment type.
        """
        try:
            from IPython import get_ipython

            shell = get_ipython().__class__.__name__

            if "COLAB_GPU" in os.environ:
                return cls.GOOGLE_COLAB
            if "VSCODE_PID" in os.environ:
                return cls.VSCODE_NOTEBOOK
            if shell == "ZMQInteractiveShell":
                return cls.JUPYTER_NOTEBOOK  # QtConsole also uses this
            if shell == "TerminalInteractiveShell":
                return cls.IPYTHON_TERMINAL
        except (ImportError, AttributeError):
            pass

        return cls.STANDARD_PYTHON  # Default to standard Python


# Example usage
if __name__ == "__main__":  # pragma: no cover
    env = EnvironmentType.detect()
    print(f"Detected environment: {env}")  # noqa
