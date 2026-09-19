---
name: alfa-wireless-diagnosis
description: >-
  Expert instructions for controlling and diagnosing the ALFA Network AWUS036AXML Wi-Fi 6E (MT7921AU) adapter.
  Covers AP/Client mode switching, 2T2R dual-antenna telemetry, regulatory domain (country US / NO-IR removal),
  station parsing, and wireless packet inspection.
---

# ALFA AWUS036AXML 無線診斷專家技能 (SKILL)

本技能提供控制 **ALFA Network AWUS036AXML (MediaTek MT7921AU)** 高功率 Wi-Fi 6E 網路卡之標準作業程序（SOP）、硬體規格參數與診斷診斷技術指南。

---

## 1. 網路卡硬體與驅動規格

* **晶片型號**：MediaTek MT7921AU / MT7961
* **介面名稱**：`wlx00c0cabb0b45` (USB 3.0 / USB 2.0 相容)
* **驅動模組**：`mt7921u` (Linux 核心內建支援)
* **天線配置**：2T2R 雙外接 RP-SMA 雙天線，支援 802.11ax (Wi-Fi 6E)、802.11ac (Wi-Fi 5) 與 802.11n。
* **支援頻譜**：2.4GHz、5GHz (UNII-1 ~ UNII-3)、6GHz (僅限 Client / Monitor 模式)。

---

## 2. 模式切換操作程序

切換腳本位於 `~/alfa-wifi-mode.sh`，亦可透過後端 `main.py` 的 `/api/mode/switch` 呼叫：

### 2.1 啟動 DiagnosticAP 熱點模式 (AP Mode)
```bash
# 啟動 5GHz 熱點 (預設頻道 36)
alfa-mode ap 5G 36

# 啟動 5GHz 高頻 UNII-3 熱點 (頻道 149，最大功率 30 dBm)
alfa-mode ap 5G 149

# 啟動 2.4GHz 熱點 (頻道 6)
alfa-mode ap 2.4G 6
```
* **運作機制**：透過 NetworkManager 建立 `type wifi mode ap` 的 Shared 連線，自動喚醒本機 `dnsmasq` 提供 `10.42.0.0/24` DHCP 與本機 DNS 解析。

### 2.2 切換為 Client 備援模式
```bash
alfa-mode client
```
* **注意事項**：Client 模式下網路連線度量（Metric）必須維持 `700`，確保不會覆蓋主力網卡 (`wlxd03745e1db0d`, Metric 100) 之預設路由。

### 2.3 停止熱點
```bash
alfa-mode stop
```

---

## 3. 無線法規與 5GHz 發射限制解除 (`country US`)

在預設法規區域（`country 00`），Linux 核心將 5GHz 與 6GHz 標註為 `NO-IR` (No Initiating Radiation)，禁止建立 Master AP。
* **解鎖為 `country US`**：
  ```bash
  sudo iw reg set US
  ```
* **法規固化檢驗**：
  ```bash
  iw reg get | grep country
  ```
  應輸出 `country US: DFS-FCC`。

---

## 4. 2T2R 雙天線即時射頻遙測解析

透過 `iw dev wlx00c0cabb0b45 station dump` 擷取數值：
* **雙天線訊號格式**：
  `signal: -65 [-66, -71] dBm`
  * `-65` 為雙天線平均訊號。
  * `[-66, -71]` 分別對應 Antenna 1 與 Antenna 2 之即時接收強度。
* **封包重傳 (Tx Retries)**：
  `tx retries: <count>` 數值若持續飆升，代表空中介質有嚴重的同頻競爭或訊號衰減。

---

## 5. 空中通訊協定側錄 (tcpdump) 指令

在診斷熱點介面上執行非阻斷式側錄：
```bash
# 側錄 DHCP 四向交握 (UDP 67/68)
sudo tcpdump -i wlx00c0cabb0b45 -n "port 67 or port 68" -v

# 側錄 DNS 查詢 (UDP 53)
sudo tcpdump -i wlx00c0cabb0b45 -n "port 53" -c 20

# 側錄 mDNS (Bonjour, UDP 5353)
sudo tcpdump -i wlx00c0cabb0b45 -n "udp port 5353"
```
