import contextlib
import os
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional, Union

import diskcache

# Separate pools for different task types to prevent deadlocks
_download_pool = ThreadPoolExecutor(max_workers=200, thread_name_prefix="rapidbay-download")
_conversion_pool = ThreadPoolExecutor(max_workers=20, thread_name_prefix="rapidbay-convert")  
_general_pool = ThreadPoolExecutor(max_workers=50, thread_name_prefix="rapidbay-general")


class ThreadProxy:
    """Proxy that makes a Future behave like a Thread for backward compatibility."""

    def __init__(self, future: Future[Any]):
        self._future = future

    def join(self, timeout: Optional[float] = None) -> None:
        """Emulate Thread.join() - wait for completion but don't propagate exceptions."""
        with contextlib.suppress(Exception):
            # Thread.join() doesn't raise exceptions from the worker thread
            self._future.result(timeout=timeout)

    def is_alive(self) -> bool:
        """Emulate Thread.is_alive() - check if task is still running."""
        return not self._future.done()


def threaded(fn: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator that routes functions to appropriate thread pools based on function type.
    
    - Download functions: Large pool (200 workers) for I/O-bound tasks
    - Conversion functions: Small pool (20 workers) for CPU-bound tasks  
    - General functions: Medium pool (50 workers) for everything else
    
    This prevents pool starvation from nested calls and handles high load scenarios.
    """
    def wrapper(*args: Any, **kwargs: Any) -> ThreadProxy:
        # Route to appropriate pool based on function characteristics
        if any(name in fn.__name__.lower() for name in ['download', 'fetch', 'retrieve']):
            # I/O-bound download tasks - can handle many concurrent operations
            future = _download_pool.submit(fn, *args, **kwargs)
        elif any(name in fn.__name__.lower() for name in ['convert', 'encode', 'process']):
            # CPU-bound conversion tasks - limit to prevent system overload
            future = _conversion_pool.submit(fn, *args, **kwargs)
        else:
            # General tasks
            future = _general_pool.submit(fn, *args, **kwargs)
            
        return ThreadProxy(future)

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
