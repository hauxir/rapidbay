import threading
from contextlib import contextmanager
from typing import Any, Dict, Generator


class LockManager:
    def __init__(self) -> None:
        self._locks: Dict[Any, threading.RLock] = {}
        self._master_lock = threading.Lock()

    def _get_lock(self, key: Any) -> threading.RLock:
        with self._master_lock:
            if key not in self._locks:
                self._locks[key] = threading.RLock()
            return self._locks[key]

    def get(self, key: Any) -> None:
        self._get_lock(key).acquire()

    def release(self, key: Any) -> None:
        lock = self._locks.get(key)
        if lock:
            lock.release()

    def is_available(self, key: Any) -> bool:
        lock = self._locks.get(key)
        if lock is None:
            return True
        # Try to acquire without blocking
        acquired = lock.acquire(blocking=False)
        if acquired:
            lock.release()
            return True
        return False

    @contextmanager
    def lock(self, key: Any) -> Generator[None, None, None]:
        lock = self._get_lock(key)
        lock.acquire()
        try:
            yield
        finally:
            lock.release()
