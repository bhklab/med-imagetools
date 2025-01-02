"""
This is a work in progress to break up the ops/ops.py file into smaller, more manageable pieces.
"""

from abc import ABC, abstractmethod
from typing import Any
from imgtools.io.loaders import BaseLoader
from imgtools.io.writers import BaseWriter


class BaseOp(ABC):
    """Abstract base class for operations.

    Classes inheriting from this must implement the `__call__` method.
    """

    @abstractmethod
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Perform the operation."""
        pass

    def __repr__(self) -> str:
        """
        Generate a string representation of the operation instance.

        Returns
        -------
        str
            The string representation of the object.
        """
        attrs = [(k, v) for k, v in self.__dict__.items() if not k.startswith("_")]
        attrs = [(k, f"'{v}'") if isinstance(v, str) else (k, v) for k, v in attrs]
        args = ", ".join(f"{k}={v}" for k, v in attrs)
        return f"{self.__class__.__name__}({args})"


class BaseInput(BaseOp):
    """Abstract base class for input operations.

    Parameters
    ----------
    loader : BaseLoader
        An instance of a subclass of `BaseLoader` responsible for loading input data.
    """

    _loader: BaseLoader

    def __init__(self, loader: BaseLoader):
        if not isinstance(loader, BaseLoader):
            msg = f"loader must be a subclass of io.BaseLoader, got {type(loader)}"
            raise ValueError(msg)
        self._loader = loader

    @abstractmethod
    def __call__(self, key: Any) -> Any:
        """Retrieve input data."""
        pass


class BaseOutput(BaseOp):
    """Abstract base class for output operations.

    Parameters
    ----------
    writer : BaseWriter
        An instance of a subclass of `BaseWriter` responsible for writing output data.
    """

    _writer: BaseWriter

    def __init__(self, writer: BaseWriter):
        if not isinstance(writer, BaseWriter):
            msg = f"writer must be a subclass of io.BaseWriter, got {type(writer)}"
            raise ValueError(msg)
        self._writer = writer

    @abstractmethod
    def __call__(self, key: Any, *args: Any, **kwargs: Any) -> None:
        """Write output data.

        Parameters
        ----------
        key : Any
            The identifier for the data to be written.
        *args : Any
            Positional arguments for the writing process.
        **kwargs : Any
            Keyword arguments for the writing process.
        """
        pass


if __name__ == "__main__":
    # Mock implementations
    class MockLoader(BaseLoader):
        def get(self, key: Any) -> str:
            return f"Data loaded for key: {key}"

    class MockWriter(BaseWriter):
        def put(self, key: Any, *args: Any, **kwargs: Any) -> None:
            print(f"Data written for key: {key} with args: {args} and kwargs: {kwargs}")

    # Concrete subclass of BaseInput
    class ExampleInput(BaseInput):
        def __call__(self, key: Any) -> str:
            return self._loader.get(key)

    # Concrete subclass of BaseOutput
    class ExampleOutput(BaseOutput):
        def __call__(self, key: Any, *args: Any, **kwargs: Any) -> None:
            self._writer.put(key, *args, **kwargs)

    # Demonstrating usage
    loader = MockLoader()
    writer = MockWriter(
        root_directory="example_dir",
        filename_format="example_{key}.txt",
        create_dirs=True,
    )

    example_input = ExampleInput(loader)
    example_output = ExampleOutput(writer)

    # Using ExampleInput
    key = "example_key"
    loaded_data = example_input(key)
    print("Loaded Data:", loaded_data)
    print("ExampleInput Repr:", repr(example_input))

    # Using ExampleOutput
    example_output(key, "example_data", extra_param="value")
    print("ExampleOutput Repr:", repr(example_output))
