from __future__ import annotations

import time
from functools import wraps
from typing import Any, Callable

from imgtools.loggers import logger

__all__ = ["timer", "timed_context", "TimerContext"]


def timer(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to measure the execution time of a function and log it with a custom name.

    Parameters
    ----------
        name (str): The custom name to use in the log message.

    Returns
    -------
        Callable[[Callable[..., Any]], Callable[..., Any]]:
        A decorator that wraps the function to measure its execution time.

    Example
    -------
        @timer("My Function")
        def my_function():
            # do something

        my_function()
        # Output: `My Function took 3.1244 seconds`
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa
            with TimerContext(name):
                result = func(*args, **kwargs)
            return result

        return wrapper

    return decorator


class TimerContext:
    start_time: float

    def __init__(self, name: str) -> None:
        self.name = name

    def __enter__(self) -> TimerContext:
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: ANN001
        logger.info(
            f"{self.name} took {time.time() - self.start_time:.4f} seconds"
        )


def timed_context(name: str) -> TimerContext:
    """
    Context manager to measure the execution time of a block of code and log it with a custom name.

    Parameters
    ----------
        name (str): The custom name to use in the log message.

    Returns
    -------
        TimerContext:
        A context manager that measures the execution time of a block of code.

    Example
    -------
        with timed_context("My Block"):
            # do something

        # Output: `My Block took 3.1244 seconds`
    """
    return TimerContext(name)
