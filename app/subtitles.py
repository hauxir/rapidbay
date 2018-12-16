import os

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
    results = ost.search_subtitles([{"sublanguageid": "all", "moviehash": h}])
    for chunk in _chunks(results, 20):
        sub_ids = {
            r["IDSubtitleFile"]: f'{basename_without_ext}.{r["SubLanguageID"]}.srt'
            for r in chunk
        }
        ost.download_subtitles(
            [_id for _id in sub_ids.keys()],
            override_filenames=sub_ids,
            output_directory=dirname,
            extension="srt",
        )


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
            return languages.get(part1=two_letter_iso).part2b
        except KeyError:
            return None
