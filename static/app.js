// Diagnostic_Alfa - Advanced WebSocket Telemetry & Flawless Theme Engine

let ws = null;
let wsReconnectTimer = null;
let liveChart = null;
let qrInstance = null;
let currentQrType = 'url';
const maxChartPoints = 35;
const chartLabels = [];
const rssiData = [];
const txRateData = [];

// ==========================================
// Initialization on DOM Ready
// ==========================================
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initChart();
  initWebSocket();
  
  if (window.lucide) {
    lucide.createIcons();
  }

  // Render initial QR Code (collapse on mobile by default to keep speedtest front & center)
  const isMobile = window.innerWidth < 768;
  const qrSection = document.getElementById('qr-expandable-section');
  const qrIcon = document.getElementById('qr-toggle-icon');
  
  if (isMobile && qrSection) {
    qrSection.classList.add('hidden');
    if (qrIcon) qrIcon.style.transform = 'rotate(0deg)';
  } else {
    renderQr('url');
    if (qrIcon) qrIcon.style.transform = 'rotate(180deg)';
  }

  // Handle URL Hash navigation
  if (window.location.hash === '#speedtest' || window.location.hash === '#speed') {
    switchTab('tab-speedtest');
  } else if (window.location.hash === '#ping') {
    switchTab('tab-ping');
  } else if (window.location.hash === '#chart') {
    switchTab('tab-chart');
  } else if (window.location.hash === '#guide' || window.location.hash === '#manual') {
    switchTab('tab-guide');
  }
});

function toggleQrBox() {
  const section = document.getElementById('qr-expandable-section');
  const icon = document.getElementById('qr-toggle-icon');
  if (!section) return;

  if (section.classList.contains('hidden')) {
    section.classList.remove('hidden');
    if (icon) icon.style.transform = 'rotate(180deg)';
    renderQr(currentQrType);
  } else {
    section.classList.add('hidden');
    if (icon) icon.style.transform = 'rotate(0deg)';
  }
}

// ==========================================
// 1. Dark / Light Theme Switching Engine
// ==========================================
function initTheme() {
  const saved = localStorage.getItem('alfa_theme') || 'dark';
  setTheme(saved);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'dark';
  const next = current === 'dark' ? 'light' : 'dark';
  setTheme(next);
}

function setTheme(theme) {
  localStorage.setItem('alfa_theme', theme);
  document.documentElement.setAttribute('data-theme', theme);
  
  const icon = document.getElementById('theme-icon');
  if (icon) {
    if (theme === 'dark') {
      icon.setAttribute('data-lucide', 'sun');
      icon.className = 'w-4 h-4 text-amber-400';
    } else {
      icon.setAttribute('data-lucide', 'moon');
      icon.className = 'w-4 h-4 text-indigo-600';
    }
  }

  if (window.lucide) lucide.createIcons();
  updateChartTheme(theme);
}

function updateChartTheme(theme) {
  if (!liveChart) return;
  const isDark = theme === 'dark';
  const gridColor = isDark ? '#334155' : '#e2e8f0';
  const textColor = isDark ? '#94a3b8' : '#64748b';
  const legendColor = isDark ? '#cbd5e1' : '#1e293b';

  liveChart.options.scales.x.grid.color = gridColor;
  liveChart.options.scales.x.ticks.color = textColor;
  liveChart.options.scales.yRSSI.grid.color = gridColor;
  liveChart.options.scales.yRSSI.ticks.color = isDark ? '#fbbf24' : '#d97706';
  liveChart.options.plugins.legend.labels.color = legendColor;
  liveChart.update('none');
}

