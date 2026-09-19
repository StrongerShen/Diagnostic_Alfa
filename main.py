#!/usr/bin/env python3
"""
Diagnostic_Alfa - ALFA AWUS036AXML Wireless Diagnostics Web Server
FastAPI backend providing WebSocket real-time telemetry, mode switching, and 5 diagnostic modules.
"""

import os
import re
import sys
import time
import shutil
import asyncio
import subprocess
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import psutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(STATIC_DIR, exist_ok=True)


def detect_alfa_iface() -> str:
    env_iface = os.environ.get("ALFA_IFACE")
    if env_iface:
        return env_iface
    # 1. 優先依硬體 MAC 00:c0:ca:bb:0b:45 偵測
    try:
        res = subprocess.run("ip -o link 2>/dev/null", shell=True, capture_output=True, text=True)
        for line in res.stdout.splitlines():
            if "00:c0:ca:bb:0b:45" in line.lower():
                parts = line.split(":", 2)
                if len(parts) >= 2:
                    return parts[1].strip()
    except Exception:
        pass
    # 2. 搜尋 mt7921 驅動之網卡
    try:
        for name in os.listdir("/sys/class/net"):
            driver_link = os.path.join("/sys/class/net", name, "device", "driver")
            if os.path.islink(driver_link):
                target = os.readlink(driver_link)
                if "mt7921" in target:
                    return name
    except Exception:
        pass
    # 3. Fallback
    if os.path.exists("/sys/class/net/wlx00c0cabb0b45"):
        return "wlx00c0cabb0b45"
    if os.path.exists("/sys/class/net/wlan1"):
        return "wlan1"
    return "wlan1"


def detect_primary_iface(exclude_iface: str) -> str:
    env_iface = os.environ.get("PRIMARY_IFACE")
    if env_iface:
        return env_iface
    try:
        res = subprocess.run("ip route show default 2>/dev/null", shell=True, capture_output=True, text=True)
        m = re.search(r"dev\s+(\S+)", res.stdout)
        if m and m.group(1) != exclude_iface:
            return m.group(1)
    except Exception:
        pass
    return "wlan0" if exclude_iface != "wlan0" else "eth0"


IFACE = detect_alfa_iface()
PRIMARY_IFACE = detect_primary_iface(IFACE)

MODE_SCRIPT = (
    os.environ.get("ALFA_MODE_SCRIPT")
    or shutil.which("alfa-mode")
    or os.path.expanduser("~/.local/bin/alfa-mode")
    or os.path.expanduser("~/alfa-wifi-mode.sh")
    or "/usr/local/bin/alfa-mode"
)

# Background process tracking
IPERF3_PROC: Optional[subprocess.Popen] = None


class SwitchModeRequest(BaseModel):
    action: str  # 'ap', 'client', 'stop'
    band: Optional[str] = "5G"
    channel: Optional[str] = "36"
    ssid: Optional[str] = "DiagnosticAP"
    password: Optional[str] = "88888888"


class PingRequest(BaseModel):
    target: str = "10.42.0.254"
    count: int = 5


def run_cmd(cmd: str) -> str:
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        return res.stdout.strip()
    except Exception as e:
        return f"Error: {e}"


def get_regulatory_domain() -> str:
    out = run_cmd("iw reg get 2>/dev/null")
    m = re.search(r"country\s+([A-Z0-9]+):", out)
    return m.group(1) if m else "Unknown"


