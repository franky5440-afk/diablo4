#!/usr/bin/env python3
"""Build static Pages artifact: merge JSON data + convert story MD → HTML JSON."""
import json
import re
import shutil
from pathlib import Path

try:
    import markdown as md_lib
    MD = md_lib.Markdown(extensions=["tables", "fenced_code", "nl2br", "sane_lists"])
    HAS_MD = True
except ImportError:
    MD = None
    HAS_MD = False

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
SITE = BASE / "site"
STORY_SRC = BASE / "content" / "story"

SECTIONS = [
    "builds_d2core", "builds_mobalytics", "builds_maxroll",
    "videos_hot_zh", "videos_hot_en", "videos_hot_ja",
    "videos_new_zh", "videos_new_en", "videos_new_ja",
    "bahamut",
    "tweets_zh", "tweets_en", "tweets_ja",
    "meta",
]


def chapter_id(filename: str, prefix: str = "ch") -> str:
    stem = Path(filename).stem
    m = re.match(r"^(\d+)", stem)
    return f"{prefix}-{m.group(1)}" if m else f"{prefix}-{stem}"


def chapter_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("# "):
            return s[2:].strip()
    return fallback


def build_story() -> dict:
    """Convert published chapter markdown → HTML payload for 劇情小說 tab.

    v1 stub: empty content/story → empty chapters（Ruth 第二輪填稿）.
    Auto-discovers numbered *.md (skip README.md).
    """
    empty = {
        "title": "暗黑破壞神4｜章回小說",
        "subtitle": "原創敘事改寫 · 非官方劇本 · 第二輪由 Ruth 填稿",
        "volumes": [{
            "id": "main",
            "title": "本篇",
            "short_title": "本篇",
            "blurb": "內容籌備中",
            "chapters": [],
            "chapter_count": 0,
        }],
        "chapters": [],
        "chapter_count": 0,
    }
    if not STORY_SRC.is_dir():
        empty["error"] = "content/story 目錄不存在"
        return empty

    files = sorted(
        p.name for p in STORY_SRC.glob("*.md")
        if p.name.lower() != "readme.md" and not p.name.startswith("_")
    )
    if not files or not HAS_MD:
        if files and not HAS_MD:
            empty["error"] = "缺少 markdown 套件，無法建置劇情"
        return empty

    chapters = []
    for fname in files:
        path = STORY_SRC / fname
        raw = path.read_text(encoding="utf-8")
        title = chapter_title(raw, Path(fname).stem)
        MD.reset()
        html = MD.convert(raw)
        chapters.append({
            "id": chapter_id(fname),
            "file": fname,
            "title": title,
            "html": html,
        })

    return {
        "title": "暗黑破壞神4｜章回小說",
        "subtitle": "原創敘事改寫 · 非官方劇本",
        "volumes": [{
            "id": "main",
            "title": "本篇",
            "short_title": "本篇",
            "blurb": "",
            "chapters": chapters,
            "chapter_count": len(chapters),
        }],
        "chapters": chapters,
        "chapter_count": len(chapters),
    }


def main():
    merged = {}
    for name in SECTIONS:
        p = DATA / f"{name}.json"
        merged[name] = json.loads(p.read_text(encoding="utf-8")) if p.exists() else ([] if name != "meta" else {})

    story = build_story()

    if SITE.exists():
        shutil.rmtree(SITE)
    (SITE / "data").mkdir(parents=True)
    payload = json.dumps(merged, ensure_ascii=False)
    (DATA / "site.json").write_text(payload, encoding="utf-8")
    (SITE / "data" / "site.json").write_text(payload, encoding="utf-8")

    story_payload = json.dumps(story, ensure_ascii=False)
    (DATA / "story.json").write_text(story_payload, encoding="utf-8")
    (SITE / "data" / "story.json").write_text(story_payload, encoding="utf-8")

    shutil.copy(BASE / "templates" / "index.html", SITE / "index.html")
    shutil.copytree(BASE / "static", SITE / "static")
    print(
        f"site built: "
        f"{sum(len(merged[k]) for k in ('builds_d2core', 'builds_mobalytics', 'builds_maxroll'))} builds, "
        f"{sum(len(merged[k]) for k in ('videos_hot_zh', 'videos_hot_en', 'videos_hot_ja', 'videos_new_zh', 'videos_new_en', 'videos_new_ja'))} videos, "
        f"story chapters={story.get('chapter_count', 0)}"
    )


if __name__ == "__main__":
    main()
