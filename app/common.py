import os
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Union

import diskcache

# Global thread pool with reasonable limits
# Max 20 threads to prevent resource exhaustion
_thread_pool = ThreadPoolExecutor(max_workers=20, thread_name_prefix="rapidbay")


def threaded(fn: Callable[..., Any]) -> Callable[..., Future[Any]]:
    def wrapper(*args: Any, **kwargs: Any) -> Future[Any]:
        # Submit to thread pool instead of creating unlimited threads
        # Returns a Future that behaves similarly to Thread for compatibility
        return _thread_pool.submit(fn, *args, **kwargs)

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


def memoize(expire: int = 300) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        cache = diskcache.Cache("/tmp/cache/")

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
