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


# Reader-facing chapter order（對齊 nioh3 STORY_PUBLISH）.
# 全稿_上站用.md / README.md stay in content/story for maintenance only.
STORY_PUBLISH = [
    "00_導讀.md",
    "01_序章_漂泊.md",
    "02_第一幕_冰冷如鐵的信仰.md",
    "03_第二幕_利刃再度翻絞.md",
    "04_第三幕_惡魔在人間.md",
    "05_第四幕_風暴將至.md",
    "06_第五幕_高昂的代價.md",
    "07_第六幕_與造物主共舞.md",
    "08_終章_無法癒合的傷.md",
]


def _strip_editor_notes(raw: str) -> str:
    """Drop any leaked 「本節依據」 editor blocks from chapter bodies."""
    # Split on markdown heading / bold markers that start 本節依據
    parts = re.split(r"(?m)^(?:#{1,6}\s*|\*\*|__)本節依據.*$", raw)
    if len(parts) == 1:
        return raw
    # Keep only the body before the first 本節依據 marker
    return parts[0].rstrip() + "\n"


def _load_chapters(src: Path, filenames: list) -> list:
    chapters = []
    for fname in filenames:
        path = src / fname
        if not path.exists():
            continue
        raw = _strip_editor_notes(path.read_text(encoding="utf-8"))
        title = chapter_title(raw, Path(fname).stem)
        MD.reset()
        html = MD.convert(raw)
        chapters.append({
            "id": chapter_id(fname),
            "file": fname,
            "title": title,
            "html": html,
        })
    return chapters


def build_story() -> dict:
    """Convert published chapter markdown → HTML payload for 劇情小說 tab.

    Picks STORY_PUBLISH (00 導讀 + 01–08) in order; skips 全稿 / README.
    """
    empty = {
        "title": "暗黑破壞神4｜章回小說",
        "subtitle": "原創敘事改寫 · 非官方劇本",
        "volumes": [{
            "id": "main",
            "title": "本篇",
            "short_title": "本篇",
            "blurb": "",
            "chapters": [],
            "chapter_count": 0,
        }],
        "chapters": [],
        "chapter_count": 0,
    }
    if not STORY_SRC.is_dir():
        empty["error"] = "content/story 目錄不存在"
        return empty
    if not HAS_MD:
        empty["error"] = "缺少 markdown 套件，無法建置劇情"
        return empty

    chapters = _load_chapters(STORY_SRC, STORY_PUBLISH)
    if not chapters:
        return empty

    return {
        "title": "暗黑破壞神4｜章回小說",
        "subtitle": "原創敘事改寫 · 非官方劇本",
        "volumes": [{
            "id": "main",
            "title": "本篇",
            "short_title": "本篇",
            "blurb": "涅維斯克漂泊 → 憎恨王座與終章餘燼",
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