def get_interface_info() -> Dict[str, Any]:
    iw_info = run_cmd(f"iw dev {IFACE} info 2>/dev/null")
    ip_info = run_cmd(f"ip -4 addr show dev {IFACE} 2>/dev/null")
    
    # Mode
    mode_match = re.search(r"type\s+(\w+)", iw_info)
    raw_mode = mode_match.group(1) if mode_match else "offline"
    
    # SSID
    ssid_match = re.search(r"ssid\s+([^\n]+)", iw_info)
    ssid = ssid_match.group(1) if ssid_match else ""
    
    # Channel & Frequency
    chan_match = re.search(r"channel\s+(\d+)\s*\(([\d\.]+)\s*MHz\)", iw_info)
    channel = chan_match.group(1) if chan_match else ""
    freq = chan_match.group(2) if chan_match else ""
    width_match = re.search(r"width:\s*(\d+)\s*MHz", iw_info)
    width = width_match.group(1) if width_match else ""
    
    # IP
    ip_match = re.search(r"inet\s+([\d\.]+/\d+)", ip_info)
    ip_addr = ip_match.group(1) if ip_match else ""
    
    # If in managed/client mode, get link info
    signal = ""
    if raw_mode == "managed":
        link_info = run_cmd(f"iw dev {IFACE} link 2>/dev/null")
        link_ssid = re.search(r"SSID:\s*([^\n]+)", link_info)
        link_freq = re.search(r"freq:\s*([\d\.]+)", link_info)
        link_sig = re.search(r"signal:\s*(-?\d+)\s*dBm", link_info)
        if link_ssid:
            ssid = link_ssid.group(1)
        if link_freq:
            freq = link_freq.group(1)
        signal = link_sig.group(1) if link_sig else ""

    return {
        "iface": IFACE,
        "type": raw_mode,  # 'AP', 'managed', etc.
        "ssid": ssid,
        "channel": channel,
        "freq_mhz": freq,
        "width_mhz": width,
        "ip": ip_addr,
        "signal": signal,
    }


# OUI Database Cache and Station Resolution
OUI_CACHE: Dict[str, str] = {}
DEVICE_CACHE: Dict[str, Dict[str, Any]] = {}

CUSTOM_OUI_MAP: Dict[str, str] = {
    # Xiaomi (小米)
    "90FB5D": "Xiaomi (小米)",
    "A6FB5D": "Xiaomi (小米, MLO虛擬BSSID)",
    "50D2F5": "Xiaomi (小米)",
    "7C49EB": "Xiaomi (小米)",
    "6490C1": "Xiaomi (小米)",
    "D4970B": "Xiaomi (小米)",
    "286C07": "Xiaomi (小米)",
    "584120": "Xiaomi (小米)",
    "34CE00": "Xiaomi (小米)",
    "04CF8C": "Xiaomi (小米)",
    # ASUS (華碩)
    "B082E2": "ASUSTek (華碩)",
    "B682E2": "ASUSTek (華碩, 虛擬BSSID)",
    "BA82E2": "ASUSTek (華碩, 虛擬BSSID)",
    "BE82E2": "ASUSTek (華碩, 虛擬BSSID)",
    "04D4C4": "ASUSTek (華碩)",
    "04421A": "ASUSTek (華碩)",
    "1C872C": "ASUSTek (華碩)",
    "2C4D54": "ASUSTek (華碩)",
    "2CFDA1": "ASUSTek (華碩)",
    "38D547": "ASUSTek (華碩)",
    "40167E": "ASUSTek (華碩)",
    "AC1F74": "ASUSTek (華碩)",
    "F02F74": "ASUSTek (華碩)",
    "D017C2": "ASUSTek (華碩)",
    "704D7B": "ASUSTek (華碩)",
    # TP-Link
    "DA07B6": "TP-Link (虛擬BSSID)",
    "DA07B4": "TP-Link (虛擬BSSID)",
    "B2A7B9": "TP-Link (虛擬BSSID)",
}


def load_oui_database():
    global OUI_CACHE
    if OUI_CACHE:
        return
    OUI_CACHE.update(CUSTOM_OUI_MAP)
    oui_paths = [
        "/usr/share/nmap/nmap-mac-prefixes",
        "/usr/share/ieee-data/oui.txt",
    ]
    for path in oui_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        parts = line.split(maxsplit=1)
                        if len(parts) == 2 and parts[0].upper() not in OUI_CACHE:
                            OUI_CACHE[parts[0].upper()] = parts[1]
                if len(OUI_CACHE) > len(CUSTOM_OUI_MAP):
                    break
            except Exception:
                pass


load_oui_database()


def lookup_mac_vendor(mac: str) -> str:
    clean = mac.replace(":", "").upper()
    prefix = clean[:6]
    if prefix in CUSTOM_OUI_MAP:
        return CUSTOM_OUI_MAP[prefix]
    if prefix in OUI_CACHE:
        return OUI_CACHE[prefix]

    try:
        first_byte = int(mac.split(":")[0], 16)
        if first_byte & 0x02 != 0:
            cand1 = f"{(first_byte & ~0x02):02X}{clean[2:6]}"
            if cand1 in CUSTOM_OUI_MAP:
                return f"{CUSTOM_OUI_MAP[cand1]} (虛擬 BSSID)"
            if cand1 in OUI_CACHE:
                return f"{OUI_CACHE[cand1]} (虛擬 BSSID)"

            cand2 = f"{(first_byte & 0xF0):02X}{clean[2:6]}"
            if cand2 in CUSTOM_OUI_MAP:
                return f"{CUSTOM_OUI_MAP[cand2]} (虛擬 BSSID)"
            if cand2 in OUI_CACHE:
                return f"{OUI_CACHE[cand2]} (虛擬 BSSID)"
    except Exception:
        pass

    return "未知硬體廠商"


