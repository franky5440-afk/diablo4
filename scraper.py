#!/usr/bin/env python3
import hashlib
import html as html_lib
import json
import logging
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote_plus, urljoin, urlparse

import cloudscraper
import requests
import yt_dlp
from bs4 import BeautifulSoup
from ddgs import DDGS

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
LOGS = BASE / "logs"
DATA.mkdir(exist_ok=True)
LOGS.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOGS / "scraper.log", encoding="utf-8"), logging.StreamHandler()],
)
log = logging.getLogger("diablo4")

UA = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.5",
}

VIDEO_DOMAINS = ("youtube.com", "youtu.be", "bilibili.com", "twitch.tv", "nicovideo.jp")

HOT_CUTOFF_DAYS = 30
RSS_CHANNEL_CAP = 60
NEW_FLAT_LIMIT = 150
GAME_TERMS = ("diablo 4", "diablo iv", "diablo4", "暗黑破壞神4", "暗黑破壞神 4", "暗黑4", "d4")
GAME_TERMS_COMPACT = ("diablo4", "diabloiv", "暗黑破壞神4", "暗黑4", "d4")

TWEET_CAP = 250
X_SEARCH_QUERIES = {
    "zh": ('"暗黑破壞神4" OR "暗黑4" OR "D4" site:x.com', "tw-zh"),
    "en": ('"Diablo 4" OR "Diablo IV" site:x.com', "us-en"),
    "ja": ('"ディアブロ4" OR "Diablo4" site:x.com', "jp-jp"),
}
X_OFFICIAL_ACCOUNTS = ("Diablo",)
SYND_URL = "https://syndication.twitter.com/srv/timeline-profile/screen-name/{}?showReplies=false"
SYND_MARKER = '<script id="__NEXT_DATA__" type="application/json">'
STATUS_RE = re.compile(r"\b(?:x|twitter)\.com/([A-Za-z0-9_]{1,15})/status(?:es)?/(\d{10,})")
TIME_PREFIX_RE = re.compile(
    r"^(?:\d+\s+(?:seconds?|minutes?|hours?|days?|weeks?|months?|years?)\s+ago"
    r"|[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}"
    r"|\d{4}-\d{2}-\d{2})\s*[·\-–—]\s*"
)
JUNK_RES = (
    re.compile(r"log\s*in\s*sign\s*up"),
    re.compile(r"sensitive\s+content"),
    re.compile(r"this\s+post\s+is\s+(?:only\s+available|unavailable)"),
    re.compile(r"\(\@[A-Za-z0-9_]+\)\.\s*\d+\s+(?:replies|retweets|likes)\b"),
)


def clean_tweet_text(text):
    t = TIME_PREFIX_RE.sub("", text or "").strip()
    if not t:
        return None
    low = t.lower()
    if any(p.search(low) for p in JUNK_RES):
        return None
    return t


def now_str():
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")


def load_json(name, default):
    p = DATA / name
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return default


def save_json(name, obj):
    (DATA / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def set_meta(section):
    meta = load_json("meta.json", {})
    meta[section] = now_str()
    save_json("meta.json", meta)


CJK_RE = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]")
KANA_RE = re.compile(r"[\u3040-\u30ff]")


def has_cjk(s):
    return bool(CJK_RE.search(s or ""))


def detect_lang(text, url=""):
    t = text or ""
    if KANA_RE.search(t):
        return "ja"
    d = domain_of(url)
    if d.endswith(".jp"):
        return "ja"
    if has_cjk(t):
        return "zh"
    return "en"


def norm_url(u):
    u = u.split("#")[0].rstrip("/")
    return u.lower()


def domain_of(u):
    netloc = urlparse(u).netloc.lower()
    return netloc[4:] if netloc.startswith("www.") else netloc


def md5_id(text):
    return re.sub(r"[^a-f0-9]", "", hashlib.md5(text.encode()).hexdigest())


def is_video_url(url):
    d = domain_of(url)
    return any(d == vd or d.endswith("." + vd) for vd in VIDEO_DOMAINS)


# ---------------------------------------------------------------- Top 10 BD（d2core 主來源；Maxroll / Mobalytics 備援）