// ==========================================
// 2. WebSocket Real-Time Connection
// (Replaces repetitive HTTP polling)
// ==========================================
function initWebSocket() {
  if (wsReconnectTimer) clearTimeout(wsReconnectTimer);

  const loc = window.location;
  const protocol = loc.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${loc.host}/ws`;

  updateWsStatus('connecting');

  try {
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      updateWsStatus('connected');
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'status') {
          updateUiStatus(msg.data);
        } else if (msg.type === 'ping_result') {
          handlePingResult(msg.data);
        } else if (msg.type === 'switch_result') {
          handleSwitchResult(msg.data);
        } else if (msg.type === 'iperf3_status') {
          updateIperf3Ui(msg.data);
        }
      } catch (err) {
        console.error("WS Parse Error:", err);
      }
    };

    ws.onclose = () => {
      updateWsStatus('disconnected');
      // Auto-reconnect after 3 seconds
      wsReconnectTimer = setTimeout(initWebSocket, 3000);
    };

    ws.onerror = (err) => {
      console.warn("WS error:", err);
      updateWsStatus('disconnected');
      ws.close();
    };

  } catch (err) {
    updateWsStatus('disconnected');
    wsReconnectTimer = setTimeout(initWebSocket, 4000);
  }
}

function updateWsStatus(state) {
  const dot = document.getElementById('ws-dot');
  const text = document.getElementById('ws-text');
  if (!dot || !text) return;

  if (state === 'connected') {
    dot.className = 'w-2 h-2 rounded-full bg-emerald-400 live-dot';
    text.className = 'font-bold text-emerald-500 font-mono';
    text.innerText = 'WS 正常';
  } else if (state === 'connecting') {
    dot.className = 'w-2 h-2 rounded-full bg-amber-400 live-dot';
    text.className = 'font-bold text-amber-500 font-mono';
    text.innerText = '連線中...';
  } else {
    dot.className = 'w-2 h-2 rounded-full bg-rose-500';
    text.className = 'font-bold text-rose-500 font-mono';
    text.innerText = 'WS 離線';
  }
}

function requestStatusRefresh() {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'get_status' }));
  } else {
    fetch('/api/status').then(r => r.json()).then(updateUiStatus);
  }
}

// ==========================================
// 3. UI Status Updating Logic
// ==========================================
function updateUiStatus(data) {
  if (!data) return;

  // Badges
  document.getElementById('badge-regdom').innerText = data.regulatory || 'US';
  
  // Interface & Mode
  const iface = data.interface || {};
  const modeText = document.getElementById('card-mode-text');
  const chanInfo = document.getElementById('card-chan-info');
  const ipText = document.getElementById('card-ip-text');
  const ssidText = document.getElementById('card-ssid');
  const freqBand = document.getElementById('card-freq-band');
  
  if (iface.type === 'AP') {
    modeText.innerHTML = `<span class="text-emerald-500 font-bold">🌟 熱點 AP 模式</span>`;
    chanInfo.innerText = `頻道 ${iface.channel || '36'} (${iface.freq_mhz || '5180'} MHz) [${iface.width_mhz || '20'}MHz]`;
    ipText.innerText = iface.ip || '10.42.0.1/24';
    ssidText.innerText = iface.ssid || 'DiagnosticAP';
    
    const ch = parseInt(iface.channel || '36');
    if (ch <= 14) freqBand.innerText = '2.4GHz';
    else if (ch >= 36) freqBand.innerText = '5GHz';
  } else if (iface.type === 'managed') {
    modeText.innerHTML = `<span class="text-blue-500 font-bold">🛡️ Client 備援模式</span>`;
    chanInfo.innerText = `連線至: ${iface.ssid} (${iface.freq_mhz || ''} MHz)`;
    ipText.innerText = iface.ip || '已連線';
    ssidText.innerText = iface.ssid || 'Uplink-Wi-Fi';
    freqBand.innerText = 'Client 模式';
  } else {
    modeText.innerHTML = `<span class="ui-sec font-bold">⏹️ 離線 / 已停止</span>`;
    chanInfo.innerText = `網路卡目前未連線`;
    ipText.innerText = '-';
  }

  // Stations
  const stations = data.stations || [];
  const countEl = document.getElementById('card-station-count');
  countEl.innerText = stations.length;
  
  const stationsList = document.getElementById('stations-list');
  
  if (stations.length > 0) {
    const sta = stations[0];
    const quickTitle = (sta.hostname && sta.hostname !== '未廣播名稱') 
      ? `${sta.hostname} (${sta.ip || sta.mac})` 
      : `${sta.mac} · ${sta.ip || '已連線'}`;
    document.getElementById('card-station-mac-quick').innerText = quickTitle;
    document.getElementById('card-station-signal').innerText = `${sta.signal_dbm} dBm`;
    document.getElementById('card-station-rate').innerText = `${sta.tx_mbps} Mbps`;
    document.getElementById('card-station-retries').innerText = `重傳封包遺失: ${sta.tx_retries}`;
    document.getElementById('card-ant1').innerText = `${sta.ant1_dbm} dBm`;
    document.getElementById('card-ant2').innerText = `${sta.ant2_dbm} dBm`;
    
    // Auto populate ping target
    const pingInput = document.getElementById('ping-target');
    if (pingInput && (!pingInput.value || pingInput.value === '10.42.0.254')) {
      pingInput.value = sta.ip || '10.42.0.254';
    }

    // Auto populate packet capture target IP
    if (sta.ip) {
      document.querySelectorAll('.packet-target-ip').forEach(el => {
        el.innerText = sta.ip;
      });
    }

    // Render Stations List
    stationsList.innerHTML = stations.map(s => {
      const hasHostname = s.hostname && s.hostname !== '未廣播名稱';
      const deviceTitle = hasHostname ? s.hostname : (s.is_random_mac ? '智慧型裝置 (未廣播名稱)' : '連線用戶端裝置');
      const vendorBadge = s.is_random_mac 
        ? `<span class="px-2 py-0.5 rounded bg-purple-500/15 text-purple-400 text-xs font-medium border border-purple-500/30 flex items-center space-x-1" title="${s.vendor_hint || 'iOS/Android 隨機 MAC 隱私防護'}">
             <i data-lucide="shield-check" class="w-3 h-3 text-purple-400"></i>
             <span>${s.vendor_detail || '隨機私人 MAC'}</span>
           </span>`
        : `<span class="px-2 py-0.5 rounded bg-blue-500/15 text-blue-400 text-xs font-medium border border-blue-500/30 flex items-center space-x-1" title="${s.vendor_hint || '實體硬體 OUI'}">
             <i data-lucide="cpu" class="w-3 h-3 text-blue-400"></i>
             <span>${s.vendor || '實體硬體'}</span>
           </span>`;

      return `
        <div class="ui-subcard border rounded-lg p-3.5 sm:p-4 flex flex-col lg:flex-row lg:items-center justify-between gap-3 shadow-sm hover:border-purple-500/40 transition-colors">
          <div class="space-y-1.5">
            <div class="flex flex-wrap items-center gap-2">
              <span class="font-bold ui-title text-sm sm:text-base flex items-center space-x-1.5">
                <i data-lucide="${s.hostname && s.hostname.toLowerCase().includes('iphone') ? 'smartphone' : 'monitor-speaker'}" class="w-4 h-4 text-purple-400"></i>
                <span>${deviceTitle}</span>
              </span>
              <span class="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 text-xs font-mono font-bold">${s.ip || '未指派 IP'}</span>
              ${vendorBadge}
            </div>
            <div class="text-xs ui-sec flex flex-wrap items-center gap-x-3 gap-y-1">
              <span class="font-mono text-slate-400">MAC: <strong class="ui-title">${s.mac}</strong></span>
              ${s.is_random_mac ? '<span class="text-[11px] text-purple-400/90 font-medium">🔒 專用 Wi-Fi 隨機位址</span>' : '<span class="text-[11px] text-blue-400/90 font-medium">🌐 實體硬體 MAC</span>'}
              <span>連線時長: <strong class="ui-title font-mono">${s.connected_time || '-'}</strong></span>
              <span>封包重傳: <strong class="font-mono ${s.tx_retries > 0 ? 'text-amber-500' : 'text-emerald-500'}">${s.tx_retries} 次</strong></span>
            </div>
          </div>
          
          <div class="grid grid-cols-3 gap-2.5 text-xs shrink-0">
            <div class="ui-tertiary px-2.5 py-1.5 rounded border">
              <div class="ui-sec text-[10px]">訊號 (RSSI)</div>
              <div class="font-bold text-amber-500 font-mono text-sm">${s.signal_dbm} dBm</div>
              <div class="text-[9px] ui-muted font-mono">Ant: ${s.ant1_dbm}/${s.ant2_dbm}</div>
            </div>
            <div class="ui-tertiary px-2.5 py-1.5 rounded border">
              <div class="ui-sec text-[10px]">即時傳輸 (Tx)</div>
              <div class="font-bold text-emerald-500 font-mono text-sm">${s.tx_mbps} Mbps</div>
              <div class="text-[9px] ui-muted font-mono truncate max-w-[95px]">${s.tx_bitrate_str}</div>
            </div>
            <div class="ui-tertiary px-2.5 py-1.5 rounded border">
              <div class="ui-sec text-[10px]">即時接收 (Rx)</div>
              <div class="font-bold text-cyan-500 font-mono text-sm">${s.rx_mbps} Mbps</div>
              <div class="text-[9px] ui-muted font-mono truncate max-w-[95px]">${s.rx_bitrate_str}</div>
            </div>
          </div>
        </div>
      `;
    }).join('');

    if (window.lucide) lucide.createIcons();

    // Add point to real-time chart
    updateChart(sta.signal_dbm, sta.tx_mbps);

  } else {
    document.getElementById('card-station-mac-quick').innerText = '尚無連線裝置';
    document.getElementById('card-station-signal').innerText = '- dBm';
    document.getElementById('card-station-rate').innerText = '- Mbps';
    document.getElementById('card-station-retries').innerText = '重傳封包遺失: 0';
    document.getElementById('card-ant1').innerText = '-';
    document.getElementById('card-ant2').innerText = '-';
    
    stationsList.innerHTML = `
      <div class="text-center py-6 ui-sec text-xs">
        <i data-lucide="wifi-off" class="w-8 h-8 mx-auto text-slate-400 mb-2"></i>
        目前尚無用戶端裝置連入 DiagnosticAP 熱點
      </div>
    `;
    if (window.lucide) lucide.createIcons();
  }
}

// ==========================================
// 4. Mode Switching Controls (via WS / REST)
// ==========================================
function sendSwitchMode(action, band='5G', chan='36') {
  const box = document.getElementById('mode-output-box');
  box.classList.remove('hidden');
  box.innerText = `⏳ 正在執行切換: ${action} ${band || ''} Ch ${chan || ''}，請稍候約 3~5 秒...`;

  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      type: 'switch_mode',
      action: action,
      band: band,
      channel: chan
    }));
  } else {
    fetch('/api/mode/switch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, band, channel: chan })
    })
    .then(r => r.json())
    .then(handleSwitchResult)
    .catch(e => { box.innerText = `❌ 連線發生錯誤: ${e}`; });
  }
}

function handleSwitchResult(data) {
  const box = document.getElementById('mode-output-box');
  box.innerText = data.output || (data.success ? '✅ 操作完成' : '❌ 操作失敗');
  setTimeout(requestStatusRefresh, 1500);
}

// ==========================================
// 5. Ping Diagnostic via WS
// ==========================================
function runPingWs() {
  const target = document.getElementById('ping-target').value;
  const count = parseInt(document.getElementById('ping-count').value) || 5;
  const btn = document.getElementById('btn-run-ping');
  const out = document.getElementById('ping-output');

  btn.disabled = true;
  btn.classList.add('opacity-50');
  out.innerText = `🚀 正在對 ${target} 發送 ${count} 個 Ping 封包測量延遲與無線抖動...`;

  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      type: 'ping',
      target: target,
      count: count
    }));
  } else {
    fetch('/api/diagnostics/ping', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target, count })
    })
    .then(r => r.json())
    .then(handlePingResult)
    .catch(err => { out.innerText = `Ping 測試失敗: ${err}`; });
  }
}

function handlePingResult(data) {
  const btn = document.getElementById('btn-run-ping');
  const out = document.getElementById('ping-output');
  const statsRow = document.getElementById('ping-stats-row');

  btn.disabled = false;
  btn.classList.remove('opacity-50');

  out.innerText = data.raw_output;
  statsRow.classList.remove('hidden');
  
  document.getElementById('ping-min').innerText = (data.stats.min_ms || '-') + ' ms';
  document.getElementById('ping-avg').innerText = (data.stats.avg_ms || '-') + ' ms';
  document.getElementById('ping-max').innerText = (data.stats.max_ms || '-') + ' ms';
  document.getElementById('ping-loss').innerText = data.loss_percent + '%';
  document.getElementById('ping-loss').className = data.loss_percent === 0 ? 'text-base font-bold font-mono text-emerald-500' : 'text-base font-bold font-mono text-rose-500';
}

// ==========================================
// 6. iPerf3 Server Toggle
// ==========================================
function sendIperf3Toggle() {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'iperf3_toggle' }));
  } else {
    fetch('/api/diagnostics/iperf3/toggle', { method: 'POST' })
      .then(fetchIperf3Status);
  }
}

function updateIperf3Ui(data) {
  const badge = document.getElementById('iperf3-status-badge');
  const btn = document.getElementById('btn-iperf3-toggle');

  if (!data.installed) {
    badge.innerText = '尚未安裝 iperf3';
    badge.className = 'px-2.5 py-1 text-xs rounded bg-amber-500/20 text-amber-500 border border-amber-500/40';
    btn.innerText = '未安裝';
    btn.disabled = true;
    btn.classList.add('opacity-50');
  } else if (data.running) {
    badge.innerText = '執行中 (5201)';
    badge.className = 'px-2.5 py-1 text-xs rounded bg-emerald-500/20 text-emerald-500 border border-emerald-500/40 font-bold';
    btn.innerText = '停止服務';
    btn.disabled = false;
    btn.classList.remove('opacity-50');
  } else {
    badge.innerText = '已停止';
    badge.className = 'px-2.5 py-1 text-xs rounded ui-pill border';
    btn.innerText = '啟動服務';
    btn.disabled = false;
    btn.classList.remove('opacity-50');
  }
}

function fetchIperf3Status() {
  fetch('/api/diagnostics/iperf3/status')
    .then(r => r.json())
    .then(updateIperf3Ui);
}

// ==========================================
// 7. QR Code Generator (URL & Wi-Fi)
// ==========================================
function renderQr(type) {
  currentQrType = type;
  const qrBox = document.getElementById('qrcode-box');
  const btnUrl = document.getElementById('btn-qr-url');
  const btnWifi = document.getElementById('btn-qr-wifi');
  const qrLabel = document.getElementById('qr-label');
  const qrInstructions = document.getElementById('qr-instructions');
  const targetUrlEl = document.getElementById('qr-target-url');

  if (!qrBox) return;
  qrBox.innerHTML = "";

  const host = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
    ? '10.42.0.1' 
    : window.location.hostname;
  const targetUrl = `http://${host}:8080/#speedtest`;

  let qrText = "";

  if (type === 'url') {
    qrText = targetUrl;
    targetUrlEl.innerText = targetUrl;
    qrLabel.innerText = "手機掃描開啟測速網頁";
    qrInstructions.innerHTML = `💡 操作提示：手機先連上 <span class="font-mono text-cyan-500 font-bold">DiagnosticAP</span>，再以相機掃描 QR Code 即可進入測速。`;

    btnUrl.className = "px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 text-white shadow-sm transition flex items-center space-x-1.5";
    btnWifi.className = "px-3.5 py-1.5 rounded-lg text-xs font-semibold ui-pill border hover:opacity-80 transition flex items-center space-x-1.5";

  } else {
    const ssid = document.getElementById('card-ssid').innerText || 'DiagnosticAP';
    qrText = `WIFI:T:WPA;S:${ssid};P:88888888;;`;
    targetUrlEl.innerText = `SSID: ${ssid} | 密碼: 88888888`;
    qrLabel.innerText = "手機相機對準一鍵加入 Wi-Fi";
    qrInstructions.innerHTML = `📱 操作提示：打開 iPhone 或 Android 相機對準 QR Code，點擊彈出的「<span class="font-bold text-amber-500">加入 ${ssid} 網路</span>」即可連線！`;

    btnWifi.className = "px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 text-white shadow-sm transition flex items-center space-x-1.5";
    btnUrl.className = "px-3.5 py-1.5 rounded-lg text-xs font-semibold ui-pill border hover:opacity-80 transition flex items-center space-x-1.5";
  }

  if (typeof QRCode !== 'undefined') {
    qrInstance = new QRCode(qrBox, {
      text: qrText,
      width: 150,
      height: 150,
      colorDark: "#0f172a",
      colorLight: "#ffffff",
      correctLevel: QRCode.CorrectLevel.M
    });
  } else {
    qrBox.innerHTML = `<span class="text-xs text-rose-500">QR 函式庫載入中...</span>`;
  }

  if (window.lucide) lucide.createIcons();
}