def resolve_station_details(mac: str, ip: str) -> Dict[str, Any]:
    global DEVICE_CACHE
    now = time.time()
    mac_lower = mac.lower()

    if mac_lower in DEVICE_CACHE:
        entry = DEVICE_CACHE[mac_lower]
        ttl = 180 if entry["hostname"] != "未廣播名稱" else 30
        if now - entry["timestamp"] < ttl:
            return entry["data"]

    # 1. Check LAA (Locally Administered Address / 隨機 MAC 防追蹤)
    try:
        first_byte = int(mac.split(":")[0], 16)
        is_random = bool(first_byte & 0x02)
    except Exception:
        is_random = False

    oui_vendor = lookup_mac_vendor(mac)

    # 2. Hostname resolution
    hostname = ""
    if ip:
        # A. Local dnsmasq DNS PTR query (fast, ~10ms)
        try:
            r = subprocess.run(
                ["dig", "@10.42.0.1", "-x", ip, "+short", "+time=1", "+tries=1"],
                capture_output=True, text=True, timeout=0.6
            )
            h = r.stdout.strip().rstrip(".")
            if h and not h.startswith(";") and "connection" not in h.lower():
                hostname = h
        except Exception:
            pass

        # B. Apple Bonjour / Avahi mDNS (multicast DNS)
        if not hostname:
            try:
                r = subprocess.run(
                    ["avahi-resolve", "-a", ip],
                    capture_output=True, text=True, timeout=0.8
                )
                lines = r.stdout.strip().splitlines()
                if lines:
                    parts = lines[0].split()
                    if len(parts) >= 2:
                        hostname = parts[1].rstrip(".local")
            except Exception:
                pass

        # C. Journalctl DHCPACK log fallback
        if not hostname:
            try:
                r = subprocess.run(
                    f'journalctl -u NetworkManager -g "DHCPACK.*{mac}" -n 3 --no-pager',
                    shell=True, capture_output=True, text=True, timeout=0.8
                )
                for line in reversed(r.stdout.strip().splitlines()):
                    m = re.search(r'DHCPACK\(.*?\)\s+[\d\.]+\s+[0-9a-fA-F:]+\s+([^\s]+)', line)
                    if m:
                        hostname = m.group(1)
                        break
            except Exception:
                pass

    # 3. Vendor classification & Inferred intelligence
    if is_random:
        vendor_label = "隨機私人 MAC"
        vendor_detail = "iOS 專用位址 / Android 隨機 MAC"
        vendor_hint = "手機啟用了專用 Wi-Fi 位址防追蹤功能；若關閉此設定可查看實體硬體廠牌"
        h_lower = hostname.lower()
        if any(k in h_lower for k in ["iphone", "ipad", "apple", "macbook"]):
            vendor_detail = "Apple (由主機名稱識別)"
        elif "pixel" in h_lower:
            vendor_detail = "Google Pixel (由主機名稱識別)"
        elif any(k in h_lower for k in ["galaxy", "samsung"]):
            vendor_detail = "Samsung (由主機名稱識別)"
        elif any(k in h_lower for k in ["xiaomi", "redmi", "mi-"]):
            vendor_detail = "小米 Xiaomi (由主機名稱識別)"
        elif "oppo" in h_lower:
            vendor_detail = "OPPO (由主機名稱識別)"
        elif "vivo" in h_lower:
            vendor_detail = "vivo (由主機名稱識別)"
    else:
        vendor_label = oui_vendor
        vendor_detail = f"實體硬體 OUI ({oui_vendor})"
        vendor_hint = "實體硬體燒錄 MAC 位址 (BIA)"

    res = {
        "is_random_mac": is_random,
        "hostname": hostname or "未廣播名稱",
        "vendor_label": vendor_label,
        "vendor_detail": vendor_detail,
        "vendor_hint": vendor_hint,
    }

    DEVICE_CACHE[mac_lower] = {
        "timestamp": now,
        "hostname": hostname or "未廣播名稱",
        "data": res
    }
    return res


