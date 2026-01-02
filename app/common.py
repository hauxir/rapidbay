import os
import threading
from typing import Any, Callable, Dict, List, Union

import diskcache
import settings


def threaded(fn: Callable[..., Any]) -> Callable[..., threading.Thread]:
    def wrapper(*args: Any, **kwargs: Any) -> threading.Thread:
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        thread.start()
        return thread

    return wrapper


def path_hierarchy(path: str) -> Union[Dict[str, List[Any]], List[Any], str]:
    hierarchy = os.path.basename(path)
    try:
        return {
            hierarchy: [
                path_hierarchy(os.path.join(path, contents))
                for contents in os.listdir(path)
            ]
        }
    except OSError:
        pass
    if hierarchy == "":
        return []
    return hierarchy


def normalize_filename(s: str) -> str:
    """Normalize filename to ASCII alphanumerics for matching, preserving path separators and periods."""
    return "".join(c for c in s if (c.isalnum() and c.isascii()) or c in "/\\.")


def memoize(expire: int = 300) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        cache = diskcache.Cache(settings.CACHE_DIR)

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = (args, frozenset(kwargs.items()))
            if key in cache:
                return cache[key]
            result = func(*args, **kwargs)
            if result:
                cache.set(key, result, expire=expire)
            return result

        return wrapper
    return decorator
