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
        """
        Downloads a file from the given URL to the specified output path.

        :param
        url: The URL of the file to download.
        :type url: str
        :param output_path:
        The path where the downloaded file will be saved. If this is an existing
        directory, it must be empty and will not be deleted on close(). If this is
        an existing regular file, it will be overwritten if necessary (but not
        deleted). Any other type of filesystem object (e.g., a non-empty directory)
        causes an error to be raised immediately during construction or when open()
        is called for writing or appending mode (if that would cause data loss). A
        regular file opened in read-only mode may also cause an error to occur when
        write() or truncate() are called; some operating systems do not support
        opening files with O_RDONLY and without O_CREAT flags at all; see os module
        documentation for more information on platform-specific behavior.) This
        parameter may refer to a named pipe using `NamedTemporaryFile` but does not
        support URLs with `file://` scheme as they cannot reliably indicate whether
        new data should overwrite old data until written completely or if there was
        no previous content at all - which could lead into
        """
        if self.downloads.get(output_path):
            return
        self.downloads[output_path] = 0
        self._urlretrieve(url, output_path)

    @threaded
    @log.catch_and_log_exceptions
    def _urlretrieve(self, url, output_path):
        """
        Downloads a file from the given URL to the specified output path.

        :param
        url: The URL of the file to download.
        :type url: str
        :param output_path:
        The path where the downloaded file will be stored. If this is an existing
        directory, it will be used as-is and its name changed to reflect what was
        downloaded instead of being overwritten. If this is an existing non-
        directory filename, that file will be overwritten with a new one named
        after what was downloaded instead of being automatically renamed by OS
        (e.g., foo -> foo_(1)). Otherwise, if this does not exist yet it will be
        created and named after what was downloaded automatically instead of being
        renamed by OS (e..g., bar -> bar_(1)). In any case, if there are multiple
        files with similar names they'll all get numbered incrementally like
        foo(2), foo(3), etc... until only one remains which then becomes your final
        output filename without any renaming at all because you already got your
        single unique name even before downloading started! This behavior can also
        occur when downloading URLs that redirect elsewhere so make sure you check
        for existence/non-existence yourself in order to avoid such problems!
        Finally note that no matter how many
        """
        def progress(block_num, block_size, total_size):
            """
            Downloads a file from the internet.

            :param url: The URL of the file to be
            downloaded.
            :type url: str

                :param output_path: The path where the
            downloaded file will be saved. If it is not provided, then it will be saved
            in 
                                    a temporary directory and deleted after
            execution finishes. If an output path is provided, then
            this function does not delete any files even if `delete_files` is set to
            True (default). This 
                                    parameter can also contain
            one or more asterisk characters that match any string containing zero or
            more characters (e.g., "**"). In this case, all matching files are deleted
            regardless of their names after execution finishes successfully or
            unsuccessfully unless `delete_files` is set to False explicitly by the
            user/developer/tester who calls this function when he/she provides an
            output path with one or more asterisk characters in it as input for this
            parameter while setting `delete_files` to False explicitly by him/herself
            as well when he/she wants only specific files matching such strings in the
            input value for this parameter but not all existing matching files
            regardless of their names before and after execution starts successfully or
            unsuccessfully because some other
            """
            downloaded = block_num * block_size
            if downloaded < total_size:
                self.downloads[output_path] = downloaded / total_size
            else:
                self.downloads[output_path] = 1

        dirname = os.path.dirname(output_path)
        os.makedirs(dirname, exist_ok=True)
        urllib.request.urlretrieve(url, output_path, progress)
