# 📡 Diagnostic_Alfa - ALFA AWUS036AXML 全頻段無線診斷平台

> **專案定位**：專門針對 **ALFA Network AWUS036AXML (聯發科 MediaTek MT7921AU / Wi-Fi 6E)** 無線網路卡打造之全頻段無線診斷、即時射頻分析、極限測速與熱點 AP 控制工作台。  
> **啟動腳本**：`./run.sh`  
> **授權協議**：MIT License

---

## 📑 目錄

1. [專案簡介與特色](#1-專案簡介與特色)
2. [無線法規區域 (US) 與解除 5G 發射限制](#2-無線法規區域-us-與解除-5g-發射限制)
3. [Web 診斷操作台快速啟動 (run.sh)](#3-web-診斷操作台快速啟動-runsh)
4. [連線裝置智慧辨識與射頻遙測 (Connected Stations)](#4-連線裝置智慧辨識與射頻遙測-connected-stations)
5. [六大 Diagnostic 實戰診斷專題](#5-六大-diagnostic-實戰診斷專題)
   - [診斷一：往返延遲與無線抖動測試 (Ping Latency & Jitter)](#診斷一往返延遲與無線抖動測試-ping-latency--jitter)
   - [診斷二：實機極限吞吐量測速 (Web Speedtest & iPerf3)](#診斷二實機極限吞吐量測速-web-speedtest--iperf3)
   - [診斷三：即時動態訊號衰減折線圖 (Live RSSI & Rate Adaptation)](#診斷三即時動態訊號衰減折線圖-live-rssi--rate-adaptation)
   - [診斷四：周遭熱點基地台掃描 (Wi-Fi Site Survey & AP Scanner)](#診斷四周遭熱點基地台掃描-wi-fi-site-survey--ap-scanner)
   - [診斷五：空中通訊協定與封包側錄 (Packet Capture & Wireshark)](#診斷五空中通訊協定與封包側錄-packet-capture--wireshark)
   - [診斷六：頻段與頻道抗干擾評估 (RF Band & Channel Comparison)](#診斷六頻段與頻道抗干擾評估-rf-band--channel-comparison)
6. [無線網路學習手冊與射頻理論實戰指南](#6-無線網路學習手冊與射頻理論實戰指南)
7. [CLI 命令列速查手冊 (alfa-mode & iw)](#7-cli-命令列速查手冊-alfa-mode--iw)
8. [AI Coding Agent 規範與專案技能 (AGENTS.md)](#8-ai-coding-agent-規範與專案技能-agentsmd)

---

## 1. 專案簡介與特色

`Diagnostic_Alfa` 是一個專門針對 **ALFA Network AWUS036AXML (聯發科 MediaTek MT7921AU / MT7961)** 高功率 Wi-Fi 6E 無線網路卡打造的即時無線診斷與熱點 AP 控制工作台。

### ✨ 核心亮點
* **多網路卡/雙網卡協同架構**：系統主力對外網卡（Primary Uplink）專職對外連網並提供 NAT 轉送；ALFA 網路卡可隨時切換為獨立診斷熱點基地台（Diagnostic AP）或 Client 備援上網，彼此路由度量（Metric）隔離互不干擾。
* **連線裝置智慧識別（主機名稱與廠牌辨識）**：整合 **Apple mDNS (Bonjour / Avahi)** 與熱點本機 **DHCP Option 12** 記錄，即時自動反查用戶端裝置主機名稱（如 `Shen-iPhone-16e`、`Pixel-10-Pro`）；內建 42,000+ 筆 IEEE OUI 製造商快取，精準識別現代 iOS / Android 之「隨機私人 MAC (LAA)」防追蹤模式並智慧反推廠牌。
* **周遭熱點站點調查 (Wi-Fi Site Survey & AP 掃描)**：非破壞性背景即時探測空間中所有 2.4GHz / 5GHz / 6GHz 基地台，解析 SSID、頻道、訊號強度（RSSI dBm 與百分比）、WPA2/WPA3 安全防護與 IEEE OUI 製造商，並智慧評估頻譜頻道壅塞度與推薦乾淨頻道。
* **一鍵 Web 儀表板 (`./run.sh`)**：支援響應式 Web 操作介面，手機連入熱點後，無需安裝任何 App，直接在手機瀏覽器開啟 `http://10.42.0.1:8080` 即可進行實機雙向測速、Ping 抖動、周遭熱點掃描與訊號分析。
* **即時雙天線訊號監控**：即時擷取 2T2R 雙天線個別訊號（`Antenna 1 / Antenna 2 dBm`）、MCS 調變指數、即時傳輸速率（Tx/Rx Bitrate）與封包重傳（Retries）。
* **WebSocket 即時推播架構**：採用非同步 WebSocket 長連線推播；徹底告別傳統 HTTP 輪詢造成的終端日誌洗版，介面反應更快更即時。
* **法規全頻道解鎖**：提供開機與熱插拔自動固化為 `country US` 的解決方案，徹底消除 Linux 核心在 5GHz UNII-1 (Ch 36~48) 與 UNII-3 (Ch 149~165) 的 `NO-IR` 限制。
* **Coding Agent 友善架構 (AGENTS.md & SKILLs)**：專案根目錄內建 `AGENTS.md`、`CLAUDE.md`、`GEMINI.md` 與 `.agents/skills/` 專家知識庫，支援 Gemini Agy CLI、Codex CLI、Claude CLI 快速接手開發與維運。

---

## 2. 無線法規區域 (US) 與解除 5G 發射限制

### 為何必須設定為 `country US`？
* 在 Linux 核心預設的全球標準領域（`country 00`），5GHz 全頻道均強制標註 **`NO-IR` (No Initiating Radiation / 禁止主動輻射發射)**，導致網路卡無法以 AP 模式廣播發射。
* 設定為 `country US` 後：
  * **5GHz UNII-1 (Ch 36~48)**：發射限制完全解除（最大 23 dBm / 200mW）。
  * **5GHz UNII-3 (Ch 149~165)**：發射限制完全解除（最大 30 dBm / 1000mW）。
  * **6GHz 頻段**：受限於國際法規與 Linux 核心，隨身型可攜式 USB 網路卡被強制歸類為 Client 終端裝置（Station），6GHz 強制標註 `NO-IR`，無法作為獨立 Master AP 發射，但完全支援 6GHz Client 連線與 6GHz Monitor 模式空中封包監聽。

### 永久固化 `country US` 的多重機制
1. **核心模組載入時預設套用**：
   ```bash
   echo "options cfg80211 ieee80211_regdom=US" | sudo tee /etc/modprobe.d/cfg80211.conf
   ```
2. **USB 網卡熱插拔時自動套用 (udev 規則)**：
   ```bash
   echo 'ACTION=="add", SUBSYSTEM=="net", KERNEL=="wl*", RUN+="/usr/sbin/iw reg set US"' | sudo tee /etc/udev/rules.d/85-regulatory.rules
   sudo udevadm control --reload-rules
   ```
3. **工具內建自癒檢查**：`alfa-mode` 腳本在啟動 AP 時會自動檢查 `iw reg get`，若非 US 會自動修正。

---

## 3. Web 診斷操作台快速啟動 (run.sh)

### 下載與啟動
```bash
git clone https://github.com/<your-username>/Diagnostic_Alfa.git
cd Diagnostic_Alfa
./run.sh
```

啟動後終端機即會顯示服務存取網址：
* **本機電腦操作**：開啟瀏覽器存取 `http://localhost:8080`
* **手機/連線裝置操作**：手機連線到 `DiagnosticAP`（預設密碼 `88888888`）後，直接開啟手機瀏覽器存取 `http://10.42.0.1:8080`
* **區域網路其他電腦**：瀏覽 `http://<區網本機IP>:8080`

按 `Ctrl+C` 即可自動安全釋放連接埠並停止 Web 伺服器背景行程。

---

## 4. 連線裝置智慧辨識與射頻遙測 (Connected Stations)

工作台具備高靈敏度的用戶端裝置連線感測與射頻遙測能力，能精準解析連入熱點之各智慧型手機、筆電或 IoT 設備：

### 📱 雙軌主機名稱 (Hostname) 自動解析
* **Android 裝置**：透過 **DHCP Option 12 (Host Name)** 協定。裝置索取 IP 時，熱點 `dnsmasq` 立即註冊本機 DNS PTR 反查記錄與日誌，系統可於 10 毫秒內解析出裝置名稱（如 `Pixel-10-Pro`）。
* **Apple 裝置 (iOS / macOS)**：iOS 裝置為保護隱私，DHCP 封包不廣播主機名稱；但連入區域網路後會發布 **mDNS (Multicast DNS / Bonjour)** 廣播。系統透過後端 `avahi-resolve` 瞬間捕捉其 `.local` 服務名稱（如 `Shen-iPhone-16e`）。

### 🔒 廠牌識別與隨機 MAC 隱私防護 (LAA vs. BIA)
* **實體硬體 MAC 位址 (BIA)**：內建 42,000+ 筆 IEEE / Nmap OUI 資料庫快取（啟動載入僅需 39ms，快取命中僅 0.01ms），若裝置使用實體硬體 MAC，直接比對出製造商（如 Apple, Samsung, Intel, Google, ASUSTek 等）。
* **隨機私人 MAC 位址 (LAA)**：現代 iOS（專用 Wi-Fi 位址）與 Android（隨機 MAC）預設啟用防追蹤虛擬 MAC。系統依據 IEEE 802 規範（第 1 個位元組次低位元為 1，即十六進位第二碼為 `2, 6, A, E`）自動判定為「隨機私人 MAC」，並結合解析出的主機名稱智慧標註廠牌。
* **💡 查驗原廠實體 MAC 方法**：使用者若在手機 Wi-Fi 設定中將 `DiagnosticAP` 的「專用 Wi-Fi 位址」或「隨機 MAC」關閉，重新連線後系統將直接呈現原廠實體硬體製造商。

### 📊 完整射頻訊號遙測參數
對每一台已連線裝置，系統即時擷取：
* **即時雙天線訊號強度**：總合 RSSI (dBm) 與雙天線獨立數值（`Antenna 1 / Antenna 2`）。
* **實體層傳輸速率**：Tx / Rx 協商速率（如 `130.0 MBit/s MCS 15`、`144.4 MBit/s MCS 15 short GI`）。
* **空口健康度**：連線時長、封包重傳計數（Tx Retries，評估是否遭遇碰撞干擾）。

---

## 5. 六大 Diagnostic 實戰診斷專題

### 診斷一：往返延遲與無線抖動測試 (Ping Latency & Jitter)
* **目的**：評估 Wi-Fi 空氣介質品質、抗干擾能力與即時往返時延。
* **Web 操作**：切換至【Ping 延遲與抖動】，系統會自動填入當前連線手機 IP（預設閘道池如 `10.42.0.254`），點擊「執行 Ping 診斷」。
* **診斷標準**：
  * 優良：延遲在 `2 ~ 15 ms` 之間，封包遺失率為 `0%`。
  * 干擾/衰減：延遲抖動飆升至 `50+ ms` 或出現封包遺失（Packet Loss）。

### 診斷二：實機極限吞吐量測速 (Web Speedtest & iPerf3)
* **目的**：測量 5GHz/2.4GHz 在當前空間距離下的真實最大應用層傳輸頻寬。
* **📱 手機 QR Code 掃描立即開啟 (零安裝)**：
  * 測速頁面頂部內建 **離線動態 QR Code 模組**：
    * **1. 網頁測速網址 QR Code**：手機掃描直接開啟 `http://10.42.0.1:8080/#speedtest`。
    * **2. Wi-Fi 一鍵加入 QR Code**：iPhone / Android 相機對準後點擊即可自動連線 `DiagnosticAP`。
* **🌓 深色 / 淺色主題自由切換**：
  * 點擊導覽列右上角的太陽/月亮圖示，即可即時切換專業夜間深色（Dark Mode）與戶外高對比淺色（Light Mode），偏好設定自動儲存於瀏覽器。
* **兩種測速方式**：
  1. **內建瀏覽器雙向測速 (Zero-Install Mobile Speedtest)**：
     * 手機連上熱點後開啟 `http://10.42.0.1:8080`，點擊「開始雙向測速」。
     * 瀏覽器透過 HTTP 串流自動測試下載與上傳速率（Mbps）。
  2. **專業 iPerf3 伺服器端 (iPerf3 Integration)**：
     * 在 Web 介面一鍵啟動 iPerf3 服務（連接埠 5201）。
     * 手機端可使用 App（如 *HE.NET Network Tools*）或另一台電腦終端機執行 `iperf3 -c 10.42.0.1 -i 1 -t 10 -P 4`。
* **診斷標準**：20MHz 頻寬（VHT-MCS 8 2T2R）在訊號良好時，實測 TCP 吞吐約 `110 ~ 135 Mbps`。

### 診斷三：即時動態訊號衰減折線圖 (Live RSSI & Rate Adaptation)
* **目的**：手持手機在不同房間走動，觀察距離與牆壁阻隔衰減，以及無線網路卡動態降速機制。
* **Web 操作**：切換至【即時訊號折線圖】。
* **診斷現象**：
  * 近距離：訊號為 `-40 ~ -50 dBm`，速率鎖定在最高 MCS 8 (173.3 Mbps)。
  * 隔牆或拉遠：訊號衰減至 `-70 ~ -80 dBm`，折線圖會即時記錄網路卡自動降為 MCS 4 或 MCS 2 以保證連線不中斷。

### 診斷四：周遭熱點基地台掃描 (Wi-Fi Site Survey & AP Scanner)
* **目的**：全面探測空間周遭所有可見 Wi-Fi 基地台，評估各頻道電磁波環境壅塞度，為診斷熱點挑選最佳乾淨頻道，並審查周遭網路安全防護等級。
* **Web 操作**：切換至【周遭熱點掃描】，點擊「快速讀取 (30ms 快取)」或「全頻主動探測 (Rescan)」。
* **功能亮點**：
  * **非破壞性背景掃描**：熱點正在發射時依然可獲取站點資訊，手機連網不中斷。
  * **完整基地台欄位**：SSID、BSSID、頻道、頻段（2.4G/5G/6G）、最大速率、訊號強度（% 與估算 dBm）、安全協定（WPA3/WPA2/Open）與硬體製造商（IEEE OUI）。
  * **頻譜頻道佔用圖 (Spectrum Congestion)**：即時統計 Ch 1, 6, 11 與 5G UNII-1 / UNII-3 佔用狀況，並自動提供推薦乾淨頻道。

### 診斷五：空中通訊協定與封包側錄 (Packet Capture & Wireshark)
* **目的**：檢視設備連入熱點後「從配發 IP 到正常上網」的完整通訊行為，排除「卡在取得 IP」、「DNS 解析卡頓」或「跳不出認證網頁」的真正根因。
* **實戰指令庫 (Cheat Sheet)**（Web 頁面提供一鍵點擊複製）：
  ```bash
  # 1. 側錄 DHCP 四向交握 (UDP 67/68，排查卡在取得 IP)
  sudo tcpdump -i <interface> -n "port 67 or port 68" -v

  # 2. 側錄 Captive Portal 上網檢測 (HTTP 204，排查 Wi-Fi 驚嘆號)
  sudo tcpdump -i <interface> -n "tcp port 80 and (tcp[tcpflags] & tcp-push != 0)"

  # 3. 側錄區域網路自動發現 (mDNS / SSDP，AirPlay 與微服務)
  sudo tcpdump -i <interface> -n "udp port 5353 or udp port 1900"

  # 4. 側錄現代 QUIC (HTTP/3) 串流 (UDP 443)
  sudo tcpdump -i <interface> -n "udp port 443" -c 30

  # 5. 側錄完整流量並儲存為 PCAP 檔案（供 Wireshark 開啟深度分析）
  sudo tcpdump -i <interface> -w /tmp/wifi_diagnostic.pcap -c 1000
  ```
  *(註：`<interface>` 預設為 ALFA 網卡介面名稱，例如 `wlx00c0cabb0b45` 或 `wlan1`)*

### 診斷六：頻段與頻道抗干擾評估 (RF Band & Channel Comparison)
* **目的**：比較 5GHz UNII-1、UNII-3 與 2.4GHz 頻段的覆蓋與抗干擾表現。
* **測試對比**：
  * **5GHz Channel 36**：低頻 UNII-1，室內干擾極少，適合近距離高速傳輸。
  * **5GHz Channel 149**：高頻 UNII-3，發射功率開放至 30 dBm (1000mW)，穿牆與遠距離能力優於 Ch 36。
  * **2.4GHz Channel 6**：波長長、穿透力最強，但背景 AP 雜訊高，Retries（重傳次數）通常高於 5GHz。

---

## 6. 無線網路學習手冊與射頻理論實戰指南

在 Web 儀表板點選右上角「📖 學習手冊」或第六個分頁【學習手冊】，內建完整目錄索引、快速跳轉與摺疊卡片，包含兩大核心板塊（共 11 個互動單元）：

### 🎯 第一篇：五大實戰測試功能與目的 (Diagnostic Tests Guide)
1. **測試模組 01：實機極限測速 (Speedtest & iPerf3)**
   * **功能與目的**：提供免裝 App 的瀏覽器雙向 HTTP 串流測速與背景 `iperf3` 多執行緒極限頻寬測試；評估在空間障礙與天線衰減下，基地台至手機之真實可用應用層 TCP 淨吞吐量。
   * **判讀指標**：110~135 Mbps（極佳）、70~110 Mbps（良好）、30~70 Mbps（隔牆衰減）、< 30 Mbps（同頻干擾嚴重）。
2. **測試模組 02：Ping 延遲與抖動 (Ping Latency & Jitter)**
   * **功能與目的**：連續發射 ICMP 探測封包至已連線裝置，精確統計最小、平均、最大往返時延 (RTT)、抖動值 (Jitter) 與封包遺失率；檢驗空中介質反應時間與波動穩定度。
   * **判讀指標**：< 5 ms（電競極佳）、5~15 ms（日常優良）、> 50 ms / 高抖動（異常碰撞）。
3. **測試模組 03：即時訊號折線圖 (Live RSSI & Rate Adaptation)**
   * **功能與目的**：每秒擷取手機訊號強度 (RSSI dBm)、雙天線數值、MCS 調變階梯、即時 Tx/Rx 協商速率與重傳次數；手持走動時即時觀測距離與水泥牆路徑損耗。
   * **判讀指標**：-30~-50 dBm（近距全速）、-50~-65 dBm（優良）、-65~-75 dBm（臨界降速）、-75~-85 dBm（微弱抗噪）、< -85 dBm（斷線邊緣）。
4. **測試模組 04：通訊協定與封包 (Protocols & Packet Inspection)**
   * **功能與目的**：檢視設備連入熱點後「從配發 IP 到正常上網」的完整通訊行為，排除「卡在取得 IP」、「DNS 解析卡頓」或「跳不出認證網頁」的真正根因。
5. **測試模組 05：頻段抗干擾 (RF Band & Channel Comparison)**
   * **功能與目的**：評估 2.4GHz、5GHz 與 6GHz 頻譜的電磁波擁擠程度，避開同頻干擾與鄰頻干擾，引導挑選最潔淨之頻道。
   * **規劃原則**：2.4G 嚴格限定 Ch 1/6/11；5G 優先推薦 UNII-1 (Ch 36~48) 或 UNII-3 (Ch 149~165)。

---

### 🔬 第二篇：Wi-Fi 射頻與通訊核心理論知識庫 (Wireless Foundations)
1. **核心理論 01：空中介面（Air Interface / OTA）與電磁波訊號本質**
   * **空中介面由來**：空氣開放共享媒介特性；臺灣正體中文通訊標準規範（避免使用普通話簡稱之「空口」）。
   * **dBm 負對數毫瓦標度**：0 dBm = 1 mW、-30 dBm = 0.001 mW、-60 dBm = 0.000001 mW。
   * **2T2R 雙天線架構 (MIMO)**：空間多工 (Spatial Multiplexing, NSS=2) 頻寬翻倍、分集接收 (Rx Diversity) 消除相位抵消衰落、波束成形 (Beamforming) 能量聚焦。
2. **核心理論 02：物理層速率 (PHY Rate) vs 真實測試吞吐量 (Throughput)**
   * **常見疑惑解密**：為什麼連線速率 173.3 Mbps，實測只有 120~135 Mbps？
   * **三大折損定律**：半雙工 (Half-Duplex) 與 CSMA/CA 空中爭用退避等待、802.11 協定層層開銷 (Preamble, MAC Header, ACK 確認訊框)、保護區間 (Guard Interval)。
   * **工程換算黃金定律**：`真實 TCP 淨吞吐量 ≈ 物理協商速率 (PHY Rate) × 60% ~ 70%`。
3. **核心理論 03：MCS 調變編碼等級與動態速率調適 (Rate Adaptation)**
   * **QAM 調變星座圖**：256-QAM (8 bits/符號)、16/64-QAM (4~6 bits/符號)、BPSK/QPSK (1~2 bits/符號)。
   * **Minstrel 演算法**：訊號轉弱時，主動降速降階調變以保全連線不中斷。
4. **核心理論 04：三大無線頻段 (2.4G / 5G / 6G) 全解密與 NO-IR 法規限制**
   * **全頻譜對照表**：波長、穿透力、頻道數量與干擾特性對照。
   * **深入剖析**：為什麼隨身 USB 網卡在 Linux 核心無法發射 6GHz AP？解密 `flags: 0x10003 NO-IR`、微波骨幹通訊保護、LPI/SP 與 AFC 雲端資料庫機制、隨身網卡強制 Station 屬性。
5. **核心理論 05：延遲 (Latency)、抖動 (Jitter) 與封包重傳 (Retries)**
   * **往返時延 RTT**：優良 Wi-Fi 空中時延標準為 2~8 ms。
   * **抖動致命性**：Jitter Buffer 爆倉瞬移或欠載破音，對即時語音/電競之破壞性甚於固定延遲。
   * **手機休眠省電模式 (Power Save)**：手機休眠喚醒第 1 個 Ping 常需 50~80ms，隨後立即恢復為 3ms 之省電物理特徵。
   * **Tx Retries 撞包重傳**：未收到 ACK 時晶片自動重發之空口耗損。
6. **核心理論 06：Wi-Fi 安全防護、802.11 原生訊框與空中側錄鑑識**
   * **AP 介面側錄 vs. Monitor 模式**：解密後 Layer 3/4 網路層行為（IP、TCP/UDP、DHCP、DNS）vs. Layer 2 原生無線電磁波訊框。
   * **802.11 原生空中訊框光譜**：Beacon 信標、Probe 探測、Auth/Assoc 二階段關聯、Deauth 斷線攻擊、RTS/CTS 隱藏節點預約、Block ACK 與 EAPOL 4 向交握。
   * **WPA2 缺陷 vs WPA3 SAE 前向保密性**：4-Way Handshake 離線字典暴力破解風險 vs 零知識證明動態會話金鑰。
   * **Wireshark 顯示過濾器語法**：`wlan.fc.type_subtype == 0x08` (Beacon)、`wlan.fc.type_subtype == 0x0c` (Deauth)、`eapol` (WPA交握)、`bootp || dns || arp`、`quic`、`mdns || ssdp`。

---

## 7. CLI 命令列速查手冊 (alfa-mode & iw)

除了 Web 介面外，亦可直接在系統任何終端機使用 `alfa-mode` 指令：

```bash
# 1. 啟動 5GHz 診斷熱點 (預設頻道 36)
alfa-mode ap 5G

# 指定 5GHz 頻道為 149
alfa-mode ap 5G 149

# 自訂 5G 頻道、密碼與 SSID
alfa-mode ap 5G 36 <自訂密碼> <自訂SSID>

# 2. 啟動 2.4GHz 診斷熱點 (預設頻道 6)
alfa-mode ap 2.4G

# 指定 2.4GHz 頻道為 1
alfa-mode ap 2.4G 1

# 3. 檢視當前連線狀態、已連線裝置 MAC/IP/訊號/即時速率
alfa-mode status

# 4. 切換回 Client 備援上網模式 (連線至指定 Wi-Fi SSID，Metric: 700)
alfa-mode client

# 5. 關閉網路卡 AP 連線
alfa-mode stop
```

### iw 即時硬體診斷指令
```bash
# 檢視所有已連線用戶端裝置詳細射頻參數（天線訊號、MCS、速率、重傳）
iw dev <interface> station dump

# 檢視單一用戶端裝置
iw dev <interface> station get <Client-MAC>

# 檢視目前系統無線法規區域
iw reg get

# 檢視網路卡支援頻率與各頻道 NO-IR 狀態
iw phy phy1 info
```

---

## 8. AI Coding Agent 規範與專案技能 (AGENTS.md)

本專案深度整合 AI Pair Programming 工作流程，內建為 **Gemini Agy CLI**、**Codex CLI** 與 **Claude CLI** 定制之標準規範：

* **核心規範文件**：
  * [`AGENTS.md`](./AGENTS.md)：定義雙網卡安全隔離鐵律、100% 臺灣正體中文要求、去識別化政策與常用維運指令。
  * [`CLAUDE.md`](./CLAUDE.md) 與 [`GEMINI.md`](./GEMINI.md)：各 CLI 工具入口導引。
* **專屬專家技能庫 (`.agents/skills/`)**：
  * `alfa-wireless-diagnosis`：ALFA AWUS036AXML (MT7921AU) 射頻遙測、模式切換與天線解析。
  * `wifi-site-survey`：周遭熱點掃描、頻道干擾雷達、WPA2/WPA3 安全分析與 OUI 廠牌匹配。
  * `taiwan-localization-guide`：通訊領域正體中文專有名詞審校對照表。

