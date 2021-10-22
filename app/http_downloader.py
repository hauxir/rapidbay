import requests
import urllib
import os
import log

from common import threaded


class HttpDownloader:
    downloads = {}

    def clear(self, output_path):
        try:
            del self.downloads[output_path]
        except KeyError:
            pass

    def download_file(self, url, output_path):
        if self.downloads.get(output_path):
            return
        self.downloads[output_path] = 0
        self._urlretrieve(url, output_path)

    @threaded
    @log.catch_and_log_exceptions
    def _urlretrieve(self, url, output_path):
        def progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if downloaded < total_size:
                self.downloads[output_path] = downloaded / total_size
            else:
                self.downloads[output_path] = 1

        dirname = os.path.dirname(output_path)
        os.makedirs(dirname, exist_ok=True)
        urllib.request.urlretrieve(url, output_path, progress)
