# 配置管理指南 Configuration Management Guide

## 概述 Overview

電力監控儀表板提供了一個完整的 Web 配置介面，讓你可以輕鬆管理 Power BI 連接設定，無需編輯配置文件或環境變數。

## 快速開始 Quick Start

### 1️⃣ 啟動伺服器
```bash
cd backend
python3 main.py
```

### 2️⃣ 訪問配置頁面
開啟瀏覽器，前往：
```
http://localhost:8000/config
```

### 3️⃣ 選擇運行模式
- **Mock 模式**（預設）：使用生成的測試數據
- **Power BI 模式**：連接真實的 Power BI 資料集

## 配置界面說明

配置界面分為三個標籤頁：

### 📊 Mock 模式
- 一鍵切換 Mock/Power BI 模式
- Mock 模式說明和特性
- 無需任何認證信息

### 🔐 Power BI 設定
填入以下信息：
| 字段 | 說明 | 示例 |
|------|------|------|
| **Client ID** | Azure AD 應用程式 ID | `abc12345-1234-1234-1234-abc123456789` |
| **Tenant ID** | Azure AD 租戶 ID | `xyz98765-5678-5678-5678-xyz987654321` |
| **使用者名稱** | Power BI 帳戶或服務帳號 | `powerbi-service@company.onmicrosoft.com` |
| **密碼** | 帳戶密碼（ROPC 流程） | `YourPassword123!` |
| **Dataset ID** | Power BI 資料集 ID | `def45678-abcd-efgh-ijkl-def456789012` |
| **Group ID** | Power BI 工作區/群組 ID | `ghi78901-ijkl-mnop-qrst-ghi789012345` |

### 📈 系統狀態
查看當前系統狀態：
- 伺服器健康狀態
- 運行模式（Mock/Power BI）
- 輪詢間隔
- 伺服器時間

## 工作流程

### 場景 1：使用 Mock 模式（開發/測試）
1. 啟動伺服器 → 自動使用 Mock 模式
2. 訪問 http://localhost:8000 查看儀表板
3. 測試所有功能
4. ✓ 無需任何配置

### 場景 2：切換至 Power BI 模式（生產）
1. 訪問 http://localhost:8000/config
2. 點選「Power BI 設定」標籤
3. 填入 Azure/Power BI 認證信息
4. 點擊「保存設定」→ 信息已加密保存
5. 點擊「切換模式」 → 切換至 Power BI 模式
6. 重啟伺服器使其生效
7. ✓ 系統開始從 Power BI 拉取真實數據

### 場景 3：測試 Power BI 連接
1. 填入完整的 Power BI 認證信息
2. 點擊「測試連接」
3. 等待驗證結果
4. ✓ 設定驗證通過後再點擊「保存設定」

## 配置文件說明

所有設定保存在：
```
backend/powerbi_config.json
```

### 文件結構
```json
{
  "use_mock_data": true,                          // 是否使用 Mock 模式
  "powerbi_client_id": "your-client-id",         // Azure Client ID
  "powerbi_tenant_id": "your-tenant-id",         // Azure Tenant ID
  "powerbi_username": "your-username",           // Power BI 帳戶
  "powerbi_password": "encrypted-password",      // 密碼（加密）
  "powerbi_dataset_id": "your-dataset-id",       // Power BI Dataset ID
  "powerbi_group_id": "your-group-id"            // Power BI Group ID
}
```

### 直接編輯配置文件
你也可以直接編輯 `powerbi_config.json`：
```bash
nano backend/powerbi_config.json
```

編輯完成後，重啟伺服器即可生效。

## API 端點參考

### GET /api/config
取得當前配置（密碼會被掩蓋）
```bash
curl http://localhost:8000/api/config
```

### POST /api/config
保存配置
```bash
curl -X POST http://localhost:8000/api/config \
  -H "Content-Type: application/json" \
  -d '{...}'
```

### POST /api/config/set-mode
切換運行模式
```bash
curl -X POST http://localhost:8000/api/config/set-mode \
  -H "Content-Type: application/json" \
  -d '{"use_mock_data": false}'
```

### POST /api/config/test-connection
測試 Power BI 連接
```bash
curl -X POST http://localhost:8000/api/config/test-connection \
  -H "Content-Type: application/json" \
  -d '{...}'
```

### POST /api/config/reset-db
清除所有資料庫數據
```bash
curl -X POST http://localhost:8000/api/config/reset-db
```

