import traceback
from typing import Any, Callable, Optional, TypeVar

import settings

F = TypeVar('F', bound=Callable[..., Any])


def debug(msg: str) -> None:
    with open(settings.LOGFILE, "a+") as f:
        f.write(msg + "\n")


def write_log() -> None:
    with open(settings.LOGFILE, "a+") as f:
        f.write(traceback.format_exc() + "\n")


def catch_and_log_exceptions(fn: F) -> Callable[..., Optional[Any]]:
    def wrapper(*args: Any, **kwargs: Any) -> Optional[Any]:
        try:
            return fn(*args, **kwargs)
        except Exception:
            write_log()
            return None

    return wrapper
