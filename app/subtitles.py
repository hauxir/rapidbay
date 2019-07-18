import os
import time
from xmlrpc.client import ProtocolError

import log
from iso639 import languages
from pythonopensubtitles.opensubtitles import OpenSubtitles
from pythonopensubtitles.utils import File


def _chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i : i + n]


@log.catch_and_log_exceptions
def download_all_subtitles(filepath):
    dirname = os.path.dirname(filepath)
    basename = os.path.basename(filepath)
    basename_without_ext = os.path.splitext(basename)[0]
    ost = OpenSubtitles()
    ost.login(None, None)
    f = File(filepath)
    h = f.get_hash()
    results_from_hash = (
        ost.search_subtitles([{"sublanguageid": "all", "moviehash": h}]) or []
    )
    languages_in_results_from_hash = [
        lang_id for lang_id in [r.get("SubLanguageID") for r in results_from_hash]
    ]
    results_from_filename = [
        r
        for r in ost.search_subtitles(
            [{"sublanguageid": "all", "query": basename_without_ext}]
        )
    ]
    results_from_filename_but_not_from_hash = [
        r
        for r in results_from_filename
        if r.get("SubLanguageID")
        and r.get("SubLanguageID") not in languages_in_results_from_hash
    ]
    results = results_from_hash + results_from_filename_but_not_from_hash
    wait_before_next_chunk = False
    for chunk in _chunks(results, 10):
        sub_ids = {
            r["IDSubtitleFile"]: f'{basename_without_ext}.{r["ISO639"]}.srt'
            for r in chunk
        }

        def _download_subtitle_chunk(retries=5):
            nonlocal ost
            try:
                ost.download_subtitles(
                    [_id for _id in sub_ids.keys()],
                    override_filenames=sub_ids,
                    output_directory=dirname,
                    extension="srt",
                )
            except ProtocolError as e:
                if retries == 0:
                    raise e
                time.sleep(10)
                ost = OpenSubtitles()
                ost.login(None, None)
                _download_subtitle_chunk(retries=retries - 1)

        if wait_before_next_chunk:
            time.sleep(10)
        _download_subtitle_chunk()
        wait_before_next_chunk = True


def get_subtitle_language(subtitle_filename):
    subtitle_filename = subtitle_filename.lower()
    assert subtitle_filename.endswith(".srt")
    filename_without_extension = os.path.splitext(subtitle_filename)[0]
    try:
        three_letter_iso = filename_without_extension[-3:]
        return languages.get(part2b=three_letter_iso).part2b
    except KeyError:
        try:
            two_letter_iso = filename_without_extension[-2:]
            if two_letter_iso == "pb":
                two_letter_iso = "pt"
            return languages.get(part1=two_letter_iso).part2b
        except KeyError:
            return None