# 暗黑核 d2core：SPA；api.d2core.com 無 token 回 ACCESS_TOKEN_EMPTY。
# 目前無公開可重放的列表 JSON，故 builds_d2core.json 可能為空；UI 以 Maxroll/Mobalytics 為 live。
D2CORE_BUILDS_URL = "https://www.d2core.com/d4/builds"
D2CORE_API_CANDIDATES = (
    "https://api.d2core.com/d4/builds",
    "https://api.d2core.com/api/d4/builds",
)

MOBA_BUILDS_URL = "https://mobalytics.gg/diablo-4/builds"
MOBA_GQL_URL = "https://mobalytics.gg/api/diablo-4/v1/graphql/query"
MOBA_SORT_BY = "TRENDING"
MOBA_TIMEFRAME = "ALL"
MOBA_GQL_QUERY = """query($input: Diablo4UserGeneratedDocumentsListInput!, $page: Diablo4UserGeneratedDocumentsListPage!) {
  game: diablo4 { documents { userGeneratedDocuments(input: $input, page: $page) {
    error
    pageInfo { total }
    documents {
      id slugifiedName status updatedAt
      data { name }
      author { name }
      featured { slug status }
      tags { data { groupSlug name slug } }
    }
  } } }
}"""

MAXROLL_BUILDS_URL = "https://maxroll.gg/d4/build-guides"
MAXROLL_CLASS_HUBS = {
    "barbarian", "druid", "necromancer", "paladin",
    "rogue", "sorcerer", "spiritborn", "warlock",
}
BUILD_TOP_N = 10


def scrape_d2core():
    """嘗試暗黑核公開 API；無 token 時回空 list（保留舊檔由 update_builds 處理）。"""
    for url in D2CORE_API_CANDIDATES:
        try:
            r = requests.get(url, headers=UA, timeout=20)
            ctype = r.headers.get("content-type", "")
            body = r.json() if "json" in ctype else {}
            if isinstance(body, dict) and body.get("errMsg") == "ACCESS_TOKEN_EMPTY":
                log.warning("d2core %s: ACCESS_TOKEN_EMPTY（SPA 需登入 token）", url)
                continue
            items = body.get("data") or body.get("builds") or body.get("list") or []
            if isinstance(items, list) and items:
                out = []
                for raw in items[:BUILD_TOP_N]:
                    if not isinstance(raw, dict):
                        continue
                    title = (raw.get("title") or raw.get("name") or "").strip()
                    link = (raw.get("url") or raw.get("link") or "").strip()
                    if not title:
                        continue
                    if link and not link.startswith("http"):
                        link = urljoin("https://www.d2core.com", link)
                    out.append({
                        "id": md5_id(link or title),
                        "rank": len(out) + 1,
                        "title": title,
                        "url": link or D2CORE_BUILDS_URL,
                        "author": raw.get("author") or raw.get("creator") or "",
                        "updated": raw.get("updated") or raw.get("updateTime"),
                        "patch": raw.get("patch") or raw.get("season"),
                        "classes": raw.get("classes") or ([raw["class"]] if raw.get("class") else []),
                        "tags": raw.get("tags") or [],
                        "source": "d2core",
                        "found_date": now_str()[:10],
                    })
                return out
        except Exception as e:
            log.warning("d2core %s failed: %s", url, e)
    return []


def fetch_moba_builds(limit):
    """Diablo 4 Mobalytics GraphQL；expert-verification 常為 0 筆，改無 tag 取 TRENDING。"""
    s = cloudscraper.create_scraper(browser={"browser": "firefox", "platform": "linux", "desktop": True})
    s.get(MOBA_BUILDS_URL, timeout=40)
    tag_sets = [
        [{"groupSlug": "vefified", "slug": "expert-verification"}],
        [],
    ]
    last_err = None
    for tags in tag_sets:
        payload = {
            "query": MOBA_GQL_QUERY,
            "variables": {
                "input": {
                    "type": "builds",
                    "sortBy": MOBA_SORT_BY,
                    "publishedTimeframe": MOBA_TIMEFRAME,
                    "tags": tags,
                },
                "page": {"limit": limit},
            },
        }
        r = s.post(MOBA_GQL_URL, json=payload, timeout=40, headers={
            "Content-Type": "application/json",
            "Referer": MOBA_BUILDS_URL,
            "Origin": "https://mobalytics.gg",
        })
        r.raise_for_status()
        body = r.json()
        if body.get("errors"):
            last_err = body["errors"][:1]
            continue
        node = body["data"]["game"]["documents"]["userGeneratedDocuments"]
        if node.get("error"):
            last_err = node["error"]
            continue
        docs = node.get("documents") or []
        if docs:
            return docs
    if last_err:
        raise ValueError(f"mobalytics error: {last_err}")
    return []


