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

1. **d2core（主來源 live）**：騰訊雲 CloudBase `function-planner-queryplanlist`（Hot / rawScore，S15）。**勿**打 `api.d2core.com`。詳見 `IMPL_REPORT.md`
2. **Maxroll**（備援）：SSR HTML `/d4/build-guides`，略過職業 hub
3. **Mobalytics**（備援）：`POST /api/diablo-4/v1/graphql/query`，cloudscraper；expert tag 常 0 筆時改無 tag TRENDING

## 影片

`GAME_TERMS`：Diablo 4 / Diablo IV / 暗黑破壞神4 / 暗黑4 / D4。邏輯同 poe2（yt-dlp flat + RSS）。

## 巴哈

`bsn=75105`（暗黑破壞神 4 哈啦板）。跳過置頂／精華列。

## 劇情小說

`content/story/`（本篇扁平）+ `dlc01/` + `dlc02/` → `build_site.py` → `data/story.json`（volumes）。
短標籤：本篇｜憎恨之軀｜憎恨之王。只上架導讀＋章回；勿 publish README／全稿／目錄大綱／99／本節依據。

## Hero

Frank 選定 **Lilith B Reach**：`static/lilith-hero-b-reach.webp` + `*-loop.webp`。
`<picture>`／`prefers-reduced-motion`／16:9／標題右側暗部；**禁止** nioh3 `.halo`。

## Commit

中文 commit messages。
