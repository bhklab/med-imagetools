"""
Timer context manager and decorator for debugging.
"""

import contextlib
import time
from functools import wraps
from typing import Any, Callable, Generator, TypeVar

from tqdm import tqdm

T = TypeVar("T", bound=Callable[..., Any])


@contextlib.contextmanager
def timer(
    subject: str = "Execution",
    enabled: bool = True,
    output_func: Callable[[str], None] = print,
) -> Generator[None, None, None]:
    """
    Context manager for measuring execution time.

    Parameters
    ----------
    subject : str, optional
            Label for the timer output (default is "Execution").
    enabled : bool, optional
            If False, the timer does nothing (default is True).
    output_func : Callable[[str], None], optional
            Function to output the result (default is `print`).
    """
    if enabled:
        start = time.perf_counter()
        yield
        elapsed = time.perf_counter() - start
        output_func(f"{subject} elapsed {elapsed * 1000:.2f} ms")
    else:
        yield


def timer_decorator(
    subject: str = "Execution",
    enabled: bool = True,
    repeats: int = 1,
    output_func: Callable[[str], None] = print,
) -> Callable[[T], T]:
    """
    Decorator for measuring execution time of a function.

    Parameters
    ----------
    subject : str, optional
        Label for the timer output (default is "Execution").
    enabled : bool, optional
        If False, the timer does nothing (default is True).
    repeats : int, optional
        Number of times to repeat the function call and take the average (default is 1).
    output_func : Callable[[str], None], optional
        Function to output the result (default is `print`).
    """

    def decorator(func: T) -> T:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
            if not enabled:
                return func(*args, **kwargs)

            total_time = 0.0
            result = None

            with tqdm(
                total=repeats,
                desc=f"{subject} '{func.__name__}' (avg over {repeats} runs)",
                leave=False,
                disable=repeats <= 1,
            ) as pbar:
                for _ in range(repeats):
                    start = time.perf_counter()
                    result = func(*args, **kwargs)
                    total_time += time.perf_counter() - start
                    pbar.update(1)

            avg_time = (total_time / repeats) * 1000
            output_func(
                f"{subject} avg elapsed {avg_time:.2f} ms over {repeats} runs"
            )

            return result

        return wrapper  # type: ignore

    return decorator


if __name__ == "__main__":

    @timer_decorator("My Function", enabled=True, repeats=5)
    def my_function() -> None:
        time.sleep(1)

    my_function()
