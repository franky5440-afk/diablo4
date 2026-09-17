#!/usr/bin/env python3
import json
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"

SECTIONS = [
    "builds_d2core", "builds_mobalytics", "builds_maxroll",
    "videos_hot_zh", "videos_hot_en", "videos_hot_ja",
    "videos_new_zh", "videos_new_en", "videos_new_ja",
    "bahamut",
    "tweets_zh", "tweets_en", "tweets_ja",
    "meta",
]

app = Flask(__name__, static_folder="static", template_folder="templates")


def load(name):
    p = DATA / f"{name}.json"
    if not p.exists():
        return [] if name != "meta" else {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/data")
def api_data():
    out = {s: load(s) for s in SECTIONS}
    return jsonify(out)


def match(item, q):
    hay = " ".join(str(item.get(k) or "") for k in (
        "title", "snippet", "channel", "source", "author", "author_name", "text",
        "classes", "tags", "patch",
    )).lower()
    return all(w in hay for w in q.split())


@app.get("/api/search")
def api_search():
    q = (request.args.get("q") or "").strip().lower()
    if not q:
        return jsonify({"query": "", "builds": [], "hot": [], "new": [], "bahamut": [], "tweets": [], "total": 0})
    builds = [b for s in ("builds_d2core", "builds_mobalytics", "builds_maxroll") for b in load(s) if match(b, q)]
    hot = [v for s in ("videos_hot_zh", "videos_hot_en", "videos_hot_ja") for v in load(s) if match(v, q)]
    new = [v for s in ("videos_new_zh", "videos_new_en", "videos_new_ja") for v in load(s) if match(v, q)]
    baha = [b for b in load("bahamut") if match(b, q)]
    tweets = sorted(
        (t for s in ("tweets_zh", "tweets_en", "tweets_ja") for t in load(s) if match(t, q)),
        key=lambda t: t.get("date") or "", reverse=True,
    )
    return jsonify({
        "query": q,
        "builds": builds[:30],
        "hot": hot[:20],
        "new": new[:20],
        "bahamut": baha[:20],
        "tweets": tweets[:20],
        "total": len(builds) + len(hot) + len(new) + len(baha) + len(tweets),
    })


@app.get("/data/<path:name>")
def data_files(name):
    return send_from_directory(DATA, name)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8768, debug=False)
