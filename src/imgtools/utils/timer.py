import time
from typing import Any, Callable

from imgtools.logging import logger


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
        @timer("my_function")
        def my_function():
            # do something
        
        my_function()
        # Output: `my_function took 3.1244 seconds`
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            elapsed_time = end_time - start_time
            logger.info(f"{name} took {elapsed_time:.4f} seconds")
            return result

        return wrapper

    return decorator
