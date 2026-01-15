import os
import time
from typing import Any, Dict, Generator, List
from xmlrpc.client import ProtocolError

import log
import settings
from iso639 import languages
from pythonopensubtitles.opensubtitles import OpenSubtitles
from pythonopensubtitles.utils import File


def _chunks(items: List[Any], n: int) -> Generator[List[Any], None, None]:
    """Yield successive n-sized chunks from items."""
    for i in range(0, len(items), n):
        yield items[i : i + n]


@log.catch_and_log_exceptions
def download_all_subtitles(filepath: str, skip: List[str] | None = None) -> None:
    if skip is None:
        skip = []
    dirname: str = os.path.dirname(filepath)
    basename: str = os.path.basename(filepath)
    basename_without_ext: str = os.path.splitext(basename)[0]
    ost: OpenSubtitles = OpenSubtitles()
    ost.login(settings.OPENSUBTITLES_USERNAME, settings.OPENSUBTITLES_PASSWORD)
    f: File = File(filepath)
    h = f.get_hash()
    language_ids: List[Any] = [
      languages.get(part1=lang).part2b for lang in settings.SUBTITLE_LANGUAGES if lang not in skip
    ]
    results_from_hash: List[Any] = (
            [
            item for sublist in
            [ost.search_subtitles([{"sublanguageid": langid, "moviehash": h}]) or [] for langid in language_ids]
            for item in sublist
        ]
    )
    languages_in_results_from_hash: List[Any] = [
        r.get("SubLanguageID") for r in results_from_hash
    ]
    results_from_filename: List[Any] = (
            [
            item for sublist in
            [ost.search_subtitles([{"sublanguageid": langid, "query": basename_without_ext}]) or [] for langid in language_ids]
            for item in sublist
        ]
    )
    results_from_filename_but_not_from_hash: List[Any] = [
        r
        for r in results_from_filename
        if r.get("SubLanguageID")
        and r.get("SubLanguageID") not in languages_in_results_from_hash
    ]
    results: List[Any] = results_from_hash + results_from_filename_but_not_from_hash
    results = [
        r
        for r in results
        if r["ISO639"] in settings.SUBTITLE_LANGUAGES
    ]
    wait_before_next_chunk = False
    sub_filenames: List[str] = []
    for chunk in _chunks(results, 10):
        sub_ids = {
            r["IDSubtitleFile"]: f'{basename_without_ext}.{r["ISO639"]}.srt'
            for r in chunk
        }
        sub_filenames = list(set(sub_filenames + list(sub_ids.values())))

        def _download_subtitle_chunk(current_sub_ids: Dict[str, str] = sub_ids, retries: int = 5) -> None:
            nonlocal ost
            if not current_sub_ids:
                return
            try:
                ost.download_subtitles(
                    list(current_sub_ids.keys()),
                    override_filenames=current_sub_ids,
                    output_directory=dirname,
                    extension="srt",
                )
            except ProtocolError as e:
                if retries == 0:
                    raise e
                time.sleep(10)
                ost = OpenSubtitles()
                ost.login(None, None)
                _download_subtitle_chunk(current_sub_ids, retries=retries - 1)

        if wait_before_next_chunk:
            time.sleep(10)
        _download_subtitle_chunk()
        wait_before_next_chunk = True

    for sub_filename in sub_filenames:
        tmp_path = os.path.join(dirname, "fixed_" + sub_filename)
        output_path = os.path.join(dirname, sub_filename)
        os.system(f"timeout 5m alass '{filepath}' '{output_path}' '{tmp_path}'")
        os.system(f"mv '{tmp_path}' '{output_path}'")


def get_subtitle_language(subtitle_filename: str) -> str | None:
    subtitle_filename = subtitle_filename.lower()
    assert subtitle_filename.endswith(".srt")
    filename_without_extension = os.path.splitext(subtitle_filename)[0]
    last_dotted_part = filename_without_extension.split(".")[-1]

    if len(last_dotted_part) == 3:
        try:
            three_letter_iso: str = filename_without_extension[-3:]
            return languages.get(part2b=three_letter_iso).part2b
        except KeyError:
            return None
    elif len(last_dotted_part) == 2:
        try:
            two_letter_iso: str = filename_without_extension[-2:]
            if two_letter_iso == "pb":
                two_letter_iso = "pt"
            return languages.get(part1=two_letter_iso).part2b
        except KeyError:
            return None

    return "en"
