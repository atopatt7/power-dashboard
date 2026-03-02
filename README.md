# 電力監控儀表板 Power Consumption Monitoring Dashboard

## 專案結構

```
├── backend/
│   ├── main.py            # HTTP 伺服器 + 排程器（Python stdlib）
│   ├── config.py          # 設定檔（設備群組、Power BI 參數）
│   ├── database.py        # SQLite 資料層
│   ├── mock_data.py       # Mock 資料產生器
│   ├── powerbi_client.py  # Power BI REST API 客戶端（第二階段啟用）
│   └── requirements.txt   # 額外依賴（接 Power BI 時需要）
├── frontend/
│   └── index.html         # React + Recharts 單頁儀表板
└── README.md
```

## 快速啟動（Mock 模式）

```bash
cd backend
python3 main.py
```

開啟瀏覽器前往 http://localhost:8000

## API 端點

| 端點 | 說明 |
|------|------|
| `GET /api/power-latest` | 每台設備最新一筆數值 |
| `GET /api/power-history?device=&start=&end=&limit=` | 歷史功率查詢 |
| `GET /api/devices` | 設備列表與群組 |
| `GET /api/health` | 健康檢查 |

## 設備群組（18 台）

| 群組 | 設備數 | 設備清單 |
|------|--------|--------|
| 高壓盤 | 2 | 一號高壓盤、二號高壓盤 |
| 洗砂 | 2 | 臥式洗砂機、立式洗砂機 |
| 集塵 | 3 | P101集塵機、P102集塵機、P103集塵機 |
| 空壓 | 4 | 漢鐘100HP空壓機、向陽100HP空壓機、漢鐘50HP空壓機、凱薩50HP空壓機 |
| 電爐 | 3 | 10T電爐、6T電爐、3T電爐 |
| 辦公室 | 3 | 一樓辦公室、二樓辦公室、三樓辦公室 |
| FMS | 1 | FMS高位震篩機 |

## Frontend 功能（已完成）

✅ **儀表板特色：**
- 🎨 現代化深色主題（類似 Power BI）
- 📱 全響應設計（桌機、平板、手機）
- ⚡ 每 10 秒自動更新
- 📊 實時功率折線圖（1m/5m/30m/1h/6h 時間範圍）
- 🎯 設備群組分類顯示
- 💾 SQLite 自動保存 7 天歷史數據

**頂部 KPI：**
- 總用電量 (kW)
- 在線設備數
- 設備群組數
- 最高用電設備與數值

**設備卡片：**
- 即時功率數值 + 時間戳
- 群組小計
- 點擊卡片查看單一設備趨勢圖

**圖表功能：**
- 多設備對比或單設備詳情
- 自訂時間範圍過濾
- 完整圖例與 Tooltip

## 接入 Power BI（第三階段）

1. 安裝依賴：`pip install msal httpx`
2. 設定環境變數：
   ```bash
   export USE_MOCK_DATA=false
   export POWERBI_CLIENT_ID=your_client_id
   export POWERBI_TENANT_ID=your_tenant_id
   export POWERBI_USERNAME=your_username
   export POWERBI_PASSWORD=your_password
   export POWERBI_DATASET_ID=your_dataset_id
   export POWERBI_GROUP_ID=your_group_id
   ```
3. 修改 `powerbi_client.py` 中的 DAX 查詢以符合你的 Power BI 資料集
4. 重啟伺服器

## 測試 API（本地）

```bash
# 健康檢查
curl http://localhost:8000/api/health

# 獲取所有設備最新數據
curl http://localhost:8000/api/power-latest

# 查詢特定設備歷史數據（過去 30 分鐘）
curl "http://localhost:8000/api/power-history?device=10T電爐&limit=100"

# 查詢時間範圍內的數據
curl "http://localhost:8000/api/power-history?start=2026-02-26T00:00:00&end=2026-02-26T23:59:59"
```

## 故障排除

**問題：無法連線到 Backend**
- 確認伺服器正在運行：`ps aux | grep main.py`
- 檢查埠號：預設 `localhost:8000`

**問題：資料庫鎖定**
- 刪除 `power_data.db*` 檔案並重啟伺服器

**問題：Mock 數據不更新**
- 檢查伺服器日誌：`tail -f /tmp/server.log`
- 確認 `USE_MOCK_DATA=true` 環境變數

## 技術棧

- **Backend**: Python 3 (stdlib only)
- **Frontend**: React 18 + Recharts (CDN)
- **Database**: SQLite 3
- **伺服器**: Python http.server
- **排程**: APScheduler (mock) / Power BI API (生產)