def get_connected_stations() -> List[Dict[str, Any]]:
    stations = []
    dump_out = run_cmd(f"iw dev {IFACE} station dump 2>/dev/null")
    if not dump_out:
        return stations

    # Parse neighbor table once for fast MAC -> IP lookup
    neigh_out = run_cmd(f"ip neigh show dev {IFACE} 2>/dev/null")
    mac_to_ip: Dict[str, str] = {}
    for line in neigh_out.splitlines():
        parts = line.split()
        if "lladdr" in parts:
            idx = parts.index("lladdr")
            if idx + 1 < len(parts):
                mac_to_ip[parts[idx + 1].lower()] = parts[0]

    blocks = dump_out.split("Station ")
    for block in blocks:
        if not block.strip():
            continue
        lines = block.strip().splitlines()
        mac = lines[0].split()[0].lower()

        # IP from neighbor table mapping, or fallback to DHCPACK search
        ip_addr = mac_to_ip.get(mac, "")
        if not ip_addr:
            try:
                dhcp_out = run_cmd(f'journalctl -u NetworkManager -g "DHCPACK.*{mac}" -n 1 --no-pager 2>/dev/null')
                m = re.search(r'DHCPACK\(.*?\)\s+([\d\.]+)\s+' + re.escape(mac), dhcp_out, re.IGNORECASE)
                if m:
                    ip_addr = m.group(1)
            except Exception:
                pass

        # Resolve vendor & hostname
        dev_info = resolve_station_details(mac, ip_addr)

        # Dual antenna signal parsing
        sig_match = re.search(r"signal:\s+(-?\d+)\s+\[(-?\d+),\s*(-?\d+)\]\s*dBm", block)
        if sig_match:
            sig_avg = int(sig_match.group(1))
            ant1 = int(sig_match.group(2))
            ant2 = int(sig_match.group(3))
        else:
            simple_sig = re.search(r"signal:\s+(-?\d+)\s*dBm", block)
            sig_avg = int(simple_sig.group(1)) if simple_sig else -50
            ant1 = sig_avg
            ant2 = sig_avg

        # Bitrates
        tx_match = re.search(r"tx bitrate:\s+([^\n]+)", block)
        rx_match = re.search(r"rx bitrate:\s+([^\n]+)", block)
        tx_rate = tx_match.group(1).strip() if tx_match else "Unknown"
        rx_rate = rx_match.group(1).strip() if rx_match else "Unknown"

        # Numeric Mbps
        tx_mbps_match = re.search(r"([\d\.]+)\s*MBit/s", tx_rate)
        rx_mbps_match = re.search(r"([\d\.]+)\s*MBit/s", rx_rate)
        tx_mbps = float(tx_mbps_match.group(1)) if tx_mbps_match else 0.0
        rx_mbps = float(rx_mbps_match.group(1)) if rx_mbps_match else 0.0

        # Retries
        retry_match = re.search(r"tx retries:\s+(\d+)", block)
        retries = int(retry_match.group(1)) if retry_match else 0

        # Connected Time
        time_match = re.search(r"connected time:\s+(\d+\s*\w+)", block)
        conn_time = time_match.group(1) if time_match else ""

        stations.append({
            "mac": mac,
            "ip": ip_addr,
            "is_random_mac": dev_info["is_random_mac"],
            "hostname": dev_info["hostname"],
            "vendor": dev_info["vendor_label"],
            "vendor_detail": dev_info["vendor_detail"],
            "vendor_hint": dev_info["vendor_hint"],
            "signal_dbm": sig_avg,
            "ant1_dbm": ant1,
            "ant2_dbm": ant2,
            "tx_bitrate_str": tx_rate,
            "rx_bitrate_str": rx_rate,
            "tx_mbps": tx_mbps,
            "rx_mbps": rx_mbps,
            "tx_retries": retries,
            "connected_time": conn_time
        })

    return stations


