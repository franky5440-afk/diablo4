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
DLC01_SRC = STORY_SRC / "dlc01"
DLC02_SRC = STORY_SRC / "dlc02"

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

# DLC01《憎恨之軀》reader chapters. Skip 全稿.
DLC01_PUBLISH = [
    "00_導讀.md",
    "01_追石入林.md",
    "02_靈界之心.md",
    "03_陵墓與背叛.md",
    "04_憎恨先驅.md",
]

# DLC02《憎恨之王》reader chapters. Skip README + 全稿.
DLC02_PUBLISH = [
    "00_導讀.md",
    "01_焚檔與偽先知.md",
    "02_骨刃與天使.md",
    "03_犧牲與斷頭.md",
    "04_創生之池.md",
]


def _strip_editor_notes(raw: str) -> str:
    """Drop any leaked 「本節依據」 editor blocks from chapter bodies."""
    # Split on markdown heading / bold markers that start 本節依據
    parts = re.split(r"(?m)^(?:#{1,6}\s*|\*\*|__)本節依據.*$", raw)
    if len(parts) == 1:
        return raw
    # Keep only the body before the first 本節依據 marker
    return parts[0].rstrip() + "\n"


def _load_chapters(src: Path, filenames: list, id_prefix: str = "ch") -> list:
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
            "id": chapter_id(fname, prefix=id_prefix),
            "file": fname,
            "title": title,
            "html": html,
        })
    return chapters


def build_story() -> dict:
    """Convert published chapter markdown → HTML payload for 劇情小說 tab.

    Schema (volumes): one JSON for a single loadStory() call.
      {
        title, subtitle,
        volumes: [ { id, title, short_title, blurb, chapters, chapter_count }, … ],
        chapters,          # backward-compat alias = 本篇 chapters
        chapter_count      # 本篇章數
      }

    Picks reader lists only; skips 全稿 / README / 目錄大綱／99／本節依據.
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

    main_chapters = _load_chapters(STORY_SRC, STORY_PUBLISH, id_prefix="ch")
    dlc01_chapters = _load_chapters(DLC01_SRC, DLC01_PUBLISH, id_prefix="dlc01")
    dlc02_chapters = _load_chapters(DLC02_SRC, DLC02_PUBLISH, id_prefix="dlc02")

    if not main_chapters and not dlc01_chapters and not dlc02_chapters:
        return empty

    volumes = [
        {
            "id": "main",
            "title": "本篇",
            "short_title": "本篇",
            "blurb": "涅維斯克漂泊 → 憎恨王座與終章餘燼",
            "chapters": main_chapters,
            "chapter_count": len(main_chapters),
        },
        {
            "id": "dlc01",
            "title": "DLC01 憎恨之軀",
            "short_title": "憎恨之軀",
            "blurb": "奈芮爾攜石入納罕圖 → 憎恨先驅與崔凡克終幕",
            "chapters": dlc01_chapters,
            "chapter_count": len(dlc01_chapters),
        },
        {
            "id": "dlc02",
            "title": "DLC02 憎恨之王",
            "short_title": "憎恨之王",
            "blurb": "納罕圖餘燼 → 斯科沃斯創生之池與墨菲斯托真身",
            "chapters": dlc02_chapters,
            "chapter_count": len(dlc02_chapters),
        },
    ]

    return {
        "title": "暗黑破壞神4｜章回小說",
        "subtitle": "原創敘事改寫 · 非官方劇本 · 含本篇與 DLC",
        "volumes": volumes,
        # Backward compatible: flat chapters = 本篇 only
        "chapters": main_chapters,
        "chapter_count": len(main_chapters),
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
    vol_summary = ", ".join(
        f"{v['id']}={v['chapter_count']}" for v in story.get("volumes", [])
    )
    print(
        f"site built: "
        f"{sum(len(merged[k]) for k in ('builds_d2core', 'builds_mobalytics', 'builds_maxroll'))} builds, "
        f"{sum(len(merged[k]) for k in ('videos_hot_zh', 'videos_hot_en', 'videos_hot_ja', 'videos_new_zh', 'videos_new_en', 'videos_new_ja'))} videos, "
        f"story volumes=[{vol_summary}] main_chapters={story.get('chapter_count', 0)}"
    )


if __name__ == "__main__":
    main()