function copyTargetUrl() {
  const url = document.getElementById('qr-target-url').innerText;
  navigator.clipboard.writeText(url).then(() => {
    const btn = document.getElementById('copy-btn-text');
    btn.innerText = "已複製！";
    setTimeout(() => { btn.innerText = "複製"; }, 1500);
  });
}

// ==========================================
// 8. Tabs & Chart Logic
// ==========================================
function switchTab(tabId) {
  const tabs = ['tab-speedtest', 'tab-ping', 'tab-chart', 'tab-packets', 'tab-channels', 'tab-guide'];
  tabs.forEach(t => {
    const el = document.getElementById(t);
    const nav = document.getElementById('nav-' + t);
    if (!el) return;
    if (t === tabId) {
      el.classList.remove('hidden');
      if (nav) {
        nav.classList.add('text-emerald-500', 'border-b-2', 'border-emerald-500');
        nav.classList.remove('ui-sec');
      }
    } else {
      el.classList.add('hidden');
      if (nav) {
        nav.classList.remove('text-emerald-500', 'border-b-2', 'border-emerald-500');
        nav.classList.add('ui-sec');
      }
    }
  });

  if (window.lucide) lucide.createIcons();
}

function initChart() {
  const ctx = document.getElementById('liveRssiChart').getContext('2d');
  const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
  const isDark = currentTheme === 'dark';
  const gridColor = isDark ? '#334155' : '#e2e8f0';
  const textColor = isDark ? '#94a3b8' : '#64748b';
  const legendColor = isDark ? '#cbd5e1' : '#1e293b';

  liveChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: chartLabels,
      datasets: [
        {
          label: '訊號強度 RSSI (dBm)',
          data: rssiData,
          borderColor: '#fbbf24',
          backgroundColor: 'rgba(251, 191, 36, 0.1)',
          yAxisID: 'yRSSI',
          tension: 0.3,
          borderWidth: 2,
          pointRadius: 3
        },
        {
          label: '傳輸速率 Tx (Mbps)',
          data: txRateData,
          borderColor: '#10b981',
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          yAxisID: 'yMbps',
          tension: 0.3,
          borderWidth: 2,
          pointRadius: 3
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false,
      },
      scales: {
        x: {
          grid: { color: gridColor },
          ticks: { color: textColor, font: { size: 10 } }
        },
        yRSSI: {
          type: 'linear',
          position: 'left',
          min: -95,
          max: -30,
          grid: { color: gridColor },
          ticks: { color: isDark ? '#fbbf24' : '#d97706', callback: val => val + ' dBm' }
        },
        yMbps: {
          type: 'linear',
          position: 'right',
          min: 0,
          max: 300,
          grid: { drawOnChartArea: false },
          ticks: { color: '#10b981', callback: val => val + ' M' }
        }
      },
      plugins: {
        legend: {
          labels: { color: legendColor, font: { size: 11 } }
        }
      }
    }
  });
}

