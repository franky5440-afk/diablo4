# IMPL Report — d2core Top10（CloudBase）

**日期**：2026-09-17（Asia/Taipei）  
**狀態**：live — `scrape_d2core()` 寫入 `data/builds_d2core.json`（≥10）

## 錯誤路徑（勿再用）

`GET https://api.d2core.com/...` → `ACCESS_TOKEN_EMPTY`。  
那是登入 API，不是公開列表端點；**永遠不要**再打 `api.d2core.com` 當 BD 列表來源。

## 正確路徑（SPA 公開憑證重放）

SPA（www.d2core.com）透過騰訊雲 CloudBase 呼叫雲函數。憑證在前端 JS 公開：

| 項目 | 值 |
|------|-----|
| ENV | `diablocore-4gkv4qjs9c6a0b40` |
| Endpoint | `POST https://tcb-api.tencentcloudapi.com/web?env=<ENV>` |
| Function | `function-planner-queryplanlist` |
| dataVersion | `2020-01-10` |
| appSign | `diablocore` |
| appAccessKeyId | `1` |
| appAccessKey | `ed6fe96e6ca08acf392d360094a58477`（SPA public） |
| D4 season | `15`（`DEFAULT_BUILD_SEASON_BY_GAME.d4`） |

### Header

`X-TCB-App-Source: timestamp=<ms>;appAccessKeyId=1;appSign=diablocore;sign=<JWT>`

JWT = HS256，payload `{"data":{},"timestamp":<ms>,"appAccessKeyId":1,"appSign":"diablocore"}`，key = `appAccessKey`。

### Body

```json
{
  "action": "functions.invokeFunction",
  "dataVersion": "2020-01-10",
  "env": "diablocore-4gkv4qjs9c6a0b40",
  "function_name": "function-planner-queryplanlist",
  "request_data": "<stringified params>"
}
```

Hot Top10 `request_data`：

```json
{
  "pageIndex": 1,
  "pageSize": 10,
  "condition": {"game": "d4", "season": 15},
  "orderBy": ["rawScore", "desc", "_createTime", "desc"],
  "enableVariant": true,
  "token": ""
}
```

### 解析

`response.data.response_data` 是 **JSON 字串** → parse → `data[]`（`_id`, `title`, `char`, `description`, …）。  
Build URL：`https://www.d2core.com/d4/planner?bd=<_id>`。

### 程式位置

- `scraper.py`：`scrape_d2core()` / `_d2core_tcb_app_source()`
- 備援不變：`scrape_maxroll()`、`scrape_mobalytics()`；失敗時 `update_builds` 保留舊 JSON

### UI

十大 BD 預設 pill = 暗黑核 d2core；Maxroll / Mobalytics 仍可切換。