def moba_item(doc):
    title = ((doc.get("data") or {}).get("name") or "").strip()
    author = ((doc.get("author") or {}).get("name") or "").strip()
    if not title or not author:
        return None
    slug = ((doc.get("featured") or {}).get("slug") or "").strip() or doc.get("slugifiedName") or ""
    if not slug:
        return None
    url = f"https://mobalytics.gg/diablo-4/builds/{slug}"
    by_group = {}
    for t in ((doc.get("tags") or {}).get("data") or []):
        by_group.setdefault(t.get("groupSlug"), []).append(t.get("name") or "")
    cls = (by_group.get("class") or by_group.get("classes") or by_group.get("ascendancy") or [""])[0]
    patch = (by_group.get("patch") or by_group.get("season") or [None])[0]
    tags = [t for t in (by_group.get("build-type") or by_group.get("mode") or []) if t]
    updated = None
    raw = doc.get("updatedAt") or ""
    if raw:
        try:
            updated = datetime.strptime(raw[:10], "%Y-%m-%d").strftime("%b %d, %Y")
        except ValueError:
            updated = None
    return {
        "id": md5_id(url),
        "title": title,
        "url": url,
        "author": author,
        "updated": updated,
        "patch": patch,
        "classes": [cls] if cls else [],
        "tags": tags,
        "source": "mobalytics",
        "found_date": now_str()[:10],
    }


def scrape_mobalytics():
    out, seen = [], set()
    for doc in fetch_moba_builds(BUILD_TOP_N * 2):
        it = moba_item(doc)
        if not it:
            continue
        k = norm_url(it["url"])
        if k in seen:
            continue
        seen.add(k)
        it["rank"] = len(out) + 1
        out.append(it)
        if len(out) >= BUILD_TOP_N:
            break
    return out