## Power BI 設置步驟

### 步驟 1：在 Azure Portal 註冊應用程式

1. 訪問 [Azure Portal](https://portal.azure.com)
2. 導航到 **Azure Active Directory** → **應用程式註冊**
3. 點擊 **新增註冊**
4. 填入應用程式名稱（如 "PowerMonitoring"）
5. 選擇 **僅限此組織目錄中的帳戶**
6. 點擊 **註冊**
7. **複製並保存：**
   - **應用程式 (用戶端) ID** → 填入 Client ID
   - **目錄 (租戶) ID** → 填入 Tenant ID

### 步驟 2：設置客戶端密碼

1. 在應用程式頁面，點擊 **憑證和密碼**
2. 點擊 **新增客戶端密碼**
3. 描述：`PowerMonitoring App Secret`
4. 過期時間：根據需要選擇
5. 點擊 **新增**
6. **複製密碼值** → 此值只會顯示一次
7. 將其保存（稍後在配置中使用）

### 步驟 3：在 Power BI 中授予權限

1. 訪問 [Power BI Admin Portal](https://app.powerbi.com/admin-portal)
2. 導航到 **租戶設定** → **開發人員設定**
3. 啟用 **允許服務主體使用 Power BI API**
4. 找到你的應用程式並設定為「允許 API 存取」

### 步驟 4：獲取 Dataset 和 Group ID

1. 訪問 [Power BI Web](https://app.powerbi.com)
2. 選擇你的工作區
3. 查看 URL，其中包含 **Group ID**
4. 選擇資料集 → URL 中包含 **Dataset ID**
5. **複製並保存** 這兩個 ID

### 步驟 5：在配置介面填入信息

1. 訪問 http://localhost:8000/config
2. 切換到「Power BI 設定」標籤
3. 填入所有必需信息
4. 點擊「測試連接」驗證
5. 點擊「保存設定」
6. 點擊「切換模式」切換至 Power BI 模式
7. 重啟伺服器：`python3 main.py`

## 故障排除

### 問題：配置無法保存
- ✓ 確認伺服器正在運行
- ✓ 檢查浏覽器控制台是否有錯誤
- ✓ 確認後端目錄有寫入權限

### 問題：Power BI 連接失敗
- ✓ 驗證所有認證信息是否正確
- ✓ 確認 Azure AD 應用程式擁有 Power BI API 權限
- ✓ 檢查帳戶是否有相應資料集的訪問權限
- ✓ 查看伺服器日誌：`tail -f /tmp/server.log`

### 問題：模式切換後伺服器仍使用舊配置
- ✓ 重啟伺服器：`python3 main.py`
- ✓ 伺服器會在啟動時讀取最新配置

### 問題：忘記密碼
- 配置文件中的密碼會被掩蓋
- 直接編輯 `powerbi_config.json` 重新設置
- 或使用配置介面重新填入

## 安全建議

1. **使用服務帳號**：建議為 Power BI 連接建立專用服務帳號，而非使用個人帳戶
2. **密碼管理**：定期更改 Azure 客戶端密碼
3. **權限最小化**：只授予服務帳號必需的 Power BI 資料集訪問權限
4. **配置文件安全**：`powerbi_config.json` 包含敏感信息，不要提交到公開倉庫
5. **HTTPS**：在生產環境中使用 HTTPS 加密配置傳輸

## 高級用法

### 批量導入配置
如果有多個伺服器需要相同配置，可以：
1. 在一台伺服器配置好 `powerbi_config.json`
2. 複製此文件到其他伺服器的 `backend/` 目錄
3. 重啟伺服器

### 環境變數覆蓋（可選）
未來版本可能支援通過環境變數覆蓋配置：
```bash
export POWERBI_CLIENT_ID=your-id
export POWERBI_TENANT_ID=your-id
python3 main.py
```

## 總結

| 功能 | Mock 模式 | Power BI 模式 |
|------|---------|-----------|
| 配置難度 | ✓ 無需配置 | 需要 6 個信息 |
| 數據來源 | 生成的測試數據 | 真實 Power BI 資料 |
| 適用場景 | 開發/測試 | 生產環境 |
| 設置時間 | 立即使用 | 30-60 分鐘 |
| 可靠性 | 100%（無外部依賴） | 取決於 Power BI 連接 |

祝你使用愉快！有問題可查看日誌或聯繫技術支援。
