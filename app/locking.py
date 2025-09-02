import threading
from contextlib import contextmanager
from typing import Any, Dict, Generator


class LockManager:
    locks: Dict[Any, threading.RLock] = {}
    _lock_creation_lock: threading.Lock = threading.Lock()

    def get(self, key: Any) -> None:
        with self._lock_creation_lock:
            if key not in self.locks:
                self.locks[key] = threading.RLock()
        self.locks[key].acquire()

    def release(self, key: Any) -> None:
        if key in self.locks:
            self.locks[key].release()

    def is_available(self, key: Any) -> bool:
        with self._lock_creation_lock:
            if key not in self.locks:
                return True
        lock = self.locks[key]
        if lock.acquire(blocking=False):
            lock.release()
            return True
        return False

    @contextmanager
    def lock(self, key: Any) -> Generator[None, None, None]:
        self.get(key)
        try:
            yield
        finally:
            self.release(key)