def get_primary_uplink() -> Dict[str, Any]:
    ip_out = run_cmd(f"ip -4 addr show dev {PRIMARY_IFACE} 2>/dev/null")
    ip_m = re.search(r"inet\s+([\d\.]+/\d+)", ip_out)
    
    # 動態識別設備型號名稱
    name = "主力網際網路連線網卡"
    if PRIMARY_IFACE == "wlan0":
        name = "Raspberry Pi 內建無線網卡 (Onboard Wi-Fi)"
    elif "wlxd03745e1db0d" in PRIMARY_IFACE or "T3U" in PRIMARY_IFACE:
        name = "TP-Link Archer T3U (RTL8812BU)"
    elif PRIMARY_IFACE.startswith("eth") or PRIMARY_IFACE.startswith("en"):
        name = "Gigabit 乙太有線網路 (Ethernet)"
    elif PRIMARY_IFACE.startswith("wlx") or PRIMARY_IFACE.startswith("wlan"):
        name = f"主力無線網卡 ({PRIMARY_IFACE})"

    route_out = run_cmd(f"ip route show dev {PRIMARY_IFACE} 2>/dev/null")
    metric_m = re.search(r"metric\s+(\d+)", route_out)
    metric_val = int(metric_m.group(1)) if metric_m else 100

    return {
        "iface": PRIMARY_IFACE,
        "name": name,
        "ip": ip_m.group(1) if ip_m else "離線",
        "metric": metric_val,
        "role": "主力網際網路連線 (NAT 轉送提供者)"
    }


def get_full_status() -> Dict[str, Any]:
    iface_info = get_interface_info()
    stations = get_connected_stations()
    regdom = get_regulatory_domain()
    primary = get_primary_uplink()
    
    return {
        "timestamp": time.time(),
        "regulatory": regdom,
        "interface": iface_info,
        "stations": stations,
        "primary_uplink": primary,
        "hardware": {
            "model": "ALFA Network AWUS036AXML",
            "chipset": "MediaTek MT7921AU / MT7961",
            "usb_id": "0e8d:7961",
            "mac": "00:c0:ca:bb:0b:45",
            "driver": "mt7921u"
        }
    }


# ==========================================
# WebSocket Connection Manager
# (Eliminates repeated HTTP polling logs)
# ==========================================

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # Send initial status on connection
        try:
            status = get_full_status()
            await websocket.send_json({"type": "status", "data": status})
        except Exception:
            pass

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()


async def telemetry_background_task():
    """Pushes live wireless telemetry over WebSockets only when clients are connected."""
    while True:
        try:
            await asyncio.sleep(2)
            if manager.active_connections:
                status = get_full_status()
                await manager.broadcast({"type": "status", "data": status})
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Launch background telemetry pusher
    task = asyncio.create_task(telemetry_background_task())
    yield
    # Shutdown: Cancel task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Diagnostic_Alfa Web Suite", version="1.2.0", lifespan=lifespan)


# ==========================================
# WebSocket Endpoint
# ==========================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "ping":
                target = data.get("target", "10.42.0.254")
                count = int(data.get("count", 5))
                res = api_diagnostic_ping(PingRequest(target=target, count=count))
                await websocket.send_json({"type": "ping_result", "data": res})

            elif msg_type == "switch_mode":
                action = data.get("action", "ap")
                band = data.get("band", "5G")
                chan = data.get("channel", "36")
                res = api_switch_mode(SwitchModeRequest(action=action, band=band, channel=chan))
                await websocket.send_json({"type": "switch_result", "data": res})
                # Immediately push updated status
                await manager.broadcast({"type": "status", "data": get_full_status()})

            elif msg_type == "wifi_scan":
                rescan = bool(data.get("rescan", False))
                scan_res = scan_nearby_wifi_aps(rescan=rescan)
                await websocket.send_json({"type": "wifi_scan_result", "data": scan_res})

            elif msg_type == "iperf3_toggle":
                api_iperf3_toggle()
                status = api_iperf3_status()
                await websocket.send_json({"type": "iperf3_status", "data": status})

            elif msg_type == "get_status":
                await websocket.send_json({"type": "status", "data": get_full_status()})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


# ==========================================
# REST API Endpoints (Fallback & Scripts)
# ==========================================

