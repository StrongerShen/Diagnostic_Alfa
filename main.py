#!/usr/bin/env python3
"""
Diagnostic_Alfa - ALFA AWUS036AXML Wireless Diagnostics Web Server
FastAPI backend providing WebSocket real-time telemetry, mode switching, and 5 diagnostic modules.
"""

import os
import re
import sys
import time
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

IFACE = "wlx00c0cabb0b45"
PRIMARY_IFACE = "wlxd03745e1db0d"
MODE_SCRIPT = os.path.expanduser("~/alfa-wifi-mode.sh")

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


def get_connected_stations() -> List[Dict[str, Any]]:
    stations = []
    dump_out = run_cmd(f"iw dev {IFACE} station dump 2>/dev/null")
    if not dump_out:
        return stations
    
    blocks = dump_out.split("Station ")
    for block in blocks:
        if not block.strip():
            continue
        lines = block.strip().splitlines()
        mac = lines[0].split()[0]
        
        # IP from neighbor table
        ip_match = run_cmd(f"ip neigh show dev {IFACE} | grep -i '{mac}' | awk '{{print $1}}'")
        ip_addr = ip_match.splitlines()[0] if ip_match else "10.42.0.254"
        
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
    return {
        "iface": PRIMARY_IFACE,
        "name": "TP-Link Archer T3U (RTL8812BU)",
        "ip": ip_m.group(1) if ip_m else "離線",
        "metric": 100,
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

@app.get("/api/status")
def api_status():
    return get_full_status()


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