def scrape_maxroll():
    """Maxroll D4 build-guides：SSR HTML；略過職業 hub 頁，取前 10 篇指南。"""
    r = requests.get(MAXROLL_BUILDS_URL, headers=UA, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    out, seen = [], set()
    for art in soup.find_all("article"):
        a = art.select_one('a[href^="/d4/build-guides/"]')
        if not a:
            continue
        href = a["href"].split("?")[0].rstrip("/")
        slug = href.rsplit("/", 1)[-1]
        if slug in MAXROLL_CLASS_HUBS:
            continue
        url = f"https://maxroll.gg{href}"
        k = norm_url(url)
        if k in seen:
            continue
        seen.add(k)
        h2 = art.find("h2")
        title = (h2.get("title") if h2 else "") or (h2.get_text(" ", strip=True) if h2 else "")
        author, updated = "", None
        if h2:
            m = re.search(r"By\s+(\S+)\s*\|\s*Last Updated:\s*(.+)", h2.get_text(" ", strip=True))
            if m:
                author = m.group(1)
                updated = m.group(2).strip()
        tags = []
        patch = None
        for sp in art.select('[class*="_tag_"]'):
            t = sp.get_text(" ", strip=True)
            if not t or t in tags:
                continue
            if re.search(r"\d+\.\d+", t) or "Season" in t:
                patch = patch or t
                continue
            tags.append(t)
        out.append({
            "id": md5_id(url),
            "rank": len(out) + 1,
            "title": title.strip(),
            "url": url,
            "author": author,
            "updated": updated,
            "patch": patch,
            "classes": tags[-2:-1] or tags[:1],
            "tags": tags,
            "source": "maxroll",
            "found_date": now_str()[:10],
        })
        if len(out) >= BUILD_TOP_N:
            break
    return out


def update_builds():
    steps = [
        ("builds_d2core", scrape_d2core),
        ("builds_mobalytics", scrape_mobalytics),
        ("builds_maxroll", scrape_maxroll),
    ]
    for name, fn in steps:
        try:
            items = fn()
        except Exception as e:
            log.error("%s failed: %s", name, e)
            continue
        if items:
            save_json(f"{name}.json", items)
            set_meta(name)
            log.info("%s: %d builds", name, len(items))
        else:
            log.warning("%s: parsed 0 items, keeping previous data", name)


# ---------------------------------------------------------------- YouTube

def yt_flat_search(query, n, sort_by_date=False, flat_limit=None):
    if sort_by_date:
        url = f"https://www.youtube.com/results?search_query={quote_plus(query)}&sp=CAI%3D"
    else:
        url = f"ytsearch{n}:{query}"
    opts = {"quiet": True, "no_warnings": True, "extract_flat": True, "skip_download": True, "socket_timeout": 30}
    if flat_limit:
        opts["playlist_items"] = f"1:{flat_limit}"
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    out = []
    for e in info.get("entries") or []:
        if not isinstance(e, dict):
            continue
        vid = e.get("id")
        if not vid or len(vid) != 11:
            continue
        out.append({
            "video_id": vid,
            "title": e.get("title") or "",
            "channel": e.get("channel") or e.get("uploader") or "",
            "channel_id": e.get("channel_id") or "",
            "view_count": e.get("view_count"),
            "duration": e.get("duration"),
            "url": f"https://www.youtube.com/watch?v={vid}",
        })
    return out


YDL_FULL = {"quiet": True, "no_warnings": True, "skip_download": True, "socket_timeout": 30}


def yt_rss_latest(channel_id):
    """回傳 (video_id, title, published_date, views, channel_name)。
    channel_name 一併帶回，否則只出現在 RSS 的候選影片會沒有頻道名，前端顯示空白、也無法去重"""
    out = []
    try:
        r = requests.get(f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}", headers=UA, timeout=15)
        r.raise_for_status()
        ns = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015",
              "m": "http://search.yahoo.com/mrss/"}
        root = ET.fromstring(r.content)
        chan = (root.findtext("a:author/a:name", "", ns) or "").strip()
        for e in root.findall("a:entry", ns):
            vid = e.findtext("yt:videoId", "", ns)
            title = (e.findtext("a:title", "", ns) or "").strip()
            pub = (e.findtext("a:published", "", ns) or "")[:10]
            views = e.find(".//m:statistics", ns)
            out.append((vid, title, pub, int(views.get("views")) if views is not None and views.get("views", "").isdigit() else None, chan))
    except Exception as e:
        log.warning("yt rss %s: %s", channel_id[:12], e)
    return out


def yt_full_info(vid):
    try:
        with yt_dlp.YoutubeDL(YDL_FULL) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
        ud = info.get("upload_date")
        date = f"{ud[:4]}-{ud[4:6]}-{ud[6:8]}" if ud else None
        vc = info.get("view_count")
        return date, vc if isinstance(vc, int) else None
    except Exception as e:
        log.warning("yt full %s: %s", vid, e)
        return None, None


def game_in_title(title):
    t = (title or "").lower()
    compact = t.replace(" ", "").replace("　", "")
    compact = compact.replace("diabloiv", "diablo4").replace("暗黑破壞神iv", "暗黑破壞神4")
    if any(w in t for w in GAME_TERMS):
        return True
    return any(w in compact for w in GAME_TERMS_COMPACT)


def within_cutoff(date_str, cutoff):
    try:
        return bool(date_str) and datetime.strptime(date_str, "%Y-%m-%d").date() >= cutoff
    except ValueError:
        return False


