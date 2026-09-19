---
name: taiwan-localization-guide
description: >-
  Strict Taiwanese Traditional Chinese (zh-TW) terminology and localization guidelines
  for wireless networking, communications engineering, and software development.
---

# 臺灣正體中文通訊與網路名詞審校指南 (SKILL)

本技能提供本專案所有程式碼、註解、UI 介面與文件之臺灣繁體 / 正體中文（zh-TW）審校標準。任何 AI Agent 接手開發時，**必須 100% 依循此對照表**，嚴禁使用中國大陸簡體直譯或普通話術語。

---

## 🔤 核心專有名詞標準對照表

| 英文原詞 (English) | 臺灣正體中文 (zh-TW) ✅ | 嚴格禁止使用之用語 ❌ |
| :--- | :--- | :--- |
| **Network Interface Card (NIC)** | **網路卡** | 網卡 |
| **Air Interface** | **空中介面** | 空口 |
| **Client / Station (STA)** | **用戶端裝置 / 工作站** | 客戶端、客戶端終端 |
| **Randomized MAC Address** | **隨機 MAC 位址** | 隨機MAC、軟MAC |
| **Private Wi-Fi Address** | **專用 Wi-Fi 位址** | 私密地址、專用地址 |
| **Access Point (AP)** | **基地台 / 無線基地台 / 熱點** | 接入點、熱點AP (不翻譯) |
| **Default Gateway** | **預設閘道** | 默認網關、默認網關地址 |
| **Default** | **預設** | 默認 |
| **Packet** | **封包** | 數據包、包 |
| **Frame** | **訊框** | 幀、數據幀 |
| **Packet Capture / Sniffing** | **封包側錄 / 封包擷取** | 抓包、抓取網絡包 |
| **Bandwidth** | **頻寬** | 帶寬 |
| **Throughput** | **吞吐量 / 淨傳輸量** | 吞吐率 |
| **Latency / Delay** | **延遲 / 往返時延** | 時延、延時 |
| **Jitter** | **抖動 / 訊號抖動** | 抖動率 |
| **Retries** | **重傳 / 重新傳送** | 重試、重發 |
| **Hostname** | **主機名稱** | 主機名 |
| **Vendor / Manufacturer** | **製造商 / 廠牌** | 廠商 (視語境)、生產商 |
| **Link / Connection** | **連線 / 連結** | 連接、鏈接 |
| **Byte** | **位元組** | 字節 |
| **Bit** | **位元** | 比特 |
| **Cache** | **快取** | 緩存 |
| **Socket** | **通訊端 / 通訊端點** | 套接字 |
| **Port** | **連接埠** | 端口 |
| **Process** | **行程** | 進程 |
| **Thread** | **執行緒** | 線程 |
| **Support** | **支援** | 支持 |
| **Optimize** | **最佳化** | 優化 |
| **Hardware** | **硬體** | 硬件 |
| **Software** | **軟體** | 軟件 |
| **App / Application** | **應用程式 / App** | 應用程序、軟件包 |
| **Interface** | **介面** | 接口 |

---

## ✍️ 文風與語境原則

1. **技術精確**：標題與指示句採用主動語態（如「執行 Ping 診斷」、「切換為 5GHz 基地台」）。
2. **警示層級明確**：
   * 💡 **提示 (Tip)**
   * ℹ️ **資訊 (Info)**
   * ⚠️ **警告 (Warning)**
   * 🛑 **危險 / 鐵律 (Danger / Restriction)**
3. **排版標準**：
   * 中文字與英數字元之間保留半形空格（如 `5GHz 頻段`、`MCS 15 調變`、`共 19 個熱點`）。
   * 標點符號一律使用全形中文標點（，、。！？：；）。
