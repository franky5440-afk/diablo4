import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import build_site


def test_story_stub_empty():
    story = build_site.build_story()
    assert story["chapter_count"] == 0
    assert story["volumes"][0]["id"] == "main"


def test_sections_have_build_keys():
    assert "builds_maxroll" in build_site.SECTIONS
    assert "builds_d2core" in build_site.SECTIONS
    assert "builds_poeninja" not in build_site.SECTIONS