def scan_nearby_wifi_aps(rescan: bool = False) -> Dict[str, Any]:
    rescan_flag = "--rescan yes" if rescan else "--rescan no"
    cmd = f"nmcli -t -f IN-USE,BSSID,SSID,MODE,CHAN,FREQ,RATE,SIGNAL,BARS,SECURITY dev wifi list {rescan_flag}"
    try:
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        lines = proc.stdout.strip().splitlines()
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "total": 0,
            "aps": [],
            "stats": {}
        }

    aps = []
    seen = set()
    chan_dist: Dict[str, int] = {}
    band_counts = {"2.4GHz": 0, "5GHz": 0, "6GHz": 0, "other": 0}

    for line in lines:
        if not line.strip():
            continue
        unescaped = line.replace(r"\:", "__COLON__")
        parts = unescaped.split(":")
        if len(parts) < 9:
            continue
        parts = [p.replace("__COLON__", ":") for p in parts]

        in_use = parts[0].strip() == "*"
        bssid = parts[1].strip()
        raw_ssid = parts[2].strip()
        ssid = raw_ssid if raw_ssid else "[隱藏 SSID / Hidden]"
        mode = parts[3].strip()
        chan = parts[4].strip()
        freq_str = parts[5].strip()
        rate = parts[6].strip()
        sig_str = parts[7].strip()
        bars = parts[8].strip()
        security = parts[9].strip() if len(parts) > 9 else "--"
        if not security:
            security = "開放無密碼 (Open)"

        # Deduplicate same BSSID + SSID + Channel
        key = (bssid.lower(), ssid, chan)
        if key in seen:
            continue
        seen.add(key)

        # Freq & Band
        freq_m = re.search(r"(\d+)", freq_str)
        freq_val = int(freq_m.group(1)) if freq_m else 0
        if freq_val >= 5925:
            band = "6GHz"
            band_counts["6GHz"] += 1
        elif freq_val >= 5000:
            band = "5GHz"
            band_counts["5GHz"] += 1
        elif freq_val >= 2400:
            band = "2.4GHz"
            band_counts["2.4GHz"] += 1
        else:
            band = "其他"
            band_counts["other"] += 1

        if chan and chan != "--":
            chan_dist[chan] = chan_dist.get(chan, 0) + 1

        # Signal dBm estimate
        try:
            sig_pct = int(sig_str)
            sig_dbm = int((sig_pct / 2) - 100)
        except Exception:
            sig_pct = 0
            sig_dbm = -100

        # Vendor lookup from OUI / MBSSID resolver
        vendor = lookup_mac_vendor(bssid)

        sec_upper = security.upper()
        if "WPA3" in sec_upper:
            sec_type = "wpa3"
        elif "WPA2" in sec_upper:
            sec_type = "wpa2"
        elif "WPA" in sec_upper:
            sec_type = "wpa1"
        elif "OPEN" in sec_upper or "--" in sec_upper or "開放" in security:
            sec_type = "open"
        else:
            sec_type = "other"

        aps.append({
            "in_use": in_use,
            "bssid": bssid,
            "ssid": ssid,
            "channel": chan,
            "freq_mhz": freq_val,
            "band": band,
            "rate": rate,
            "signal_pct": sig_pct,
            "signal_dbm": sig_dbm,
            "bars": bars,
            "security": security,
            "security_type": sec_type,
            "vendor": vendor
        })

    # Sort: in-use first, then signal descending
    aps.sort(key=lambda x: (not x["in_use"], -x["signal_pct"]))

    # Recommendations for least congested channels
    ch2g_counts = {ch: chan_dist.get(str(ch), 0) for ch in [1, 6, 11]}
    best_2g = min(ch2g_counts, key=ch2g_counts.get) if ch2g_counts else 6

    ch5g_candidates = [36, 40, 44, 48, 149, 153, 157, 161]
    ch5g_counts = {ch: chan_dist.get(str(ch), 0) for ch in ch5g_candidates}
    best_5g = min(ch5g_counts, key=ch5g_counts.get) if ch5g_counts else 36

    stats = {
        "total_aps": len(aps),
        "band_counts": band_counts,
        "channel_distribution": chan_dist,
        "recommendation": {
            "best_2g_channel": best_2g,
            "best_5g_channel": best_5g
        }
    }

    return {
        "success": True,
        "timestamp": time.time(),
        "stats": stats,
        "aps": aps
    }


@app.get("/api/status")
def api_status():
    return get_full_status()


@app.get("/api/wifi/scan")
def api_wifi_scan(rescan: bool = False):
    return scan_nearby_wifi_aps(rescan=rescan)


