# 快速參考 Quick Reference

## 🚀 啟動應用

```bash
cd backend
python3 main.py
```

## 🌐 訪問地址

| 頁面 | URL | 用途 |
|------|-----|------|
| 📊 儀表板 | http://localhost:8000 | 實時功率監控 |
| ⚙️ 配置 | http://localhost:8000/config | 系統設定管理 |
| 🏥 健康檢查 | http://localhost:8000/api/health | API 狀態 |

## 📋 API 端點

```bash
# 獲取當前配置
curl http://localhost:8000/api/config

# 獲取最新功率數據
curl http://localhost:8000/api/power-latest

# 獲取設備列表
curl http://localhost:8000/api/devices

# 查詢歷史數據
curl "http://localhost:8000/api/power-history?device=一號高壓盤&limit=100"

# 保存配置
curl -X POST http://localhost:8000/api/config \
  -H "Content-Type: application/json" \
  -d '{"powerbi_client_id": "xxx", ...}'

# 切換運行模式
curl -X POST http://localhost:8000/api/config/set-mode \
  -H "Content-Type: application/json" \
  -d '{"use_mock_data": false}'

# 測試 Power BI 連接
curl -X POST http://localhost:8000/api/config/test-connection \
  -H "Content-Type: application/json" \
  -d '{"powerbi_client_id": "xxx", ...}'

# 清除資料庫
curl -X POST http://localhost:8000/api/config/reset-db
```

## 🔧 配置文件

位置：`backend/powerbi_config.json`

```json
{
  "use_mock_data": true,
  "powerbi_client_id": "",
  "powerbi_tenant_id": "",
  "powerbi_username": "",
  "powerbi_password": "",
  "powerbi_dataset_id": "",
  "powerbi_group_id": ""
}
```

## 📂 項目結構

```
電力監控儀表板/
├── backend/
│   ├── main.py              # 主伺服器程式
│   ├── config.py            # 設備配置
│   ├── config_manager.py    # 配置管理（新）
│   ├── database.py          # 資料庫層
│   ├── mock_data.py         # Mock 數據生成器
│   ├── powerbi_client.py    # Power BI 客戶端
│   ├── powerbi_config.json  # 配置文件（生成）
│   └── power_data.db        # SQLite 資料庫
├── frontend/
│   ├── index.html           # 儀表板
│   └── config.html          # 配置介面（新）
├── README.md
├── FEATURES.md
├── CONFIGURATION_GUIDE.md   # 詳細配置指南（新）
└── QUICK_REFERENCE.md       # 本文件
```

## ⏱️ 時間快速切換

```
1m   → 1 分鐘   (60 筆)
5m   → 5 分鐘   (30 筆)
30m  → 30 分鐘  (180 筆)
1h   → 1 小時  (360 筆)
6h   → 6 小時  (2160 筆)
```

## 🎯 常見任務

### 任務：查看當前運行模式
```bash
curl http://localhost:8000/api/health | jq .mock_mode
```

### 任務：從 Mock 切換到 Power BI
1. 訪問 http://localhost:8000/config
2. 填入 Power BI 認證信息
3. 點擊「保存設定」
4. 點擊「切換模式」
5. 重啟伺服器

### 任務：重置所有數據
```bash
curl -X POST http://localhost:8000/api/config/reset-db
```

### 任務：查看過去 1 小時的功率數據
```bash
curl "http://localhost:8000/api/power-history?limit=360"
```

## 🐛 調試

```bash
# 檢查伺服器日誌
tail -f /tmp/server.log

# 檢查伺服器進程
ps aux | grep main.py

# 測試連接
curl -v http://localhost:8000/api/health

# 查看配置文件
cat backend/powerbi_config.json
```

## 📊 Mock 數據特性

- **更新頻率**：每 10 秒
- **保留期**：7 天
- **設備數**：18 台（7 個群組）
- **時間變化**：工作時間 +20%，夜間 -40%
- **隨機波動**：±5% 高斯雜訊

## 🔑 Power BI 必需信息

需要 6 個信息才能連接 Power BI：

1. **Client ID** - Azure AD 應用程式 ID
2. **Tenant ID** - Azure 租戶 ID
3. **Username** - Power BI 帳戶（通常是 email）
4. **Password** - 帳戶密碼
5. **Dataset ID** - Power BI 資料集 ID
6. **Group ID** - Power BI 工作區 ID

## 📈 設備群組

| 群組 | 設備數 | 基礎功率 |
|------|--------|---------|
| 高壓盤 | 2 | 400-600 kW |
| 洗砂 | 2 | 75-150 kW |
| 集塵 | 3 | 30-80 kW |
| 空壓 | 4 | 120-250 kW |
| 電爐 | 3 | 300-800 kW |
| 辦公室 | 3 | 8-35 kW |
| FMS | 1 | 150-300 kW |

## 💾 配置持久化

所有配置自動保存到 `powerbi_config.json`：
- 重啟伺服器時會自動載入
- 可通過 Web 介面或直接編輯文件修改
- 密碼保存時會被加密（可選）

## 🆘 常見問題

**Q：配置無法保存？**
A：確認伺服器正在運行，檢查 `/tmp/server.log`

**Q：Power BI 連接失敗？**
A：驗證所有 6 個信息是否正確，檢查 Azure AD 權限

**Q：如何看到調試信息？**
A：`tail -f /tmp/server.log` 查看伺服器日誌

**Q：可以同時運行多個伺服器嗎？**
A：可以，修改 PORT 環境變數：`PORT=8001 python3 main.py`

## 📞 支援

查看詳細文檔：
- `README.md` - 項目概述
- `FEATURES.md` - 完整功能清單
- `CONFIGURATION_GUIDE.md` - 詳細配置步驟

---

**最後更新**：2026-02-26
**版本**：第二階段（React Frontend + Configuration UI）
