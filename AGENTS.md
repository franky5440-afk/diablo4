# diablo4 專案規範

暗黑破壞神4（Diablo 4）攻略聚合站。Flask 本機版 + GitHub Pages 線上版共用同一套前端與資料。
架構複製自 `franky5440-afk/poe2`；劇情小說掛載對齊 `nioh3`。

## 語言

一律使用繁體中文回覆。程式碼、指令、變數名稱維持英文。

## 架構與資料流

```
scraper.py ──> data/*.json ──> build_site.py ──> site/（靜態站，Pages artifact）
                     │
                     └──> app.py（Flask 本機版，直接讀 data/）
```

- `data/*.json` 是唯一資料來源
- `site/` 已列入 `.gitignore`，**絕不 commit**
- 本機埠 **8768**（poe2=8766，nioh3 歷史 8765/8767）
- **不要**新增遊戲資料／item／skill DB tab

## BD 來源

1. **d2core（意圖主來源）**：SPA + `ACCESS_TOKEN_EMPTY` → 常空；保留 scraper hook
2. **Maxroll**（v1 live）：SSR HTML `/d4/build-guides`，略過職業 hub
3. **Mobalytics**（v1 live）：`POST /api/diablo-4/v1/graphql/query`，cloudscraper；expert tag 常 0 筆時改無 tag TRENDING

## 影片

`GAME_TERMS`：Diablo 4 / Diablo IV / 暗黑破壞神4 / 暗黑4 / D4。邏輯同 poe2（yt-dlp flat + RSS）。

## 巴哈

`bsn=75105`（暗黑破壞神 4 哈啦板）。跳過置頂／精華列。

## 劇情小說

`content/story/*.md` → `build_site.py` → `data/story.json`。v1 可空。

## Hero

`static/hero-lilith.webp` 抽象 placeholder；Nelli 正式立繪第二輪。

## Commit

中文 commit messages。