@app.post("/api/mode/switch")
def api_switch_mode(req: SwitchModeRequest):
    if not os.path.isfile(MODE_SCRIPT):
        raise HTTPException(status_code=500, detail=f"Mode script not found at {MODE_SCRIPT}")
    
    if req.action == "ap":
        band = req.band or "5G"
        chan = req.channel or ("36" if band == "5G" else "6")
        password = req.password or "88888888"
        ssid = req.ssid or "DiagnosticAP"
        cmd = f"{MODE_SCRIPT} ap {band} {chan} {password} '{ssid}'"
    elif req.action == "client":
        cmd = f"{MODE_SCRIPT} client"
    elif req.action == "stop":
        cmd = f"{MODE_SCRIPT} stop"
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    try:
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=25)
        output = proc.stdout + proc.stderr
        return {
            "success": proc.returncode == 0,
            "action": req.action,
            "output": output
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "output": "切換操作逾時 (Timeout)"}


@app.post("/api/diagnostics/ping")
def api_diagnostic_ping(req: PingRequest):
    target = req.target.strip()
    if not re.match(r"^[\w\.\-]+$", target):
        raise HTTPException(status_code=400, detail="Invalid target address")
    count = min(max(req.count, 1), 20)
    
    cmd = f"ping -c {count} -W 1 {target}"
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=25)
    raw = proc.stdout + proc.stderr
    
    rtt_match = re.search(r"rtt min/avg/max/mdev = ([\d\.]+)/([\d\.]+)/([\d\.]+)/([\d\.]+)\s*ms", raw)
    loss_match = re.search(r"(\d+)%\s*packet loss", raw)
    
    return {
        "success": proc.returncode == 0,
        "target": target,
        "raw_output": raw,
        "loss_percent": int(loss_match.group(1)) if loss_match else 100,
        "stats": {
            "min_ms": float(rtt_match.group(1)) if rtt_match else None,
            "avg_ms": float(rtt_match.group(2)) if rtt_match else None,
            "max_ms": float(rtt_match.group(3)) if rtt_match else None,
            "mdev_ms": float(rtt_match.group(4)) if rtt_match else None,
        }
    }


@app.get("/api/diagnostics/iperf3/status")
def api_iperf3_status():
    global IPERF3_PROC
    is_installed = subprocess.run("command -v iperf3", shell=True, capture_output=True).returncode == 0
    running = False
    
    for p in psutil.process_iter(['name', 'cmdline']):
        try:
            if 'iperf3' in p.info['name'] and any('-s' in str(arg) for arg in (p.info['cmdline'] or [])):
                running = True
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
            
    return {
        "installed": is_installed,
        "running": running,
        "server_ip": "10.42.0.1",
        "server_port": 5201
    }


@app.post("/api/diagnostics/iperf3/toggle")
def api_iperf3_toggle():
    global IPERF3_PROC
    status = api_iperf3_status()
    if not status["installed"]:
        raise HTTPException(status_code=400, detail="iperf3 is not installed.")
        
    if status["running"]:
        subprocess.run("pkill -f 'iperf3 -s'", shell=True)
        IPERF3_PROC = None
        return {"running": False, "message": "iPerf3 Server 已停止"}
    else:
        IPERF3_PROC = subprocess.Popen(["iperf3", "-s", "-p", "5201"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"running": True, "message": "iPerf3 Server 已在 10.42.0.1:5201 啟動"}


# ==========================================
# In-Browser Speedtest Streaming Endpoints
# ==========================================

@app.get("/api/speedtest/download")
async def speedtest_download(size_mb: int = 25):
    size_mb = min(max(size_mb, 5), 100)
    chunk = b"0" * (64 * 1024)
    total_chunks = (size_mb * 1024 * 1024) // len(chunk)
    
    async def data_stream():
        for _ in range(total_chunks):
            yield chunk
            
    return StreamingResponse(data_stream(), media_type="application/octet-stream")


@app.post("/api/speedtest/upload")
async def speedtest_upload(request: Request):
    received = 0
    start = time.time()
    async for chunk in request.stream():
        received += len(chunk)
    elapsed = max(time.time() - start, 0.001)
    mbps = (received * 8) / (elapsed * 1_000_000)
    return {
        "bytes_received": received,
        "elapsed_seconds": round(elapsed, 3),
        "mbps": round(mbps, 2)
    }


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False, access_log=False)
