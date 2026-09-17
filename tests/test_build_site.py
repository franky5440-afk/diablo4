import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import build_site


def test_story_volumes_present():
    story = build_site.build_story()
    assert "error" not in story
    vol_ids = [v["id"] for v in story["volumes"]]
    assert vol_ids == ["main", "dlc01", "dlc02"]
    assert story["volumes"][0]["short_title"] == "本篇"
    assert story["volumes"][1]["short_title"] == "憎恨之軀"
    assert story["volumes"][2]["short_title"] == "憎恨之王"
    assert story["chapter_count"] == story["volumes"][0]["chapter_count"] == 9
    assert story["volumes"][1]["chapter_count"] == 5
    assert story["volumes"][2]["chapter_count"] == 5
    # No editor-only files in published chapter lists
    for vol in story["volumes"]:
        for ch in vol["chapters"]:
            assert "全稿" not in ch["file"]
            assert ch["file"] != "README.md"
            assert "本節依據" not in ch["html"]


def test_sections_have_build_keys():
    assert "builds_maxroll" in build_site.SECTIONS
    assert "builds_d2core" in build_site.SECTIONS
    assert "builds_poeninja" not in build_site.SECTIONS
