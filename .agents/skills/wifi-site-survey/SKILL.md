---
name: wifi-site-survey
description: >-
  Standard operating procedures for Wi-Fi site survey, environmental AP scanning,
  spectrum congestion analysis, and channel interference assessment using NetworkManager and iw.
---

# Wi-Fi 站點調查與周遭熱點掃描專家技能 (SKILL)

本技能指導如何在 Linux 環境下進行非破壞性（Non-disruptive）之周遭 Wi-Fi 熱點基地台掃描、頻段擁擠度評估、WPA2/WPA3 安全性審查與 IEEE OUI 廠牌比對。

---

## 1. 非破壞性掃描核心原理

當 ALFA 網路卡正在擔任 AP（發射 Beacon 與轉發封包）時，若強制在該介面上執行 `iw scan`，會導致核心回傳 `Device or resource busy (-EBUSY)` 或造成已連線手機斷線。
* **最佳實踐**：利用 NetworkManager 聚合掃描介面：
  ```bash
  # 快速讀取最新掃描快取 (延遲僅約 30ms，零斷線風險)
  nmcli -t -f IN-USE,BSSID,SSID,MODE,CHAN,FREQ,RATE,SIGNAL,BARS,SECURITY dev wifi list --rescan no

  # 觸發主動更新掃描 (耗時約 2~5 秒)
  nmcli dev wifi rescan
  ```

---

## 2. 欄位解析與資料結構標準

透過 `nmcli` 獲取之欄位定義：
1. **IN-USE**：`*` 代表本機網路介面當前正連線至該 AP。
2. **BSSID**：基地台實體/虛擬 MAC 位址（例如 `00:C0:CA:BB:0B:45`）。
3. **SSID**：網路識別名稱。若為空則標註為 `[隱藏 SSID / Hidden]`。
4. **CHAN / FREQ**：
   * 2.4GHz：頻率 2412 ~ 2484 MHz（頻道 1 ~ 14）。
   * 5GHz：頻率 5180 ~ 5825 MHz（UNII-1 Ch 36~48、UNII-3 Ch 149~165）。
   * 6GHz：頻率 5925 ~ 7125 MHz。
5. **SIGNAL / BARS**：訊號品質百分比 (0~100%)。
   * 估算 dBm 換算公式：`dBm = (SIGNAL_PERCENT / 2) - 100`。
6. **SECURITY**：
   * `WPA3` / `WPA3-SAE`：最高安全性（防離線字典檔攻擊）。
   * `WPA2` / `WPA1 WPA2`：現行普遍標準。
   * `--` 或空值：`開放無密碼 (Open)`，具資安風險。
7. **VENDOR (製造商)**：
   * 透過比對 BSSID 前 6 碼十六進位至 IEEE OUI 資料庫獲取廠牌（如 TP-Link, ASUSTek, Cisco, Apple, D-Link 等）。

---

## 3. 頻道干擾與最佳頻道評估準則

* **2.4GHz 頻段**：
  * 僅推薦使用互不干擾的 **頻道 1、6、11**。
  * 統計各頻道的 AP 數量與 RSSI 訊號強度，選取佔用量最少者。
* **5GHz 頻段**：
  * **UNII-1 (Ch 36~48)**：乾淨、室內衰減小，推薦 80MHz 頻寬（例如 Ch 36, 40, 44, 48）。
  * **UNII-3 (Ch 149~165)**：功率上限高達 1000mW，穿透力與傳輸距離佳。
  * **DFS 頻道 (Ch 52~144)**：可能遭遇氣象雷達偵測而強制靜默退讓。
