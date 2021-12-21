import threading
import time
from contextlib import contextmanager


class LockManager:
    locks = {}

    def get(self, key):
        """
        This function is a decorator that allows only one thread to access the
        decorated function at a time.
        """
        thread_id = threading.get_ident()
        while self.locks.get(key) not in [None, thread_id, None]:
            time.sleep(1)
        self.locks[key] = thread_id

    def release(self, key):
        del self.locks[key]

    def is_available(self, key):
        thread_id = threading.get_ident()
        return self.locks.get(key, thread_id) == thread_id

    @contextmanager
    def lock(self, key):
        """
        This function is a context manager that locks the given key in the cache.
        It raises an exception if the key is already locked by another thread.
        """
        thread_id = threading.get_ident()
        if self.locks.get(key) == thread_id:
            yield
        else:
            self.get(key)
            yield
            self.release(key)
