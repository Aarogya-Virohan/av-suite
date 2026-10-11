from datetime import datetime, timezone

from app.api.v1.posture import report_filename

NOW = datetime(2026, 10, 11, 6, 5, 9, tzinfo=timezone.utc)


def test_plain_case_ref_keeps_its_name_and_becomes_unique():
    assert report_filename("PT-0042", NOW, "ab12cd34") == "PT-0042_20261011T060509Z_ab12cd34.json"


def test_same_case_ref_no_longer_collides():
    assert report_filename("Na", NOW, "aaaaaaaa") != report_filename("Na", NOW, "bbbbbbbb")


def test_path_characters_cannot_leave_the_folder():
    name = report_filename("../../app/main", NOW, "ab12cd34")
    assert "/" not in name and "\\\\" not in name and ".." not in name
    assert name == "app_main_20261011T060509Z_ab12cd34.json"


def test_empty_or_symbol_only_case_ref_still_gets_a_name():
    assert report_filename("", NOW, "x").startswith("report_")
    assert report_filename("///", NOW, "x").startswith("report_")


def test_long_case_ref_is_capped():
    name = report_filename("A" * 500, NOW, "x")
    assert name.startswith("A" * 60 + "_")