def dedupe_video_items(items):
    """同一頻道重複上傳／分段直播常出現完全同名的多支影片，前十名塞 3 份同一支很難看。
    以（頻道, 標題）去重，保留先出現的那支（呼叫端已排好序）"""
    out, seen = [], set()
    for it in items:
        k = ((it.get("channel") or "").strip().lower(), (it.get("title") or "").strip().lower())
        if k in seen:
            continue
        seen.add(k)
        out.append(it)
    return out


HOT_LOOKUP_BUDGET = 30


def resolve_dates_and_views(cands, rss_map, date_cache, budget=HOT_LOOKUP_BUDGET):
    """把候選的上傳日期／觀看數補齊：先吃免費來源（RSS、date_cache），
    只有兩者都沒有的才動用 yt_full_info（會打 YouTube，雲端 IP 容易被擋），且有次數上限。
    日期是熱門排序的第一順位條件，所以補日期的優先序放在觀看數高的候選"""
    for v in cands:
        info = rss_map.get(v["video_id"]) or {}
        if not v.get("date"):
            v["date"] = info.get("date") or date_cache.get(v["video_id"])
        if not isinstance(v.get("view_count"), int) and isinstance(info.get("views"), int):
            v["view_count"] = info["views"]
        if not v.get("channel") and info.get("channel"):
            v["channel"] = info["channel"]

    pending = [v for v in cands if not v.get("date") or not isinstance(v.get("view_count"), int)]
    pending.sort(key=lambda x: -(x.get("view_count") or 0))
    for v in pending[:budget]:
        date, views = yt_full_info(v["video_id"])
        time.sleep(0.4)
        if date:
            v["date"] = date
            date_cache[v["video_id"]] = date
        if isinstance(views, int):
            v["view_count"] = views
    return cands


def pick_hot_videos(pool, rss_map, keep, to_item, top_n, date_cache=None, hot_cutoff_days=HOT_CUTOFF_DAYS):
    """賽季遊戲的「熱門」不看全歷史觀看數：**時間先於觀看數**。
    先把候選的上傳日期補齊，取近 hot_cutoff_days 天內的依觀看數排序；
    窗內湊不滿 top_n 才用窗外（較舊）的依觀看數遞補，窗內候選一律優先，
    不因窗外某支觀看數更高就插隊。日期查不到的排最後，只在真的湊不滿時才用。"""
    date_cache = date_cache if date_cache is not None else {}
    cutoff = (datetime.now(timezone.utc) - timedelta(days=hot_cutoff_days)).date()
    chan_of = {v["video_id"]: v["channel"] for v in pool}
    cands = {v["video_id"]: dict(v) for v in pool}
    # 頻道 RSS 近期上傳也列入候選，避免搜尋結果偏舊時樣本不足
    for vid, info in rss_map.items():
        if vid in cands:
            continue
        if not (within_cutoff(info["date"], cutoff) and keep(info["title"]) and game_in_title(info["title"])):
            continue
        cands[vid] = {"video_id": vid, "title": info["title"],
                      "channel": chan_of.get(vid) or info.get("channel") or "",
                      "url": f"https://www.youtube.com/watch?v={vid}", "view_count": info["views"],
                      "date": info["date"]}

    resolve_dates_and_views(list(cands.values()), rss_map, date_cache)

    by_views = sorted(cands.values(), key=lambda x: -(x["view_count"] or 0))
    recent = [v for v in by_views if within_cutoff(v.get("date"), cutoff)]
    older = [v for v in by_views if v.get("date") and not within_cutoff(v["date"], cutoff)]
    undated = [v for v in by_views if not v.get("date")]

    picked = dedupe_video_items(recent)[:top_n]
    if len(picked) < top_n:
        picked = dedupe_video_items(picked + older + undated)[:top_n]
    return [to_item(v, v.get("date"), v["view_count"]) for v in picked]