function clearChartData() {
  chartLabels.length = 0;
  rssiData.length = 0;
  txRateData.length = 0;
  if (liveChart) liveChart.update();
}

function updateChart(sig, txMbps) {
  if (!liveChart) return;
  const now = new Date();
  const timeStr = `${now.getHours().toString().padStart(2,'0')}:${now.getMinutes().toString().padStart(2,'0')}:${now.getSeconds().toString().padStart(2,'0')}`;
  
  chartLabels.push(timeStr);
  rssiData.push(sig);
  txRateData.push(txMbps);

  if (chartLabels.length > maxChartPoints) {
    chartLabels.shift();
    rssiData.shift();
    txRateData.shift();
  }

  liveChart.update('none');
}

// ==========================================
// 9. In-Browser Speedtest Engine
// ==========================================
async function startBrowserSpeedtest() {
  const btn = document.getElementById('btn-browser-speedtest');
  const dlVal = document.getElementById('speed-dl-val');
  const ulVal = document.getElementById('speed-ul-val');
  const progressBar = document.getElementById('speed-progress-bar');
  const progress = document.getElementById('speed-progress');

  btn.disabled = true;
  btn.classList.add('opacity-50');
  progressBar.classList.remove('hidden');
  progress.style.width = '10%';
  dlVal.innerText = '測試中...';
  ulVal.innerText = '-- Mbps';

  try {
    // 1. Download Speedtest (Fetch 30MB stream)
    const dlStart = performance.now();
    const dlRes = await fetch('/api/speedtest/download?size_mb=30');
    const reader = dlRes.body.getReader();
    let receivedBytes = 0;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      receivedBytes += value.length;
      progress.style.width = `${Math.min(10 + (receivedBytes / (30 * 1024 * 1024)) * 40, 50)}%`;
    }

    const dlDuration = (performance.now() - dlStart) / 1000;
    const dlMbps = ((receivedBytes * 8) / (dlDuration * 1_000_000)).toFixed(1);
    dlVal.innerHTML = `${dlMbps} <span class="text-sm font-normal ui-sec">Mbps</span>`;

    // 2. Upload Speedtest (Send 15MB stream)
    progress.style.width = '60%';
    ulVal.innerText = '測試中...';

    const ulSize = 15 * 1024 * 1024;
    const ulBuffer = new Uint8Array(ulSize);
    const ulRes = await fetch('/api/speedtest/upload', {
      method: 'POST',
      body: ulBuffer
    });
    const ulData = await ulRes.json();
    progress.style.width = '100%';

    ulVal.innerHTML = `${ulData.mbps} <span class="text-sm font-normal ui-sec">Mbps</span>`;

  } catch (e) {
    dlVal.innerText = '測試失敗';
    ulVal.innerText = '測試失敗';
  } finally {
    btn.disabled = false;
    btn.classList.remove('opacity-50');
    setTimeout(() => { progressBar.classList.add('hidden'); }, 1500);
  }
}

