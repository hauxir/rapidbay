import requests
import urllib.request
import os
from typing import Dict, Optional
import log

from common import threaded


class HttpDownloader:
    downloads: Dict[str, float] = {}

    def clear(self, output_path: str) -> None:
        try:
            del self.downloads[output_path]
        except KeyError:
            pass

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
        urllib.request.urlretrieve(url, output_path, progress)