def pick_new_videos(pool, rss_map, keep, to_item, top_n):
    """取候選池裡最近上傳的 top_n 部影片：一律依上傳日期新到舊排序；
    近期候選不足 top_n 時，用較舊的候選遞補湊滿——語意是「目前最新的 top_n 部」，
    不因某個時間窗內剛好樣本不足就讓 tab 顯示的部數縮水。"""
    chan_of = {v["video_id"]: v["channel"] for v in pool}
    cands = {}
    for vid, info in rss_map.items():
        if not (keep(info["title"]) and game_in_title(info["title"])):
            continue
        try:
            datetime.strptime(info["date"], "%Y-%m-%d")
        except (ValueError, TypeError):
            continue
        cands[vid] = to_item({"video_id": vid, "title": info["title"],
                              "channel": chan_of.get(vid) or info.get("channel") or "",
                              "url": f"https://www.youtube.com/watch?v={vid}"}, info["date"], info["views"])

    items = dedupe_video_items(sorted(cands.values(), key=lambda x: x["date"] or "", reverse=True))[:top_n]
    if len(items) >= top_n:
        return items

    log.warning("videos new: rss candidates only %d (<%d), falling back to full-extract scan to backfill",
                len(items), top_n)
    seen = {it["video_id"] for it in items}
    extra, scanned = [], 0
    for v in pool:
        if v["video_id"] in seen:
            continue
        if len(items) + len(extra) >= top_n or scanned >= 40:
            break
        scanned += 1
        date, vc = yt_full_info(v["video_id"])
        time.sleep(0.4)
        if date:
            extra.append(to_item(v, date, vc))
            seen.add(v["video_id"])
    return dedupe_video_items(sorted(items + extra, key=lambda x: x["date"] or "", reverse=True))[:top_n]


def collect_videos(lang, date_cache):
    if lang == "zh":
        hot_queries, new_queries = ["暗黑破壞神4 攻略", "Diablo 4 配裝", "D4 BD"], ["暗黑破壞神4 攻略"]

        def keep(title):
            return has_cjk(title) and not KANA_RE.search(title)
    elif lang == "ja":
        hot_queries, new_queries = ["ディアブロ4 ビルド", "Diablo4 攻略"], ["ディアブロ4 ビルド"]

        def keep(title):
            return bool(KANA_RE.search(title))
    else:
        hot_queries, new_queries = ["Diablo 4 build guide", "Diablo IV build"], ["Diablo 4 build guide"]

        def keep(title):
            return not has_cjk(title)

    # 熱門池同時吃「相關度」與「上傳時間」兩種排序：只用相關度的話，
    # YouTube 會一直回 2024 上市期那批高觀看數老片，近 30 天的新片根本進不了候選池
    pool_hot = []
    seen = set()
    for q in hot_queries:
        for v in yt_flat_search(q, 25):
            k = v["video_id"]
            if k in seen:
                continue
            seen.add(k)
            if not keep(v["title"]):
                continue
            pool_hot.append(v)
    for q in hot_queries:
        for v in yt_flat_search(q, 25, sort_by_date=True, flat_limit=50):
            k = v["video_id"]
            if k in seen:
                continue
            seen.add(k)
            if not keep(v["title"]):
                continue
            pool_hot.append(v)

    def to_item(v, date, vc):
        return {
            "video_id": v["video_id"],
            "title": v["title"],
            "channel": v["channel"],
            "url": v["url"],
            "views": vc,
            "date": date,
            "lang": lang,
        }

    pool_new = []
    seen2 = set()
    for q in new_queries:
        for v in yt_flat_search(q, 25, sort_by_date=True, flat_limit=NEW_FLAT_LIMIT):
            k = v["video_id"]
            if k in seen2:
                continue
            seen2.add(k)
            if not keep(v["title"]):
                continue
            pool_new.append(v)

    chans = []
    for v in sorted(pool_hot, key=lambda x: -(x.get("view_count") or 0)):
        cid = v.get("channel_id")
        if cid and cid not in chans:
            chans.append(cid)
    for v in pool_new:
        cid = v.get("channel_id")
        if cid and cid not in chans:
            chans.append(cid)
    rss_map = {}
    for cid in chans[:RSS_CHANNEL_CAP]:
        for vid, title, pub, views, chan in yt_rss_latest(cid):
            if pub and len(pub) == 10:
                rss_map[vid] = {"title": title, "date": pub, "views": views, "channel": chan}
        time.sleep(0.3)
    log.info("videos [%s]: %d channels rss -> %d videos", lang, min(len(chans), RSS_CHANNEL_CAP), len(rss_map))
    # RSS 全空代表 YouTube 擋下請求，不把無日期老片遞補成新快照。
    if not rss_map:
        log.warning("videos [%s]: RSS 0 部，視為 YouTube 擋下，hot/new 一律回空 list 讓 update_videos 保留前一日資料", lang)
        return [], []

    hot = pick_hot_videos(pool_hot, rss_map, keep, to_item, 10, date_cache)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=HOT_CUTOFF_DAYS)).date()
    fresh = sum(1 for it in hot if within_cutoff(it["date"], cutoff))
    log.info("videos hot [%s]: %d picked, %d within %dd", lang, len(hot), fresh, HOT_CUTOFF_DAYS)
    if fresh < len(hot):
        log.warning("videos hot [%s]: only %d/%d within %dd, backfilled with older",
                    lang, fresh, len(hot), HOT_CUTOFF_DAYS)

    log.info("videos new [%s]: %d candidates", lang, len(pool_new))
    new = pick_new_videos(pool_new, rss_map, keep, to_item, 10)
    log.info("videos new [%s]: %d picked", lang, len(new))

    return hot, new


