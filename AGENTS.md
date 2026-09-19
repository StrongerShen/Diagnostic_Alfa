# 🤖 Diagnostic_Alfa - AI Coding Agents 開發指南 (AGENTS.md)

本文件專為 **Gemini Agy CLI**、**Codex CLI**、**Claude CLI** 及各類 AI Pair Programming 助理設計。任何接手本專案之 AI Agent **必須嚴格遵守**本文件所列之系統架構、安全隔離原則、臺灣正體中文規範與開發準則。

---

## 📌 1. 專案定位與硬體雙網卡拓撲

### 1.1 專案核心定位
`Diagnostic_Alfa` 專門為 **ALFA Network AWUS036AXML (聯發科 MediaTek MT7921AU / MT7961, Wi-Fi 6E)** 打造之全頻段無線通訊診斷、即時射頻遙測、Wi-Fi 站點調查（Site Survey）與熱點 AP 控制工作台。

### 1.2 雙網路卡硬體分工與最高安全隔離原則
主機同時搭載兩張無線網路卡，各自肩負嚴格區隔之任務：
1. **主力對外連線網卡 (`wlxd03745e1db0d`)**：
   * **角色**：專職連接外部網際網路，並透過 `iptables` 提供 NAT IP 偽裝（Masquerade）與封包轉送。
   * **路由度量**：Metric 100（預設閘道優先權最高）。
   * ⚠️ **【鐵律】絕不可中斷、關閉（down）、重置或更動此網路卡的 IP 與路由設定**，否則將導致本機網際網路完全斷線。
2. **ALFA 診斷測試網卡 (`wlx00c0cabb0b45`)**：
   * **角色**：專職作為診斷基地台（Diagnostic AP）、空口封包側錄、周遭熱點 AP 掃描或 Client 備援模式。
   * **路由度量**：若處於 Client 模式時 Metric 設為 700（絕不搶佔主力網卡流量）。

---

## 🛡️ 2. Coding Agent 行為守則與鐵律

1. **語言純度標準（100% 臺灣正體中文）**：
   * 本專案全數註解、UI 顯示文字、Log 輸出與說明文件，**一律使用臺灣正體中文（zh-TW）**。
   * 嚴格禁止使用任何中國大陸用語或機器直譯詞彙（如嚴禁「空口」、「網卡」、「默認」、「客戶端」、「抓包」、「套接字」、「鏈接」等）。
   * 專有名詞標準請參照 `.agents/skills/taiwan-localization-guide/SKILL.md`。
2. **去識別化與隱私安全（De-identification）**：
   * 本專案已開源推播至公開 GitHub Repo。
   * **嚴禁在程式碼、設定檔或 Commit 中寫入使用者真實私有 SSID、個人 Wi-Fi 密碼、內部私有網域名稱或個人實體硬體 MAC**。
   * 範例一律使用去識別化佔位符（如 `DiagnosticAP`、`88888888`、`<interface>`、`<Client-MAC>`）。
3. **變更驗證與無損熱重載**：
   * 修改後端後必須執行語法檢查：`python3 -m py_compile main.py`。
   * 前端使用原生 HTML5 + Tailwind CSS + Lucide Icons + Chart.js，嚴禁引入龐大複雜之編譯鏈（如 Webpack/Vite），確保開箱即用。
   * 修改前後確保現有 5 大實戰模組、學習手冊、主題切換與連線裝置解析功能不受影響。

---

## 📂 3. 專案結構與關鍵檔案索引

```
Diagnostic_Alfa/
├── AGENTS.md                  # 本開發指南 (Gemini Agy / Codex / Claude CLI 共通)
├── CLAUDE.md                  # Claude CLI 專用導引
├── GEMINI.md                  # Gemini Agy CLI 專用導引
├── README.md                  # 專案公開說明文件 (去識別化)
├── main.py                    # FastAPI 後端、WebSocket 遙測推播、OUI/Hostname 解析、AP 掃描 API
├── run.sh                     # 一鍵環境檢查、依賴安裝與 Web 伺服器啟動腳本 (Port 8080)
├── requirements.txt           # Python 輕量依賴 (fastapi, uvicorn, pydantic, psutil)
├── static/
│   ├── index.html             # 響應式單頁診斷儀表板 (Dark/Light 雙主題、QR Code、互動模組)
│   └── app.js                 # 前端 WebSocket 狀態同步、Chart.js 折線圖、互動邏輯
└── .agents/
    └── skills/                # 專案專屬 AI 專家技能庫
        ├── alfa-wireless-diagnosis/SKILL.md  # ALFA 射頻遙測、模式切換與天線解析技能
        ├── wifi-site-survey/SKILL.md         # 周遭熱點掃描、頻段評估與干擾分析技能
        └── taiwan-localization-guide/SKILL.md # 臺灣正體中文通訊名詞審校指南
```

---

## 🛠️ 4. 常用維運與開發指令

### 啟動與重啟服務
```bash
# 一鍵啟動 (自動建立 .venv、檢查依賴、釋放 Port 8080 並啟動 Uvicorn)
./run.sh

# 手動背景重啟
kill $(lsof -ti :8080) 2>/dev/null || true
.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8080 --no-access-log &
```

### 驗證與健康檢查
```bash
# 1. 檢查 Python 語法
python3 -m py_compile main.py

# 2. 測試即時遙測 API
curl -s http://localhost:8080/api/status | jq .interface

# 3. 測試已連線裝置解析 (含 Hostname 與隨機 MAC 偵測)
curl -s http://localhost:8080/api/status | jq .stations

# 4. 測試周遭熱點 AP 快速掃描
nmcli -t -f IN-USE,BSSID,SSID,MODE,CHAN,FREQ,RATE,SIGNAL,BARS,SECURITY dev wifi list --rescan no
```

---

## 🧠 5. 專案專屬技能庫 (Project Skills)

Agent 進行特定任務時，請閱讀或呼叫下列技能指引：
* **`alfa-wireless-diagnosis`**：處理 `iw`、`wpa_supplicant`、`hostapd`、天線訊號 `[Ant1, Ant2]`、法規 `country US` (解除 NO-IR) 與封包側錄。
* **`wifi-site-survey`**：處理周遭 Wi-Fi AP 站點掃描、頻道干擾雷達、WPA2/WPA3 安全分析與 OUI 廠牌匹配。
* **`taiwan-localization-guide`**：通訊領域正體中文專有名詞標準對照字典。
