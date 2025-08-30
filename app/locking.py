import threading
import time
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional


class LockManager:
    locks: Dict[Any, int] = {}

    def get(self, key: Any) -> None:
        thread_id = threading.get_ident()
        while self.locks.get(key) not in [None, thread_id, None]:
            time.sleep(1)
        self.locks[key] = thread_id

    def release(self, key: Any) -> None:
        del self.locks[key]

    def is_available(self, key: Any) -> bool:
        thread_id = threading.get_ident()
        return self.locks.get(key, thread_id) == thread_id

    @contextmanager
    def lock(self, key: Any) -> Generator[None, None, None]:
        thread_id = threading.get_ident()
        if self.locks.get(key) == thread_id:
            yield
        else:
            self.get(key)
            yield
            self.release(key)