def update_videos():
    cache = load_json("video_dates.json", {})
    for lang in ("zh", "en", "ja"):
        hot, new = collect_videos(lang, cache)
        for it in [*hot, *new]:
            vid = it["video_id"]
            if it["date"]:
                cache[vid] = it["date"]
            elif vid in cache:
                it["date"] = cache[vid]
        for category, items in (("hot", hot), ("new", new)):
            name = f"videos_{category}_{lang}"
            if items:
                save_json(f"{name}.json", items)
                set_meta(name)
                log.info("%s: %d videos", name, len(items))
            else:
                log.warning("%s: parsed 0 items, keeping previous data", name)
    save_json("video_dates.json", cache)


# ---------------------------------------------------------------- 巴哈姆特

BAHA_URL = "https://forum.gamer.com.tw/B.php?bsn=75105"  # 暗黑破壞神 4 哈啦板
BAHA_BASE = "https://forum.gamer.com.tw/"


def parse_baha_rows(html):
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for row in soup.select("tr.b-list__row"):
        if row.select_one(".b-list__summary__mark"):
            continue
        main_link = row.select_one("td.b-list__main > a[href*='C.php']")
        if not main_link:
            continue
        title_el = row.select_one(".b-list__main__title")
        brief = row.select_one(".b-list__brief")
        num_el = row.select_one(".b-list__count__number span")
        author_el = row.select_one(".b-list__count__user a")
        time_el = row.select_one(".b-list__time__edittime a")
        items.append({
            "title": title_el.get_text(" ", strip=True) if title_el else "",
            "url": urljoin(BAHA_BASE, main_link.get("href", "")),
            "author": author_el.get_text(strip=True) if author_el else "",
            "replies": num_el.get_text(strip=True) if num_el else "",
            "time": time_el.get_text(strip=True) if time_el else "",
            "snippet": brief.get_text(" ", strip=True)[:200] if brief else "",
        })
    return items


def update_bahamut():
    items = []
    try:
        r = requests.get(BAHA_URL, headers=UA, timeout=20)
        r.raise_for_status()
        rows = parse_baha_rows(r.text)
        seen = set()
        for it in rows:
            k = norm_url(it["url"])
            if k in seen:
                continue
            seen.add(k)
            it["id"] = md5_id(k)
            it["source"] = "forum.gamer.com.tw"
            it["found_date"] = now_str()[:10]
            items.append(it)
            if len(items) >= 10:
                break
    except Exception as e:
        log.error("bahamut failed: %s", e)
    if items:
        save_json("bahamut.json", items)
        set_meta("bahamut")
        log.info("bahamut: %d topics", len(items))
    else:
        log.warning("bahamut: no items parsed, keeping previous data")


# ---------------------------------------------------------------- X 推文