// ==========================================
// 10. Wireless Learning Guide Collapsible & TOC
// ==========================================
function toggleGuideSection(secId) {
  const body = document.getElementById(`guide-${secId}-body`) || document.getElementById(`guide-sec-${secId}-body`);
  const icon = document.getElementById(`guide-${secId}-icon`) || document.getElementById(`guide-sec-${secId}-icon`);
  if (!body) return;

  const isHidden = body.classList.contains('hidden');
  if (isHidden) {
    body.classList.remove('hidden');
    if (icon) icon.style.transform = 'rotate(180deg)';
  } else {
    body.classList.add('hidden');
    if (icon) icon.style.transform = 'rotate(0deg)';
  }
}

function toggleAllGuideSections(expand) {
  const bodies = document.querySelectorAll('[id^="guide-"][id$="-body"]');
  bodies.forEach(body => {
    const baseId = body.id.replace(/-body$/, '');
    const icon = document.getElementById(`${baseId}-icon`);
    if (expand) {
      body.classList.remove('hidden');
      if (icon) icon.style.transform = 'rotate(180deg)';
    } else {
      body.classList.add('hidden');
      if (icon) icon.style.transform = 'rotate(0deg)';
    }
  });
}

function jumpToGuideSection(secId) {
  const body = document.getElementById(`guide-${secId}-body`) || document.getElementById(`guide-sec-${secId}-body`);
  const icon = document.getElementById(`guide-${secId}-icon`) || document.getElementById(`guide-sec-${secId}-icon`);
  const container = document.getElementById(`guide-${secId}`) || document.getElementById(`guide-sec-${secId}`);

  if (body && body.classList.contains('hidden')) {
    body.classList.remove('hidden');
    if (icon) icon.style.transform = 'rotate(180deg)';
  }

  if (container) {
    container.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}

// ==========================================
// 11. Command Clipboard Copy Helper
// ==========================================
function copyText(btn, text) {
  if (!text && btn) {
    const parent = btn.closest('.ui-subcard') || btn.parentElement;
    const codeEl = parent ? parent.querySelector('.cmd-text') : null;
    if (codeEl) text = codeEl.innerText.trim();
  }
  if (!text) return;

  function onSuccess() {
    if (btn) {
      const origHtml = btn.innerHTML;
      btn.innerHTML = `<i data-lucide="check" class="w-3 h-3 text-emerald-400"></i><span class="text-emerald-400 font-bold">已複製</span>`;
      if (window.lucide) lucide.createIcons();
      setTimeout(() => {
        btn.innerHTML = origHtml;
        if (window.lucide) lucide.createIcons();
      }, 2000);
    }
  }

  function fallback() {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.top = '-9999px';
    textArea.style.opacity = '0';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    try {
      document.execCommand('copy');
      onSuccess();
    } catch (err) {
      console.error('Copy failed', err);
    }
    document.body.removeChild(textArea);
  }

  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).then(onSuccess, fallback);
  } else {
    fallback();
  }
}
