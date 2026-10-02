from unittest.mock import patch

import pytest

from app.title_parser import parse_title


def test_standard_tv_episode():
    assert parse_title("Better.Call.Saul.S03E06.1080p.BluRay.x265-RARBG") == {
        "title": "Better Call Saul",
        "season": 3,
        "episode": 6,
        "year": None,
    }


def test_movie_with_year():
    assert parse_title("The.Matrix.1999.2160p.UHD.BluRay.x265-RARBG") == {
        "title": "The Matrix",
        "season": None,
        "episode": None,
        "year": 1999,
    }


def test_movie_without_year():
    with patch("app.title_parser.PTN.parse", return_value={"title": "The Matrix"}):
        assert parse_title("The.Matrix.2160p.BluRay") == {
            "title": "The Matrix",
            "season": None,
            "episode": None,
            "year": None,
        }


def test_episode_with_season_code_in_title():
    with patch("app.title_parser.PTN.parse", return_value={"title": "Example Show"}):
        assert parse_title("Example.Show.S02E03") == {
            "title": "Example Show",
            "season": 2,
            "episode": 3,
            "year": None,
        }


def test_anime_release_group():
    parsed = parse_title("[SubsPlease] Spy x Family - 05 (1080p) [A1B2C3D4].mkv")
    assert parsed["title"]
    assert parsed["episode"] == 5


def test_dots_and_underscores_are_cleaned():
    with patch("app.title_parser.PTN.parse", return_value={"title": "  Some__Show.Name  "}):
        assert parse_title("Some__Show.Name.S01E02")["title"] == "Some Show Name"


def test_trailing_junk_is_not_part_of_ptn_title():
    assert parse_title("Better.Call.Saul.S03E06.1080p.BluRay.x265-RARBG")["title"] == "Better Call Saul"


def test_empty_title_raises_value_error():
    with pytest.raises(ValueError):
        parse_title("")


def test_whitespace_only_title_raises_value_error():
    with pytest.raises(ValueError):
        parse_title(" \t\n ")


def test_ptn_type_error_returns_empty_dict():
    with patch("app.title_parser.PTN.parse", side_effect=TypeError):
        assert parse_title("unparseable title") == {}


def test_season_without_ptn_episode_uses_supplementary_episode():
    with patch("app.title_parser.PTN.parse", return_value={"title": "Example Show", "season": 4}):
        assert parse_title("Example.Show.S04E09") == {
            "title": "Example Show",
            "season": 4,
            "episode": 9,
            "year": None,
        }


def test_very_long_title():
    long_name = "A Very Long Example Series Name With Many Words"
    with patch("app.title_parser.PTN.parse", return_value={"title": long_name, "season": 1, "episode": 2}):
        assert parse_title(f"{long_name}.S01E02.1080p.WEB-DL")["title"] == long_name


def test_parenthetical_year_is_kept_when_ptn_drops_it():
    parsed = parse_title("Dune (2021) [1080p] [WEBRip]")
    assert parsed["title"] == "Dune"
    assert parsed["year"] == 2021


def test_older_parenthetical_year_stays_distinct():
    parsed = parse_title("Dune (1984) 1080p BrRip x264 -YIFY")
    assert parsed["title"] == "Dune"
    assert parsed["year"] == 1984


def test_dotted_2020s_year_is_split_out_of_the_title():
    dune = parse_title("Dune.2021.1080p.BluRay.REMUX.AVC.DTS-HD.MA.TrueHD.7.1.Atmos-FGT")
    assert dune["title"] == "Dune"
    assert dune["year"] == 2021

    part_two = parse_title("Dune.Part.Two.2024.2160p.WEB-DL.DDP5.1.Atmos.H.265-FLUX")
    assert part_two["title"] == "Dune Part Two"
    assert part_two["year"] == 2024

    with_uhd = parse_title("Dune.Part.Two.2024.UHD.BluRay.2160p.TrueHD.Atmos-FraMeSToR")
    assert with_uhd["title"] == "Dune Part Two"
    assert with_uhd["year"] == 2024


def test_release_tags_after_the_year_are_not_part_of_the_title():
    nordic = parse_title("Dune Part Two 2024 NORDiC 1080p REMUX BluRay AVC DTS-HD MA TrueHD 7 1 Atmos")
    assert nordic["title"] == "Dune Part Two"
    assert nordic["year"] == 2024

    versioned = parse_title("Dune Part Two 2024 V2 1080p X264 HDTS English + Hindi AAC 2.5GB")
    assert versioned["title"] == "Dune Part Two"
    assert versioned["year"] == 2024


