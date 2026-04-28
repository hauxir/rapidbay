import contextlib
import os
import urllib.request
from typing import Dict, Set

import log
from common import threaded


class HttpDownloader:
    def __init__(self) -> None:
        self.downloads: Dict[str, float] = {}
        # Output paths whose urlretrieve raised. The daemon drains this each
        # heartbeat to fail over to libtorrent for the affected file.
        self.failures: Set[str] = set()

    def clear(self, output_path: str) -> None:
        with contextlib.suppress(KeyError):
            del self.downloads[output_path]

    def download_file(self, url: str, output_path: str) -> None:
        if self.downloads.get(output_path):
            return
        self.downloads[output_path] = 0
        self._urlretrieve(url, output_path)

    @threaded
    @log.catch_and_log_exceptions
    def _urlretrieve(self, url: str, output_path: str) -> None:
        def progress(block_num: int, block_size: int, total_size: int) -> None:
            downloaded = block_num * block_size
            if downloaded < total_size:
                self.downloads[output_path] = downloaded / total_size
            else:
                self.downloads[output_path] = 1

        dirname = os.path.dirname(output_path)
        os.makedirs(dirname, exist_ok=True)
        try:
            urllib.request.urlretrieve(url, output_path, progress)
        except Exception:
            self.downloads.pop(output_path, None)
            self.failures.add(output_path)
            raise