def snowflake_date(tid):
    ts = (int(tid) >> 22) + 1288834974657
    return datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def x_timeline(screen_name):
    try:
        r = requests.get(SYND_URL.format(screen_name), headers=UA, timeout=20)
        r.raise_for_status()
        data = json.loads(r.text.split(SYND_MARKER, 1)[1].split("</script>", 1)[0])
        entries = data["props"]["pageProps"]["timeline"]["entries"]
        out = []
        for e in entries:
            tw = e.get("content", {}).get("tweet", {})
            tid = tw.get("id_str") or ""
            text = (tw.get("full_text") or "").strip()
            likes = tw.get("favorite_count")
            if not tid or not text:
                continue
            out.append({
                "tid": tid,
                "author": screen_name,
                "author_name": (tw.get("user", {}) or {}).get("name") or "",
                "text": text,
                "likes": likes if isinstance(likes, int) else None,
                "date": snowflake_date(tid),
            })
        return out
    except Exception as e:
        log.warning("x timeline %s: %s", screen_name, e)
        return []


def tweet_item(t):
    url = f"https://x.com/{t['author']}/status/{t['tid']}"
    text = t.get("text") or ""
    return {
        "id": md5_id(url),
        "tid": t["tid"],
        "url": url,
        "author": t["author"],
        "author_name": t.get("author_name") or "",
        "text": text,
        "date": t.get("date") or snowflake_date(t["tid"]),
        "likes": t.get("likes"),
        "lang": detect_lang(text),
    }


def update_tweets():
    pool = {}
    for lang in ("zh", "en", "ja"):
        for it in load_json(f"tweets_{lang}.json", []):
            if isinstance(it.get("tid"), str) and it["tid"].isdigit():
                pool[it["tid"]] = it

    added = 0

    def merge(t):
        nonlocal added
        if t["tid"] not in pool:
            added += 1
        pool[t["tid"]] = tweet_item(t)

    with DDGS() as d:
        for qkey, (q, region) in X_SEARCH_QUERIES.items():
            try:
                results = list(d.text(q, region=region, max_results=20))
            except Exception as e:
                log.warning("ddgs x %s %s: %s", qkey, q, e)
                continue
            for r in results:
                m = STATUS_RE.search(r.get("href") or "")
                if not m:
                    continue
                title = html_lib.unescape((r.get("title") or "").strip())
                body = html_lib.unescape((r.get("body") or "").strip())
                if not game_in_title(title + " " + body):
                    continue
                disp, _, rest = title.partition(" on X:")
                text = rest.strip()
                if text.endswith("/ X"):
                    text = text[:-3].strip()
                if len(text) >= 2 and text.startswith('"') and text.endswith('"'):
                    text = text[1:-1].strip()
                if not text:
                    text = body
                text = clean_tweet_text(text)
                if not text:
                    continue
                merge({"tid": m.group(2), "author": m.group(1).lower(),
                       "author_name": disp.strip(), "text": text})
            time.sleep(1.5)

    for sn in X_OFFICIAL_ACCOUNTS:
        for t in x_timeline(sn):
            if game_in_title(t["text"]):
                merge(t)

    buckets = {"zh": [], "en": [], "ja": []}
    for it in pool.values():
        lang = it.get("lang") if it.get("lang") in buckets else detect_lang(it["text"])
        buckets[lang].append(it)
    total = {}
    for lang, items in buckets.items():
        items.sort(key=lambda x: ((x.get("date") or ""), (x.get("likes") or 0)), reverse=True)
        items = items[:TWEET_CAP]
        total[lang] = len(items)
        save_json(f"tweets_{lang}.json", items)
    set_meta("tweets")
    log.info("tweets: +%d -> zh=%d en=%d ja=%d", added, total["zh"], total["en"], total["ja"])


def main():
    started = time.time()
    log.info("=" * 50)
    steps = [
        ("builds", update_builds),
        ("videos", update_videos),
        ("bahamut", update_bahamut),
        ("tweets", update_tweets),
    ]
    failures = []
    for name, fn in steps:
        try:
            fn()
        except Exception as e:
            log.exception("%s crashed: %s", name, e)
            failures.append(name)
    set_meta("_last_run")
    log.info("done in %.1fs%s", time.time() - started, f" | FAILED: {failures}" if failures else "")


if __name__ == "__main__":
    main()