def test_season_pack_suffix_is_removed_from_the_show_title():
    parsed = parse_title("Dune Prophecy S01 1080p x265-ELiTE")
    assert parsed["title"] == "Dune Prophecy"
    assert parsed["season"] == 1
    assert parsed["episode"] is None
    assert "seasons" not in parsed


def test_single_season_pack_keeps_the_show_name():
    parsed = parse_title("Slow Horses - S04 - Mp4 x264 AC3 1080p")
    assert parsed["title"] == "Slow Horses"
    assert parsed["season"] == 4
    assert parsed["episode"] is None

    worded = parse_title("Slow Horses Season 4 Complete 1080p")
    assert worded["title"] == "Slow Horses"
    assert worded["season"] == 4
    assert worded["episode"] is None


def test_season_range_lists_every_covered_season():
    parsed = parse_title("Slow Horses 2022 Seasons 1 to 5 Complete 1080p WEB x264 [i_c]")
    assert parsed["title"] == "Slow Horses"
    assert parsed["year"] == 2022
    assert parsed["season"] is None
    assert parsed["episode"] is None
    assert parsed["seasons"] == [1, 2, 3, 4, 5]

    coded = parse_title("Slow Horses S01-S05 1080p")
    assert coded["title"] == "Slow Horses"
    assert coded["seasons"] == [1, 2, 3, 4, 5]
    assert coded["episode"] is None


def test_one_word_season_pack_keeps_the_show_name():
    parsed = parse_title("Dune S01 COMPLETE 1080p")
    assert parsed["title"] == "Dune"
    assert parsed["season"] == 1
    assert parsed["episode"] is None

    mobland = parse_title("MobLand S02 1080P AMZN WEB-DL DDP5.1. X265 POOTLED")
    assert mobland["title"] == "MobLand"
    assert mobland["season"] == 2
    assert mobland["episode"] is None

    dashed = parse_title("Mobland - S01 - Mp4 x264 AC3 1080p")
    assert dashed["title"] == "Mobland"
    assert dashed["season"] == 1
    assert dashed["episode"] is None

    untouched = parse_title("Mission Complete 1080p BluRay")
    assert untouched["title"] != "Mission"


def test_part_one_keeps_its_title_and_gains_a_year():
    parsed = parse_title("Dune Part One 2021 720p BluRay x264 DuaL-TURKO")
    assert parsed["title"] == "Dune Part One"
    assert parsed["year"] == 2021


def test_book_titles_are_not_rewritten_as_the_movie():
    audiobook = parse_title("Dune - Audiobook Collection 2015")
    assert audiobook["title"] != "Dune"
    assert "audiobook" in audiobook["title"].casefold()

    epub = parse_title("Dune by Frank Herbert EPUB")
    assert epub["title"] != "Dune"


def test_year_in_2020s_is_preserved():
    with patch("app.title_parser.PTN.parse", return_value={"title": "Dune Part Two", "year": 2024}):
        assert parse_title("Dune.Part.Two.2024.2160p")["year"] == 2024


def test_non_latin_title_is_preserved():
    with patch("app.title_parser.PTN.parse", return_value={"title": "進撃の巨人"}):
        assert parse_title("進撃の巨人.S04E01")["title"] == "進撃の巨人"


def test_episode_code_after_other_metadata_is_found():
    with patch("app.title_parser.PTN.parse", return_value={"title": "Example Show"}):
        assert parse_title("Example.Show.1080p.WEB-DL.S01.E12-GROUP")["episode"] == 12


def test_ptn_and_supplementary_regex_agree():
    with patch("app.title_parser.PTN.parse", return_value={"title": "Example Show", "season": 3, "episode": 6}):
        assert parse_title("Example.Show.S03E06")["season"] == 3
        assert parse_title("Example.Show.S03E06")["episode"] == 6


def test_ptn_values_take_precedence_when_regex_disagrees():
    with patch("app.title_parser.PTN.parse", return_value={"title": "Example Show", "season": 7, "episode": 11}):
        parsed = parse_title("Example.Show.S02E03")
    assert parsed["season"] == 7
    assert parsed["episode"] == 11


def test_missing_ptn_title_falls_back_to_cleaned_original():
    with patch("app.title_parser.PTN.parse", return_value={"season": 1, "episode": 2}):
        assert parse_title("Fallback_Title.S01E02")["title"] == "Fallback Title"
