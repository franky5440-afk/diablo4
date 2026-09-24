# 暗黑破壞神4 攻略武庫 · Diablo 4 Guide Hub

彙整 Diablo 4 Top 10 BD、熱門／最新 YouTube 攻略影片、巴哈姆特討論、X 推文，並預留劇情小說掛載。

- **線上**：https://franky5440-afk.github.io/diablo4/
- **本機埠**：`8768`
- **對標**：`franky5440-afk/poe2`（架構）／劇情掛載參考 `nioh3`

## Tabs（v1）

| Tab | 說明 |
|-----|------|
| 十大 BD | **暗黑核 d2core** Hot Top10（live）＋ Maxroll / Mobalytics 備援 |
| 熱門影片 TOP10 | 近 30 天，zh / en / ja |
| 最新影片 | 依上傳日，zh / en / ja |
| 巴哈討論 | `bsn=75105` 暗黑破壞神 4 哈啦板 |
| X 推文 | `@Diablo` + 搜尋詞 |
| 劇情小說 | stub；`content/story/` → `data/story.json`（Ruth 第二輪） |

**不含**遊戲資料／item／skill DB tab。

## 本機啟動

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./start.sh          # http://127.0.0.1:8768
./stop.sh
./update.sh         # 手動跑 scraper + build
```

## 更新流程

```
scraper.py → data/*.json → build_site.py → site/（Pages artifact）
```

GitHub Actions：每日 UTC 00:00（`deploy.yml`）跑 scraper、建站、部署 Pages。

首次啟用 Pages：Repo → Settings → Pages → Source = **GitHub Actions**。

## BD 來源說明

- **主來源（live）**：暗黑核 https://www.d2core.com/d4/builds
  - **不要**打 `api.d2core.com`（會回 `ACCESS_TOKEN_EMPTY`，錯誤路徑）
  - 正確：騰訊雲 CloudBase `POST tcb-api.tencentcloudapi.com/web?env=diablocore-…`
  - 雲函數 `function-planner-queryplanlist`，Hot 排序 `rawScore`，S15，寫入 `builds_d2core.json`
  - 計畫 URL：`https://www.d2core.com/d4/planner?bd=<_id>`
- **備援**：Maxroll `d4/build-guides`、Mobalytics GraphQL `diablo-4`

## License

Apache-2.0
