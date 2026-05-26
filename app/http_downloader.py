import contextlib
import os
import time
import urllib.request
from typing import Dict, Set, Tuple

import log
from common import threaded


class HttpDownloader:
    def __init__(self) -> None:
        self.downloads: Dict[str, float] = {}
        self.download_rates: Dict[str, int] = {}
        self._rate_samples: Dict[str, Tuple[float, int]] = {}
        # Output paths whose urlretrieve raised. The daemon drains this each
        # heartbeat to fail over to libtorrent for the affected file.
        self.failures: Set[str] = set()

    def clear(self, output_path: str) -> None:
        with contextlib.suppress(KeyError):
            del self.downloads[output_path]
        self.download_rates.pop(output_path, None)
        self._rate_samples.pop(output_path, None)

    def download_file(self, url: str, output_path: str) -> None:
        if self.downloads.get(output_path):
            return
        self.downloads[output_path] = 0
        self._rate_samples[output_path] = (time.monotonic(), 0)
        self._urlretrieve(url, output_path)

    @threaded
    @log.catch_and_log_exceptions
    def _urlretrieve(self, url: str, output_path: str) -> None:
        def progress(block_num: int, block_size: int, total_size: int) -> None:
            downloaded = block_num * block_size
            now = time.monotonic()
            last_time, last_bytes = self._rate_samples.get(output_path, (now, downloaded))
            elapsed = now - last_time
            if elapsed >= 0.5:
                self.download_rates[output_path] = max(0, int((downloaded - last_bytes) / elapsed))
                self._rate_samples[output_path] = (now, downloaded)
            if downloaded < total_size:
                self.downloads[output_path] = downloaded / total_size
            else:
                self.downloads[output_path] = 1
                self.download_rates[output_path] = 0

        dirname = os.path.dirname(output_path)
        os.makedirs(dirname, exist_ok=True)
        try:
            urllib.request.urlretrieve(url, output_path, progress)
        except Exception:
            self.downloads.pop(output_path, None)
            self.download_rates.pop(output_path, None)
            self._rate_samples.pop(output_path, None)
            self.failures.add(output_path)
            raise
