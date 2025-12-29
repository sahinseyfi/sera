const state = {
  status: null,
  poller: null,
  lcdActiveInput: null,
  history: {
    metric: 'dht_temp',
    range: '24h',
    lastFetch: 0,
    data: null,
    render: null,
    hoverBound: false,
  },
  historyTimer: null,
  eventsTimer: null,
  eventsLastFetch: 0,
  settingsSavedTimer: null,
};

const HISTORY_METRICS = {
  dht_temp: { label: 'DHT22 Sıcaklık', unit: '°C' },
  dht_hum: { label: 'DHT22 Nem', unit: '%' },
  ds18_temp: { label: 'DS18B20 Sıcaklık', unit: '°C' },
  lux: { label: 'Lux', unit: 'lx' },
  soil_ch0: { label: 'Toprak CH0', unit: 'raw' },
  soil_ch1: { label: 'Toprak CH1', unit: 'raw' },
  soil_ch2: { label: 'Toprak CH2', unit: 'raw' },
  soil_ch3: { label: 'Toprak CH3', unit: 'raw' },
};

const HISTORY_RANGES = {
  '24h': { seconds: 24 * 3600, label: 'Son 24 saat' },
  '7d': { seconds: 7 * 24 * 3600, label: 'Son 7 gün' },
};

function adminHeaders() {
  const headers = { 'Content-Type': 'application/json' };
  const token = localStorage.getItem('adminToken');
  if (token) headers['X-Admin-Token'] = token;
  return headers;
}

function formatDate(ts) {
  if (!ts) return '---';
  try {
    return new Date(ts).toLocaleTimeString();
  } catch (e) {
    return ts;
  }
}

function formatUnixSeconds(ts) {
  if (!ts) return '---';
  try {
    return new Date(ts * 1000).toLocaleTimeString();
  } catch (e) {
    return ts;
  }
}

function formatUnixMinutes(ts) {
  if (!ts) return '---';
  try {
    return new Date(ts * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch (e) {
    return ts;
  }
}

function formatAge(seconds) {
  if (seconds === null || seconds === undefined) return 'Veri yok';
  const value = Number(seconds);
  if (Number.isNaN(value)) return 'Veri yok';
  return `Veri gecikmesi: ${value.toFixed(1)} sn`;
}

function formatDuration(seconds) {
  if (seconds === null || seconds === undefined) return '--';
  const value = Number(seconds);
  if (Number.isNaN(value)) return '--';
  if (value < 60) return `${Math.round(value)} sn`;
  if (value < 3600) return `${Math.round(value / 60)} dk`;
  if (value < 86400) return `${(value / 3600).toFixed(1)} sa`;
  return `${(value / 86400).toFixed(1)} gün`;
}

function formatEnergy(wh) {
  if (wh === null || wh === undefined) return '--';
  const value = Number(wh);
  if (Number.isNaN(value)) return '--';
  if (value >= 1000) return `${(value / 1000).toFixed(2)} kWh`;
  return `${value.toFixed(1)} Wh`;
}

function formatCurrencyTry(value) {
  if (value === null || value === undefined) return '--';
  const num = Number(value);
  if (Number.isNaN(num)) return '--';
  return `${num.toFixed(2)} TL`;
}

function minutesRemaining(untilTs) {
  if (!untilTs) return 0;
  const diff = Number(untilTs) - (Date.now() / 1000);
  if (Number.isNaN(diff) || diff <= 0) return 0;
  return Math.ceil(diff / 60);
}

function minutesRemainingFrom(startTs, minutes) {
  if (!startTs || !minutes) return 0;
  const until = Number(startTs) + (Number(minutes) * 60);
  return minutesRemaining(until);
}

function formatMetricValue(value, metric) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '--';
  const meta = HISTORY_METRICS[metric] || { unit: '' };
  const num = Number(value);
  if (meta.unit === 'raw') return `${Math.round(num)}`;
  const precision = meta.unit === '°C' ? 1 : meta.unit === '%' ? 1 : 1;
  return `${num.toFixed(precision)} ${meta.unit}`.trim();
}

function downsamplePoints(points, maxPoints) {
  if (points.length <= maxPoints) return points;
  const step = Math.ceil(points.length / maxPoints);
  const sampled = [];
  for (let i = 0; i < points.length; i += step) sampled.push(points[i]);
  if (sampled[sampled.length - 1] !== points[points.length - 1]) {
    sampled.push(points[points.length - 1]);
  }
  return sampled;
}

function calibrationInputId(channel, type) {
  const suffix = channel.charAt(0).toUpperCase() + channel.slice(1);
  return `cal${type === 'dry' ? 'Dry' : 'Wet'}${suffix}`;
}

function statusBadge(id, status) {
  const el = document.getElementById(id);
  if (!el) return;
  const labelMap = {
    ok: { text: 'OK', cls: 'text-bg-success' },
    simulated: { text: 'SIM', cls: 'text-bg-info' },
    unavailable: { text: 'YOK', cls: 'text-bg-warning' },
    missing: { text: 'YOK', cls: 'text-bg-warning' },
    error: { text: 'HATA', cls: 'text-bg-danger' },
    crc_error: { text: 'CRC', cls: 'text-bg-warning' },
  };
  const meta = labelMap[status] || { text: '---', cls: 'text-bg-secondary' };
  el.textContent = meta.text;
  el.className = `badge ${meta.cls}`;
}

function renderStatus(status) {
  const badge = document.getElementById('safeModeBadge');
  if (badge) {
    badge.textContent = status.safe_mode ? 'SAFE MODE AÇIK' : 'SAFE MODE KAPALI';
    badge.style.background = status.safe_mode ? 'rgba(248,113,113,0.18)' : 'rgba(74,222,128,0.18)';
    badge.style.borderColor = status.safe_mode ? '#f87171' : '#4ade80';
  }
  const last = document.getElementById('lastUpdated');
  if (last) last.textContent = formatDate(status.timestamp);
  const ageEl = document.getElementById('dataAge');
  if (ageEl) {
    ageEl.textContent = formatAge(status.data_age_sec);
    ageEl.classList.remove('text-danger', 'text-secondary');
    ageEl.classList.add(status.data_stale ? 'text-danger' : 'text-secondary');
  }
  try { if (window.renderDashboard) window.renderDashboard(status); } catch (_) {}
  try { if (window.renderControl) window.renderControl(status); } catch (_) {}
  try { if (window.renderSettings) window.renderSettings(status); } catch (_) {}
  try { if (window.renderPins) window.renderPins(status); } catch (_) {}
  try { if (window.renderLcd) window.renderLcd(status); } catch (_) {}
}

function poll() {
  fetch('/api/status')
    .then(r => r.json())
    .then(data => {
      state.status = data;
      renderStatus(data);
    })
    .catch(() => {});
}

window.initDashboard = function() {
  poll();
  state.poller = setInterval(poll, 2500);
  initHistory();
  initEvents();
};

window.renderDashboard = function(data) {
  if (!document.getElementById('dhtTemp')) return;
  const readings = data.sensor_readings || {};
  const dht = readings.dht22 || {};
  const ds = readings.ds18b20 || {};
  const lux = readings.bh1750 || {};
  const soil = readings.soil || {};
  const sensorFaults = data.sensor_faults || {};
  const automationState = data.automation_state || {};
  const manualRemaining = minutesRemaining(automationState.manual_override_until_ts);
  const blockRemaining = minutesRemaining(automationState.block_until_ts);
  const manualActive = manualRemaining > 0;
  const blockActive = blockRemaining > 0;
  const minOffRemaining = minutesRemainingFrom(automationState.last_auto_off_ts, automationState.min_off_minutes);
  const minOffActive = minOffRemaining > 0;
  const luxMax = Number(data.automation?.lux_max || 0);
  const luxTooHigh = luxMax > 0 && lux.lux != null && Number(lux.lux) >= luxMax;
  const okMinutesValue = Number(automationState.ok_minutes_today || 0);
  const targetMinutesValue = Number(automationState.target_ok_minutes || 0);
  const targetReached = automationState.enabled && targetMinutesValue > 0 && okMinutesValue >= targetMinutesValue;
  const dhtAvg = dht.averages || {};
  const fmtAvg = (avg) => {
    if (!avg || avg.temperature == null || avg.humidity == null) return '--';
    return `${avg.temperature}°C / ${avg.humidity}%`;
  };
  document.getElementById('dhtTemp').textContent = dht.temperature ?? '--';
  document.getElementById('dhtHum').textContent = dht.humidity ?? '--';
  statusBadge('dhtStatus', dht.status);
  const avg1 = document.getElementById('dhtAvg1m');
  const avg5 = document.getElementById('dhtAvg5m');
  const avg30 = document.getElementById('dhtAvg30m');
  if (avg1) avg1.textContent = fmtAvg(dhtAvg['1m']);
  if (avg5) avg5.textContent = fmtAvg(dhtAvg['5m']);
  if (avg30) avg30.textContent = fmtAvg(dhtAvg['30m']);
  document.getElementById('dsTemp').textContent = ds.temperature ?? '--';
  statusBadge('dsStatus', ds.status);
  document.getElementById('luxValue').textContent = lux.lux ?? '--';
  statusBadge('luxStatus', lux.status);
  document.getElementById('soil0').textContent = soil.ch0 ?? '--';
  document.getElementById('soil1').textContent = soil.ch1 ?? '--';
  const soil2 = document.getElementById('soil2');
  const soil3 = document.getElementById('soil3');
  if (soil2) soil2.textContent = soil.ch2 ?? '--';
  if (soil3) soil3.textContent = soil.ch3 ?? '--';
  statusBadge('soilStatus', soil.status);
  const actWrap = document.getElementById('actuatorList');
  actWrap.innerHTML = '';
  Object.entries(data.actuator_state || {}).forEach(([name, info]) => {
    const item = document.createElement('div');
    item.className = 'd-flex flex-column gap-1 p-2 border rounded-3';
    item.style.borderColor = info.state ? '#22c55e' : '#cbd5f5';
    const stateText = info.state ? 'ON' : 'OFF';
    const lastChange = formatUnixSeconds(info.last_change_ts);
    const reason = info.reason ? ` · ${info.reason}` : '';
    const gpio = info.gpio_pin != null ? `GPIO ${info.gpio_pin}` : 'GPIO ?';
    const polarity = info.active_low ? 'active-low' : 'active-high';
    item.innerHTML = `
      <div class="d-flex justify-content-between align-items-center">
        <span class="small text-uppercase fw-semibold">${name}</span>
        <span class="pill small" style="border-color:${info.state ? '#22c55e' : '#64748b'}">${stateText}</span>
      </div>
      <div class="small text-secondary">${gpio} · ${polarity}</div>
      <div class="small text-secondary">Son değişiklik: ${lastChange}${reason}</div>
    `;
    actWrap.appendChild(item);
  });
  const alertBox = document.getElementById('alerts');
  alertBox.innerHTML = '';
  (data.alerts || []).slice(-5).forEach(a => {
    const div = document.createElement('div');
    div.textContent = `[${a.severity}] ${formatDate(a.ts)} ${a.message}`;
    alertBox.appendChild(div);
  });
  const autoBadge = document.getElementById('automationBadge');
  if (autoBadge) {
    if (!automationState.enabled) {
      autoBadge.textContent = 'Otomasyon Kapalı';
    } else if (automationState.lux_paused) {
      autoBadge.textContent = 'Otomasyon Pasif (Lux Hatası)';
    } else if (luxTooHigh) {
      autoBadge.textContent = 'Otomasyon Pasif (Lux Max)';
    } else if (manualActive) {
      autoBadge.textContent = `Otomasyon Manuel Override (${manualRemaining} dk)`;
    } else if (minOffActive) {
      autoBadge.textContent = `Otomasyon Min Kapalı (${minOffRemaining} dk)`;
    } else if (blockActive) {
      autoBadge.textContent = 'Otomasyon Bloklu';
    } else if (targetReached) {
      autoBadge.textContent = 'Otomasyon Hedef Tamam';
    } else {
      autoBadge.textContent = 'Otomasyon Açık';
    }
  }
  const targetBadge = document.getElementById('autoTargetBadge');
  if (targetBadge) {
    if (targetReached) {
      targetBadge.classList.remove('d-none');
    } else {
      targetBadge.classList.add('d-none');
    }
  }
  const okMinutes = document.getElementById('autoOkMinutes');
  if (okMinutes) {
    okMinutes.textContent = automationState.ok_minutes_today ?? '--';
    okMinutes.classList.toggle('text-success', targetReached);
  }
  const targetMinutes = document.getElementById('autoTargetMinutes');
  if (targetMinutes) {
    targetMinutes.textContent = automationState.target_ok_minutes ?? '--';
    targetMinutes.classList.toggle('text-success', targetReached);
  }
  const remainingMinutes = document.getElementById('autoRemainingMinutes');
  if (remainingMinutes) {
    const remaining = Math.max(0, Math.ceil(targetMinutesValue - okMinutesValue));
    remainingMinutes.textContent = targetMinutesValue ? `${remaining} dk` : '--';
    remainingMinutes.classList.toggle('text-success', targetReached);
  }
  const windowState = document.getElementById('autoWindowState');
  if (windowState) {
    const range = data.automation?.window_start && data.automation?.window_end
      ? `${data.automation.window_start}-${data.automation.window_end}`
      : '';
    const label = automationState.within_window ? 'içinde' : 'dışında';
    windowState.textContent = range ? `${range} (${label})` : label;
  }
  const resetTime = document.getElementById('autoResetTime');
  if (resetTime) {
    resetTime.textContent = data.automation?.reset_time ?? '00:00';
  }
  const overrideState = document.getElementById('autoOverrideState');
  if (overrideState) {
    overrideState.textContent = manualActive ? `${manualRemaining} dk` : 'Yok';
  }
  const blockState = document.getElementById('autoBlockState');
  if (blockState) {
    blockState.textContent = blockActive ? `${blockRemaining} dk` : 'Yok';
  }
  const minOffState = document.getElementById('autoMinOffState');
  if (minOffState) {
    minOffState.textContent = minOffActive ? `${minOffRemaining} dk` : 'Yok';
  }
  const autoSummary = document.getElementById('autoSummary');
  if (autoSummary) {
    let summary = 'Otomasyon kapalı.';
    if (automationState.enabled) {
      if (automationState.lux_paused) {
        summary = 'Lux hatası nedeniyle pasif.';
      } else if (manualActive) {
        summary = `Manuel override aktif (${manualRemaining} dk).`;
      } else if (minOffActive) {
        summary = `Min kapalı süresi aktif (${minOffRemaining} dk).`;
      } else if (blockActive) {
        summary = `Bloklu (${blockRemaining} dk).`;
      } else if (targetReached) {
        summary = 'Hedefe ulaşıldı.';
      } else {
        summary = automationState.within_window ? 'Aktif (pencere içinde).' : 'Aktif (pencere dışında).';
      }
    }
    autoSummary.textContent = summary;
  }
  const autoCard = document.getElementById('automationCard');
  if (autoCard) {
    autoCard.classList.remove('border-success', 'border-warning', 'border-danger', 'border-info', 'border-secondary', 'border-2');
    let borderClass = 'border-secondary';
    if (automationState.enabled) {
      if (automationState.lux_paused) {
        borderClass = 'border-danger';
      } else if (luxTooHigh) {
        borderClass = 'border-info';
      } else if (manualActive || blockActive) {
        borderClass = 'border-warning';
      } else if (minOffActive) {
        borderClass = 'border-info';
      } else if (targetReached) {
        borderClass = 'border-success';
      } else if (automationState.within_window) {
        borderClass = 'border-success';
      } else {
        borderClass = 'border-info';
      }
    }
    autoCard.classList.add('border-2', borderClass);
  }
  const lastOffReason = document.getElementById('autoLastOffReason');
  if (lastOffReason) {
    const reason = automationState.last_auto_off_reason || '';
    if (!reason) {
      lastOffReason.textContent = '--';
    } else if (reason === 'automation_window') {
      lastOffReason.textContent = 'Pencere dışında';
    } else if (reason === 'automation_target_met') {
      lastOffReason.textContent = 'Hedefe ulaşıldı';
    } else if (reason === 'automation_lux_max') {
      lastOffReason.textContent = 'LUX_MAX üstü';
    } else if (reason === 'automation_max_block') {
      lastOffReason.textContent = 'Maks blok';
    } else if (reason === 'automation_block') {
      lastOffReason.textContent = 'Bloklu';
    } else {
      lastOffReason.textContent = reason;
    }
  }

  const banner = document.getElementById('statusBanner');
  if (banner) {
    const items = [];
    if (data.safe_mode) {
      items.push({ level: 'warning', text: 'SAFE MODE açık: manuel kontrol kilitli.' });
    }
    if (sensorFaults.pump) {
      items.push({ level: 'danger', text: 'Pompa kilitli: toprak nem sensörü hatası.' });
    }
    if (sensorFaults.heater) {
      items.push({ level: 'danger', text: 'Isıtıcı kilitli: sıcaklık sensörü hatası.' });
    }
    if (automationState.enabled && automationState.lux_paused) {
      items.push({ level: 'warning', text: 'Lux otomasyonu pasif: BH1750 hatası.' });
    }
    if (automationState.enabled && luxTooHigh) {
      items.push({ level: 'info', text: `Lux otomasyonu pasif: LUX_MAX (${luxMax}) üstü.` });
    }
    if (manualActive) {
      items.push({ level: 'warning', text: `Otomasyon manuel override aktif (${manualRemaining} dk).` });
    }
    if (blockActive) {
      items.push({ level: 'warning', text: `Otomasyon bloklu (pencere sonuna ${blockRemaining} dk).` });
    }
    if (minOffActive) {
      items.push({ level: 'info', text: `Otomasyon min kapalı süresi (${minOffRemaining} dk).` });
    }
    if (targetReached) {
      items.push({ level: 'success', text: 'Lux otomasyonu hedefe ulaştı.' });
    }
    if (data.data_age_sec === null || data.data_age_sec === undefined) {
      items.push({ level: 'danger', text: 'Sensör verisi alınamıyor.' });
    } else if (data.data_stale) {
      items.push({
        level: 'danger',
        text: `Sensör verisi güncel değil. ${formatAge(data.data_age_sec)} (limit ${data.stale_threshold_sec || 15} sn).`,
      });
    } else {
      items.push({
        level: 'info',
        text: `${formatAge(data.data_age_sec)} (limit ${data.stale_threshold_sec || 15} sn).`,
      });
    }
    const sensorStatuses = [
      { label: 'DHT22', status: dht.status },
      { label: 'DS18B20', status: ds.status },
      { label: 'BH1750', status: lux.status },
      { label: 'ADS1115', status: soil.status },
    ];
    sensorStatuses.forEach(s => {
      if (s.status && !['ok', 'simulated'].includes(s.status)) {
        items.push({ level: 'warning', text: `${s.label} okuma hatası (${s.status}).` });
      }
    });
    banner.innerHTML = items
      .map(item => `<div class="alert alert-${item.level} py-2 mb-2 small">${item.text}</div>`)
      .join('');
  }

  const energy = data.energy || {};
  const energy24 = energy.window_24h || {};
  const energy7d = energy.window_7d || {};
  const energyTotal24 = document.getElementById('energyTotal24h');
  const energyTotal7 = document.getElementById('energyTotal7d');
  if (energyTotal24) energyTotal24.textContent = formatEnergy(energy24.total_wh ?? 0);
  if (energyTotal7) energyTotal7.textContent = formatEnergy(energy7d.total_wh ?? 0);
  const energyCost24 = document.getElementById('energyCost24h');
  const energyCost7 = document.getElementById('energyCost7d');
  if (energyCost24) energyCost24.textContent = formatCurrencyTry(energy24.cost_try ?? null);
  if (energyCost7) energyCost7.textContent = formatCurrencyTry(energy7d.cost_try ?? null);
  const renderEnergyList = (containerId, channels) => {
    const wrap = document.getElementById(containerId);
    if (!wrap) return;
    const entries = Object.entries(channels || {})
      .map(([name, info]) => ({ name, ...info }))
      .filter(item => Number(item.energy_wh || 0) > 0 || Number(item.seconds || 0) > 0)
      .sort((a, b) => Number(b.energy_wh || 0) - Number(a.energy_wh || 0));
    if (!entries.length) {
      wrap.innerHTML = '<div class="text-secondary">Veri yok.</div>';
      return;
    }
    wrap.innerHTML = entries.map(item => {
      const powerText = item.power_w ? `${item.power_w}W x${item.quantity || 1}` : 'Güç yok';
      const duration = formatDuration(item.seconds || 0);
      const energyText = formatEnergy(item.energy_wh || 0);
      return `
        <div class="energy-item">
          <div>
            <div class="fw-semibold small">${item.name}</div>
            <div class="text-secondary small">${powerText} · ${duration}</div>
          </div>
          <div class="small fw-semibold">${energyText}</div>
        </div>`;
    }).join('');
  };
  renderEnergyList('energyList24h', energy24.channels);
  renderEnergyList('energyList7d', energy7d.channels);
  const energyNote = document.getElementById('energyNote');
  if (energyNote) {
    energyNote.textContent = energy.only_timed ? 'Not: Sadece süreli (seconds) kayıtları kullanılır.' : '';
  }

  const healthWrap = document.getElementById('sensorHealthList');
  if (healthWrap) {
    const health = data.sensor_health || {};
    const order = ['dht22', 'ds18b20', 'bh1750', 'soil'];
    const rows = order.map(key => ({ key, ...(health[key] || {}) }));
    healthWrap.innerHTML = rows.map(item => {
      const status = item.status || 'unknown';
      const ok = ['ok', 'simulated'].includes(status);
      const badgeClass = ok ? 'text-bg-success' : (status === 'unknown' ? 'text-bg-secondary' : 'text-bg-danger');
      let detail = 'Aktif';
      if (!ok) {
        const offline = formatDuration(item.offline_seconds);
        detail = `Son OK: ${offline} önce`;
      }
      return `
        <div class="health-item">
          <div>
            <div class="fw-semibold small">${item.label || item.key}</div>
            <div class="text-secondary small">${detail}</div>
          </div>
          <span class="badge ${badgeClass}">${status}</span>
        </div>`;
    }).join('');
    const limitNote = document.getElementById('sensorHealthNote');
    if (limitNote) {
      const limitSeconds = rows[0]?.offline_limit_seconds;
      limitNote.textContent = limitSeconds ? `Offline uyarı limiti: ${formatDuration(limitSeconds)}.` : '';
    }
  }
};

function sendActuator(name, state, seconds) {
  const payload = { state: state ? 'on' : 'off' };
  if (seconds !== undefined) payload.seconds = seconds;
  return fetch(`/api/actuator/${name}`, {
    method: 'POST',
    headers: adminHeaders(),
    body: JSON.stringify(payload),
  }).then(async r => {
    if (!r.ok) {
      const body = await r.json();
      throw new Error(body.error || 'Hata');
    }
    return r.json();
  });
}

window.initControl = function() {
  poll();
  state.poller = setInterval(poll, 2500);
  const refreshBtn = document.getElementById('refreshNow');
  if (refreshBtn) refreshBtn.onclick = poll;
  const emergencyBtn = document.getElementById('emergencyStop');
  if (emergencyBtn) {
    emergencyBtn.onclick = () => {
      if (emergencyBtn.disabled) return;
      fetch('/api/emergency_stop', { method: 'POST', headers: adminHeaders() }).then(() => poll());
    };
  }
};

window.renderControl = function(data) {
  const wrap = document.getElementById('controlCards');
  if (!wrap) return;
  const banner = document.getElementById('controlBanner');
  const sensorFaults = data.sensor_faults || {};
  if (banner) {
    const items = [];
    if (data.safe_mode) {
      items.push({ level: 'warning', text: 'SAFE MODE açık: manuel kontrol kilitli.' });
    } else {
      items.push({ level: 'info', text: 'SAFE MODE kapalı: manuel kontrol açık.' });
    }
    if (sensorFaults.pump) {
      items.push({ level: 'danger', text: 'Pompa kilitli: toprak nem sensörü hatası.' });
    }
    if (sensorFaults.heater) {
      items.push({ level: 'danger', text: 'Isıtıcı kilitli: sıcaklık sensörü hatası.' });
    }
    banner.innerHTML = items
      .map(item => `<div class="alert alert-${item.level} py-2 mb-2 small">${item.text}</div>`)
      .join('');
  }
  wrap.innerHTML = '';
  const actuators = Object.entries(data.actuator_state || {});
  if (!actuators.length) {
    wrap.innerHTML = '<div class="text-secondary small">Röleler yüklenemedi. Lütfen /api/status kontrol et.</div>';
    return;
  }
  const cooldowns = data.cooldowns || {};
  const pumpMax = Number(data.limits?.pump_max_seconds || 0);
  actuators.forEach(([name, info]) => {
    const col = document.createElement('div');
    col.className = 'col-md-4';
    const isPump = name.includes('PUMP');
    const isHeater = name.includes('HEATER');
    const heaterLocked = isHeater && !!sensorFaults.heater;
    const pumpLocked = isPump && !!sensorFaults.pump;
    const heaterMax = data.limits?.heater_max_seconds;
    const heaterNote = isHeater && heaterMax ? `Isıtıcı max: ${heaterMax} sn` : '';
    const heaterLockNote = heaterLocked ? 'Isıtıcı kilitli: sensör hatası.' : '';
    const pumpCooldown = isPump && cooldowns[name] != null ? Number(cooldowns[name]) : 0;
    const pumpNote = isPump
      ? (pumpCooldown > 0 ? `Pompa cooldown: ${Math.ceil(pumpCooldown)} sn` : 'Pompa hazır.')
      : '';
    col.innerHTML = `
      <div class="card h-100">
        <div class="card-body d-flex flex-column gap-2">
          <div>
            <div class="d-flex justify-content-between align-items-center">
              <h6 class="mb-0">${info.description || name}</h6>
              <span class="pill small" style="border-color:${info.state ? '#22c55e' : '#64748b'}">${name}</span>
            </div>
            <div class="text-secondary small">GPIO ${info.gpio_pin} · ${info.active_low ? 'active-low' : 'active-high'}</div>
            ${heaterNote ? `<div class="small text-secondary">${heaterNote}</div>` : ''}
            ${heaterLockNote ? `<div class="small text-danger">${heaterLockNote}</div>` : ''}
            ${pumpNote ? `<div class="small text-secondary">${pumpNote}</div>` : ''}
            ${pumpLocked ? '<div class="small text-danger">Pompa kilitli: sensör hatası.</div>' : ''}
          </div>
          <div class="d-flex gap-2 align-items-center flex-wrap mt-auto">
            <input class="form-control form-control-sm w-25" data-field="sec" type="number" min="1" placeholder="sn">
            <button class="btn btn-success flex-fill" data-action="on">Aç</button>
            <button class="btn btn-outline-info flex-fill" data-action="pulse">Süreli</button>
            <button class="btn btn-outline-secondary flex-fill" data-action="off">Kapat</button>
          </div>
        </div>
      </div>`;
    col.querySelectorAll('button').forEach(btn => {
      btn.onclick = () => {
        const action = btn.dataset.action === 'on';
        const input = col.querySelector('[data-field="sec"]');
        const secRaw = input ? parseInt(input.value || '0', 10) : 0;
        const seconds = Number.isFinite(secRaw) && secRaw > 0 ? secRaw : null;
        if (btn.dataset.action === 'pulse') {
          if (!seconds) return alert('Süreli için saniye gir.');
          sendActuator(name, true, seconds).then(poll).catch(e => alert(e.message));
          return;
        }
        if (btn.dataset.action === 'on') {
          if (isPump) {
            const finalSec = seconds || pumpMax || 5;
            sendActuator(name, true, finalSec).then(poll).catch(e => alert(e.message));
            return;
          }
          sendActuator(name, true, seconds || undefined).then(poll).catch(e => alert(e.message));
          return;
        }
        sendActuator(name, false).then(poll).catch(e => alert(e.message));
      };
    });
    wrap.appendChild(col);
  });
  const lockControls = !!data.safe_mode;
  wrap.querySelectorAll('button, input').forEach(btn => {
    btn.disabled = lockControls;
  });
  if (sensorFaults.pump) {
    wrap.querySelectorAll('[data-action="on"], [data-action="pulse"]').forEach(btn => {
      const card = btn.closest('.card');
      if (!card) return;
      const pill = card.querySelector('.pill');
      if (!pill) return;
      if (!String(pill.textContent || '').includes('PUMP')) return;
      btn.disabled = true;
    });
  }
  const emergencyBtn = document.getElementById('emergencyStop');
  if (emergencyBtn) emergencyBtn.disabled = false;
};

function initHistory() {
  const metricSelect = document.getElementById('historyMetric');
  const rangeLabel = document.getElementById('historyRangeLabel');
  if (!metricSelect || !rangeLabel) return;
  metricSelect.value = state.history.metric;
  metricSelect.onchange = () => {
    state.history.metric = metricSelect.value;
    fetchHistory(true);
  };
  document.querySelectorAll('[data-history-range]').forEach(btn => {
    btn.addEventListener('click', () => {
      setHistoryRange(btn.dataset.historyRange);
    });
  });
  updateHistoryRangeButtons();
  fetchHistory(true);
  if (state.historyTimer) clearInterval(state.historyTimer);
  state.historyTimer = setInterval(() => fetchHistory(false), 30000);
  window.addEventListener('resize', () => {
    if (state.history.data) renderHistory(state.history.data);
  });
  bindHistoryHover();
}

function bindHistoryHover() {
  if (state.history.hoverBound) return;
  const canvas = document.getElementById('historyChart');
  const tooltip = document.getElementById('historyTooltip');
  if (!canvas || !tooltip) return;
  const wrap = canvas.closest('.history-chart-wrap');
  if (!wrap) return;
  canvas.addEventListener('mousemove', (event) => {
    const render = state.history.render;
    if (!render || !render.points || !render.points.length) {
      tooltip.classList.add('d-none');
      return;
    }
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    const { pad, plotW, plotH, points, minVal, maxVal, metric } = render;
    if (x < pad || x > pad + plotW || y < pad || y > pad + plotH) {
      tooltip.classList.add('d-none');
      return;
    }
    const ratio = (x - pad) / plotW;
    const idx = Math.min(points.length - 1, Math.max(0, Math.round(ratio * (points.length - 1))));
    const point = points[idx];
    let value = Number(point[1]);
    if (metric === 'dht_temp' || metric === 'ds18_temp') {
      value = Math.min(maxVal, Math.max(minVal, value));
    }
    const timeLabel = formatUnixMinutes(point[0]);
    const valueLabel = formatMetricValue(value, metric);
    tooltip.textContent = `${timeLabel} · ${valueLabel}`;
    tooltip.classList.remove('d-none');
    const wrapRect = wrap.getBoundingClientRect();
    const left = Math.min(wrapRect.width - tooltip.offsetWidth - 8, Math.max(8, x + 12));
    const top = Math.max(8, y - 28);
    tooltip.style.left = `${left}px`;
    tooltip.style.top = `${top}px`;
  });
  canvas.addEventListener('mouseleave', () => tooltip.classList.add('d-none'));
  window.addEventListener('scroll', () => tooltip.classList.add('d-none'), { passive: true });
  state.history.hoverBound = true;
}

function setHistoryRange(range) {
  if (!HISTORY_RANGES[range]) return;
  state.history.range = range;
  updateHistoryRangeButtons();
  fetchHistory(true);
}

function updateHistoryRangeButtons() {
  document.querySelectorAll('[data-history-range]').forEach(btn => {
    const active = btn.dataset.historyRange === state.history.range;
    btn.classList.toggle('active', active);
  });
}

function fetchHistory(force) {
  const metric = state.history.metric;
  if (!HISTORY_METRICS[metric]) return;
  const now = Date.now() / 1000;
  if (!force && now - state.history.lastFetch < 25) return;
  const rangeMeta = HISTORY_RANGES[state.history.range] || HISTORY_RANGES['24h'];
  const from = now - rangeMeta.seconds;
  fetch(`/api/history?metric=${encodeURIComponent(metric)}&from=${from}&to=${now}`)
    .then(r => r.json())
    .then(data => {
      state.history.lastFetch = now;
      state.history.data = data;
      renderHistory(data);
    })
    .catch(() => {
      renderHistory({ metric, points: [] });
    });
}

function renderHistory(data) {
  const metric = data.metric || state.history.metric;
  const rangeMeta = HISTORY_RANGES[state.history.range] || HISTORY_RANGES['24h'];
  const rangeLabel = document.getElementById('historyRangeLabel');
  if (rangeLabel) {
    const metricLabel = HISTORY_METRICS[metric]?.label || metric;
    rangeLabel.textContent = `${metricLabel} · ${rangeMeta.label}`;
  }
  const downloadLink = document.getElementById('historyDownload');
  if (downloadLink && data.from_ts && data.to_ts) {
    const fromTs = encodeURIComponent(data.from_ts);
    const toTs = encodeURIComponent(data.to_ts);
    downloadLink.href = `/api/history?metric=${encodeURIComponent(metric)}&from=${fromTs}&to=${toTs}&format=csv`;
  }
  const pointsRaw = Array.isArray(data.points) ? data.points : [];
  const points = pointsRaw.filter(p => p && p.length > 1 && p[1] !== null && !Number.isNaN(Number(p[1])));
  const countEl = document.getElementById('historyCount');
  if (countEl) countEl.textContent = points.length ? `${points.length}` : '--';
  const emptyEl = document.getElementById('historyEmpty');
  if (emptyEl) emptyEl.classList.toggle('d-none', points.length > 0);
  const updatedEl = document.getElementById('historyUpdated');
  if (updatedEl) updatedEl.textContent = new Date().toLocaleTimeString();

  if (!points.length) {
    const minEl = document.getElementById('historyMin');
    const maxEl = document.getElementById('historyMax');
    const lastEl = document.getElementById('historyLast');
    if (minEl) minEl.textContent = '--';
    if (maxEl) maxEl.textContent = '--';
    if (lastEl) lastEl.textContent = '--';
    const canvas = document.getElementById('historyChart');
    if (canvas) drawHistoryChart(canvas, [], metric);
    return;
  }

  let minVal = Number.POSITIVE_INFINITY;
  let maxVal = Number.NEGATIVE_INFINITY;
  for (const point of points) {
    const value = Number(point[1]);
    if (value < minVal) minVal = value;
    if (value > maxVal) maxVal = value;
  }
  const lastVal = points[points.length - 1][1];
  const minEl = document.getElementById('historyMin');
  const maxEl = document.getElementById('historyMax');
  const lastEl = document.getElementById('historyLast');
  if (minEl) minEl.textContent = formatMetricValue(minVal, metric);
  if (maxEl) maxEl.textContent = formatMetricValue(maxVal, metric);
  if (lastEl) lastEl.textContent = formatMetricValue(lastVal, metric);
  const canvas = document.getElementById('historyChart');
  if (canvas) {
    const sampled = downsamplePoints(points, 800);
    drawHistoryChart(canvas, sampled, metric, minVal, maxVal);
  }
}

function drawHistoryChart(canvas, points, metric, minVal, maxVal) {
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  const width = canvas.clientWidth || 600;
  const height = canvas.clientHeight || 240;
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.floor(width * dpr);
  canvas.height = Math.floor(height * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);
  const labelFont = '11px "Space Grotesk", sans-serif';
  const tickCount = 5;
  const labelValues = [];
  if (minVal != null && maxVal != null) {
    const rawRange = (maxVal - minVal) || 1;
    for (let i = 0; i < tickCount; i += 1) {
      labelValues.push(maxVal - (rawRange * (i / (tickCount - 1))));
    }
  }
  ctx.font = labelFont;
  const labelWidths = labelValues
    .filter(v => v != null && Number.isFinite(Number(v)))
    .map(v => ctx.measureText(formatMetricValue(Number(v), metric)).width);
  const labelPad = labelWidths.length ? Math.max(...labelWidths) + 16 : 36;
  const pad = Math.max(36, Math.min(64, Math.ceil(labelPad)));
  const plotW = width - pad - 18;
  const plotH = height - pad * 2;

  ctx.strokeStyle = 'rgba(148,163,184,0.4)';
  ctx.lineWidth = 1;
  for (let i = 0; i < tickCount; i += 1) {
    const y = pad + (plotH * (i / (tickCount - 1)));
    ctx.beginPath();
    ctx.moveTo(pad, y);
    ctx.lineTo(pad + plotW, y);
    ctx.stroke();
  }

  if (!points.length) {
    ctx.fillStyle = '#94a3b8';
    ctx.font = '12px "Space Grotesk", sans-serif';
    ctx.fillText('Veri yok', pad, height / 2);
    return;
  }

  if (metric === 'dht_temp' || metric === 'ds18_temp') {
    minVal = 0;
    maxVal = 45;
  }
  const range = (maxVal - minVal) || 1;
  const labelColor = '#64748b';
  ctx.fillStyle = labelColor;
  ctx.font = labelFont;
  ctx.textAlign = 'right';
  ctx.textBaseline = 'middle';
  for (let i = 0; i < tickCount; i += 1) {
    const y = pad + (plotH * (i / (tickCount - 1)));
    const value = maxVal - (range * (i / (tickCount - 1)));
    ctx.fillText(formatMetricValue(value, metric), pad - 10, y);
  }

  const timeLabelY = pad + plotH + 8;
  const timeLabelColor = '#64748b';
  ctx.fillStyle = timeLabelColor;
  ctx.textBaseline = 'top';
  if (points.length >= 2) {
    const labelCount = Math.max(4, Math.min(8, Math.floor(plotW / 110)));
    for (let i = 0; i < labelCount; i += 1) {
      const idx = Math.round((points.length - 1) * (i / (labelCount - 1)));
      const ts = points[idx][0];
      const x = pad + (plotW * (i / (labelCount - 1)));
      ctx.textAlign = i === 0 ? 'left' : (i === labelCount - 1 ? 'right' : 'center');
      ctx.fillText(formatUnixMinutes(ts), x, timeLabelY);
    }
  }

  if (points.length < 2) {
    let value = Number(points[0][1]);
    if (metric === 'dht_temp' || metric === 'ds18_temp') {
      value = Math.min(maxVal, Math.max(minVal, value));
    }
    const x = pad + plotW;
    const y = pad + plotH - ((value - minVal) / range) * plotH;
    ctx.fillStyle = '#0ea5a4';
    ctx.beginPath();
    ctx.arc(x, y, 3, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#0f172a';
    ctx.font = labelFont;
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    ctx.fillText(formatMetricValue(value, metric), x + 6, y);
    const ts = points[0][0];
    ctx.fillStyle = timeLabelColor;
    ctx.font = labelFont;
    ctx.textAlign = 'right';
    ctx.textBaseline = 'top';
    ctx.fillText(formatUnixMinutes(ts), pad + plotW, timeLabelY);
    return;
  }

  ctx.beginPath();
  points.forEach((point, idx) => {
    let value = Number(point[1]);
    if (metric === 'dht_temp' || metric === 'ds18_temp') {
      value = Math.min(maxVal, Math.max(minVal, value));
    }
    const x = pad + (plotW * (idx / (points.length - 1)));
    const y = pad + plotH - ((value - minVal) / range) * plotH;
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  const gradient = ctx.createLinearGradient(0, pad, 0, pad + plotH);
  gradient.addColorStop(0, 'rgba(14, 165, 164, 0.25)');
  gradient.addColorStop(1, 'rgba(14, 165, 164, 0.02)');
  ctx.lineTo(pad + plotW, pad + plotH);
  ctx.lineTo(pad, pad + plotH);
  ctx.closePath();
  ctx.fillStyle = gradient;
  ctx.fill();

  ctx.beginPath();
  points.forEach((point, idx) => {
    let value = Number(point[1]);
    if (metric === 'dht_temp' || metric === 'ds18_temp') {
      value = Math.min(maxVal, Math.max(minVal, value));
    }
    const x = pad + (plotW * (idx / (points.length - 1)));
    const y = pad + plotH - ((value - minVal) / range) * plotH;
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.strokeStyle = '#0ea5a4';
  ctx.lineWidth = 2;
  ctx.stroke();

  const lastPoint = points[points.length - 1];
  if (lastPoint) {
    let value = Number(lastPoint[1]);
    if (metric === 'dht_temp' || metric === 'ds18_temp') {
      value = Math.min(maxVal, Math.max(minVal, value));
    }
    const x = pad + plotW;
    const y = pad + plotH - ((value - minVal) / range) * plotH;
    ctx.fillStyle = '#0ea5a4';
    ctx.beginPath();
    ctx.arc(x, y, 3, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#0f172a';
    ctx.font = '11px "Space Grotesk", sans-serif';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    ctx.fillText(formatMetricValue(value, metric), x + 6, y);
  }
  state.history.render = {
    points,
    metric,
    minVal,
    maxVal,
    pad,
    plotW,
    plotH,
  };
}

function initEvents() {
  const wrap = document.getElementById('eventLog');
  if (!wrap) return;
  fetchEvents(true);
  if (state.eventsTimer) clearInterval(state.eventsTimer);
  state.eventsTimer = setInterval(() => fetchEvents(false), 8000);
}

function fetchEvents(force) {
  const now = Date.now() / 1000;
  if (!force && state.eventsLastFetch && now - state.eventsLastFetch < 7) return;
  state.eventsLastFetch = now;
  fetch('/api/events?limit=50')
    .then(r => r.json())
    .then(data => renderEvents(data))
    .catch(() => renderEvents({ events: [] }));
}

function renderEvents(data) {
  const wrap = document.getElementById('eventLog');
  if (!wrap) return;
  const updated = document.getElementById('eventLogUpdated');
  if (updated) updated.textContent = new Date().toLocaleTimeString();
  const eventsRaw = Array.isArray(data.events) ? data.events : [];
  const disabledNames = new Set(
    Object.entries((state.status && state.status.actuator_state) || {})
      .filter(([, info]) => info && info.enabled === false)
      .map(([name]) => name.toUpperCase())
  );
  const events = eventsRaw.filter(event => {
    if (event.category !== 'actuator') return true;
    const metaName = event.meta && event.meta.name;
    if (!metaName) return true;
    return !disabledNames.has(String(metaName).toUpperCase());
  });
  if (!events.length) {
    wrap.textContent = 'Olay yok.';
    return;
  }
  const levelBadge = (level) => {
    const map = {
      info: 'text-bg-info',
      warning: 'text-bg-warning',
      error: 'text-bg-danger',
    };
    return map[level] || 'text-bg-secondary';
  };
  const categoryBadge = (category) => {
    const map = {
      actuator: 'text-bg-primary',
      alert: 'text-bg-warning',
      system: 'text-bg-secondary',
    };
    return map[category] || 'text-bg-secondary';
  };
  wrap.innerHTML = events.map(event => {
    const time = event.ts ? formatUnixSeconds(event.ts) : '--';
    const levelCls = levelBadge(event.level);
    const catCls = categoryBadge(event.category);
    const message = event.message || '';
    return `
      <div class="event-item">
        <span class="text-secondary">${time}</span>
        <span class="badge ${catCls}">${event.category || '-'}</span>
        <span class="badge ${levelCls}">${event.level || '-'}</span>
        <span>${message}</span>
      </div>`;
  }).join('');
}

function updateAdminTokenStatus() {
  const status = document.getElementById('adminTokenStatus');
  if (!status) return;
  const token = localStorage.getItem('adminToken') || '';
  status.textContent = token ? 'Durum: Kaydedildi' : 'Durum: Yok';
}

function initAdminToken() {
  const input = document.getElementById('adminTokenInput');
  if (!input) return;
  input.value = localStorage.getItem('adminToken') || '';
  updateAdminTokenStatus();
}

window.initSettings = function() {
  poll();
  state.poller = setInterval(poll, 2500);
  document.getElementById('saveSettings').onclick = saveSettings;
  initAdminToken();
  bindCalibrationButtons();
};

function bindCalibrationButtons() {
  document.querySelectorAll('[data-cal-channel]').forEach(btn => {
    btn.onclick = () => {
      const channel = btn.dataset.calChannel;
      const type = btn.dataset.calType;
      const soil = state.status?.sensor_readings?.soil || {};
      const value = soil[channel];
      if (value === null || value === undefined) {
        alert('Toprak sensör verisi yok.');
        return;
      }
      const inputId = calibrationInputId(channel, type);
      const input = document.getElementById(inputId);
      if (input) input.value = Math.round(Number(value));
    };
  });
}

function saveSettings() {
  const savedNote = document.getElementById('settingsSavedNote');
  if (savedNote) savedNote.textContent = '';
  if (state.settingsSavedTimer) {
    clearTimeout(state.settingsSavedTimer);
    state.settingsSavedTimer = null;
  }
  const readFloat = (id, fallback) => {
    const el = document.getElementById(id);
    if (!el) return fallback;
    const value = parseFloat(el.value);
    return Number.isFinite(value) ? value : fallback;
  };
  const readInt = (id, fallback) => {
    const el = document.getElementById(id);
    if (!el) return fallback;
    const value = parseInt(el.value, 10);
    return Number.isFinite(value) ? value : fallback;
  };
  const currentLimits = state.status?.limits || {};
  const currentAuto = state.status?.automation || {};
  const currentAlerts = state.status?.alerts_config || {};
  const tokenInput = document.getElementById('adminTokenInput');
  if (tokenInput) {
    const value = tokenInput.value.trim();
    if (value) {
      localStorage.setItem('adminToken', value);
    } else {
      localStorage.removeItem('adminToken');
    }
    updateAdminTokenStatus();
  }
  const heaterCutoff = readFloat('heaterCutoff', currentLimits.heater_cutoff_temp ?? 0);
  const heaterTLow = readFloat('heaterTLow', currentAuto.heater_t_low ?? 18);
  const heaterTHigh = readFloat('heaterTHigh', currentAuto.heater_t_high ?? 20);
  const heaterNightTLow = readFloat('heaterNightTLow', currentAuto.heater_night_t_low ?? 17);
  const heaterNightTHigh = readFloat('heaterNightTHigh', currentAuto.heater_night_t_high ?? 19);
  const pumpDryThreshold = readFloat('pumpDryThreshold', currentAuto.pump_dry_threshold ?? 0);
  const alertOfflineMinutes = readFloat('alertOfflineMinutes', currentAlerts.sensor_offline_minutes ?? 5);
  const alertTempHigh = readFloat('alertTempHigh', currentAlerts.temp_high_c ?? 30);
  const alertTempLow = readFloat('alertTempLow', currentAlerts.temp_low_c ?? 0);
  const alertHumHigh = readFloat('alertHumHigh', currentAlerts.hum_high_pct ?? 85);
  const alertHumLow = readFloat('alertHumLow', currentAlerts.hum_low_pct ?? 0);
  const soilCalibration = {};
  ['ch0', 'ch1', 'ch2', 'ch3'].forEach(channel => {
    const dryRaw = parseFloat(document.getElementById(calibrationInputId(channel, 'dry')).value);
    const wetRaw = parseFloat(document.getElementById(calibrationInputId(channel, 'wet')).value);
    soilCalibration[channel] = {
      dry: Number.isFinite(dryRaw) ? dryRaw : null,
      wet: Number.isFinite(wetRaw) ? wetRaw : null,
    };
  });
  const payload = {
    safe_mode: document.getElementById('safeModeToggle').checked,
    limits: {
      pump_max_seconds: readInt('pumpMax', currentLimits.pump_max_seconds ?? 15),
      pump_cooldown_seconds: readInt('pumpCooldown', currentLimits.pump_cooldown_seconds ?? 60),
      heater_max_seconds: readInt('heaterMax', currentLimits.heater_max_seconds ?? 300),
      heater_cutoff_temp: heaterCutoff,
      energy_kwh_low: readFloat('energyKwhLow', currentLimits.energy_kwh_low ?? 2.330),
      energy_kwh_high: readFloat('energyKwhHigh', currentLimits.energy_kwh_high ?? 3.451),
      energy_kwh_threshold: readFloat('energyKwhThreshold', currentLimits.energy_kwh_threshold ?? 240),
    },
    automation: {
      enabled: document.getElementById('autoEnabled').value === 'true',
      lux_ok: readInt('luxOk', currentAuto.lux_ok ?? 350),
      lux_max: readInt('luxMax', currentAuto.lux_max ?? 0),
      target_ok_minutes: readInt('targetMinutes', currentAuto.target_ok_minutes ?? 300),
      window_start: document.getElementById('windowStart').value,
      window_end: document.getElementById('windowEnd').value,
      reset_time: document.getElementById('resetTime').value,
      min_on_minutes: readInt('minOnMinutes', currentAuto.min_on_minutes ?? 0),
      min_off_minutes: readInt('minOffMinutes', currentAuto.min_off_minutes ?? 0),
      max_block_minutes: readInt('maxBlockMinutes', currentAuto.max_block_minutes ?? 0),
      manual_override_minutes: readInt('manualOverrideMinutes', currentAuto.manual_override_minutes ?? 0),
      heater_enabled: document.getElementById('heaterEnabled').value === 'true',
      heater_sensor: document.getElementById('heaterSensor').value,
      heater_t_low: heaterTLow,
      heater_t_high: heaterTHigh,
      heater_max_minutes: readInt('heaterMaxMinutes', currentAuto.heater_max_minutes ?? 0),
      heater_min_off_minutes: readInt('heaterMinOffMinutes', currentAuto.heater_min_off_minutes ?? 0),
      heater_manual_override_minutes: readInt('heaterManualOverrideMinutes', currentAuto.heater_manual_override_minutes ?? 0),
      heater_fan_required: document.getElementById('heaterFanRequired').value === 'true',
      heater_night_enabled: document.getElementById('heaterNightEnabled').value === 'true',
      heater_night_start: document.getElementById('heaterNightStart').value,
      heater_night_end: document.getElementById('heaterNightEnd').value,
      heater_night_t_low: heaterNightTLow,
      heater_night_t_high: heaterNightTHigh,
      pump_enabled: document.getElementById('pumpEnabled').value === 'true',
      pump_soil_channel: document.getElementById('pumpSoilChannel').value,
      pump_dry_threshold: pumpDryThreshold,
      pump_dry_when_above: document.getElementById('pumpDryWhenAbove').value === 'true',
      pump_pulse_seconds: readInt('pumpPulseSeconds', currentAuto.pump_pulse_seconds ?? 5),
      pump_max_daily_seconds: readInt('pumpMaxDailySeconds', currentAuto.pump_max_daily_seconds ?? 0),
      pump_window_start: document.getElementById('pumpWindowStart').value,
      pump_window_end: document.getElementById('pumpWindowEnd').value,
      pump_manual_override_minutes: readInt('pumpManualOverrideMinutes', currentAuto.pump_manual_override_minutes ?? 0),
      fan_enabled: document.getElementById('fanEnabled').value === 'true',
      fan_rh_high: readInt('fanRhHigh', currentAuto.fan_rh_high ?? 70),
      fan_rh_low: readInt('fanRhLow', currentAuto.fan_rh_low ?? 60),
      fan_max_minutes: readInt('fanMaxMinutes', currentAuto.fan_max_minutes ?? 0),
      fan_min_off_minutes: readInt('fanMinOffMinutes', currentAuto.fan_min_off_minutes ?? 0),
      fan_manual_override_minutes: readInt('fanManualOverrideMinutes', currentAuto.fan_manual_override_minutes ?? 0),
      fan_night_enabled: document.getElementById('fanNightEnabled').value === 'true',
      fan_night_start: document.getElementById('fanNightStart').value,
      fan_night_end: document.getElementById('fanNightEnd').value,
      fan_night_rh_high: readInt('fanNightRhHigh', currentAuto.fan_night_rh_high ?? 75),
      fan_night_rh_low: readInt('fanNightRhLow', currentAuto.fan_night_rh_low ?? 65),
      fan_periodic_enabled: document.getElementById('fanPeriodicEnabled').value === 'true',
      fan_periodic_every_minutes: readInt('fanPeriodicEvery', currentAuto.fan_periodic_every_minutes ?? 0),
      fan_periodic_duration_minutes: readInt('fanPeriodicDuration', currentAuto.fan_periodic_duration_minutes ?? 0),
      fan_periodic_night_enabled: document.getElementById('fanPeriodicNightEnabled').value === 'true',
      fan_periodic_night_every_minutes: readInt('fanPeriodicNightEvery', currentAuto.fan_periodic_night_every_minutes ?? 0),
      fan_periodic_night_duration_minutes: readInt('fanPeriodicNightDuration', currentAuto.fan_periodic_night_duration_minutes ?? 0),
      soil_calibration: soilCalibration,
    },
    alerts: {
      sensor_offline_minutes: Math.max(0, Math.round(alertOfflineMinutes)),
      temp_high_c: alertTempHigh,
      temp_low_c: alertTempLow,
      hum_high_pct: alertHumHigh,
      hum_low_pct: alertHumLow,
    },
  };
  fetch('/api/settings', {
    method: 'POST',
    headers: adminHeaders(),
    body: JSON.stringify(payload),
  }).then(async r => {
    const body = await r.json().catch(() => ({}));
    if (!r.ok) {
      const msg = body.error || 'Ayar kaydi basarisiz.';
      alert(msg);
      if (savedNote) savedNote.textContent = '';
      return;
    }
    if (savedNote) {
      savedNote.textContent = 'Kaydedildi';
      state.settingsSavedTimer = setTimeout(() => {
        savedNote.textContent = '';
        state.settingsSavedTimer = null;
      }, 3000);
    }
    poll();
  });
}

window.renderSettings = function(data) {
  if (!document.getElementById('safeModeToggle')) return;
  const limits = data.limits || {};
  document.getElementById('safeModeToggle').checked = data.safe_mode;
  document.getElementById('pumpMax').value = limits.pump_max_seconds ?? 15;
  document.getElementById('pumpCooldown').value = limits.pump_cooldown_seconds ?? 60;
  document.getElementById('heaterMax').value = limits.heater_max_seconds ?? 300;
  document.getElementById('heaterCutoff').value = limits.heater_cutoff_temp ?? 30;
  document.getElementById('energyKwhLow').value = limits.energy_kwh_low ?? 2.330;
  document.getElementById('energyKwhHigh').value = limits.energy_kwh_high ?? 3.451;
  document.getElementById('energyKwhThreshold').value = limits.energy_kwh_threshold ?? 240;
  const auto = data.automation || {};
  document.getElementById('autoEnabled').value = auto.enabled ? 'true' : 'false';
  document.getElementById('luxOk').value = auto.lux_ok ?? 350;
  document.getElementById('luxMax').value = auto.lux_max ?? 0;
  document.getElementById('targetMinutes').value = auto.target_ok_minutes ?? 300;
  document.getElementById('windowStart').value = auto.window_start ?? '06:00';
  document.getElementById('windowEnd').value = auto.window_end ?? '22:00';
  document.getElementById('resetTime').value = auto.reset_time ?? '00:00';
  document.getElementById('minOnMinutes').value = auto.min_on_minutes ?? 0;
  document.getElementById('minOffMinutes').value = auto.min_off_minutes ?? 0;
  document.getElementById('maxBlockMinutes').value = auto.max_block_minutes ?? 0;
  document.getElementById('manualOverrideMinutes').value = auto.manual_override_minutes ?? 0;
  document.getElementById('heaterEnabled').value = auto.heater_enabled ? 'true' : 'false';
  document.getElementById('heaterSensor').value = auto.heater_sensor ?? 'dht22';
  document.getElementById('heaterTLow').value = auto.heater_t_low ?? 18;
  document.getElementById('heaterTHigh').value = auto.heater_t_high ?? 20;
  document.getElementById('heaterMaxMinutes').value = auto.heater_max_minutes ?? 5;
  document.getElementById('heaterMinOffMinutes').value = auto.heater_min_off_minutes ?? 2;
  document.getElementById('heaterManualOverrideMinutes').value = auto.heater_manual_override_minutes ?? 10;
  document.getElementById('heaterFanRequired').value = auto.heater_fan_required === false ? 'false' : 'true';
  document.getElementById('heaterNightEnabled').value = auto.heater_night_enabled ? 'true' : 'false';
  document.getElementById('heaterNightStart').value = auto.heater_night_start ?? '22:00';
  document.getElementById('heaterNightEnd').value = auto.heater_night_end ?? '06:00';
  document.getElementById('heaterNightTLow').value = auto.heater_night_t_low ?? 17;
  document.getElementById('heaterNightTHigh').value = auto.heater_night_t_high ?? 19;
  document.getElementById('pumpEnabled').value = auto.pump_enabled ? 'true' : 'false';
  document.getElementById('pumpSoilChannel').value = auto.pump_soil_channel ?? 'ch0';
  document.getElementById('pumpDryThreshold').value = auto.pump_dry_threshold ?? 0;
  document.getElementById('pumpDryWhenAbove').value = auto.pump_dry_when_above ? 'true' : 'false';
  document.getElementById('pumpPulseSeconds').value = auto.pump_pulse_seconds ?? 5;
  document.getElementById('pumpMaxDailySeconds').value = auto.pump_max_daily_seconds ?? 60;
  document.getElementById('pumpWindowStart').value = auto.pump_window_start ?? '06:00';
  document.getElementById('pumpWindowEnd').value = auto.pump_window_end ?? '22:00';
  document.getElementById('pumpManualOverrideMinutes').value = auto.pump_manual_override_minutes ?? 10;
  document.getElementById('fanEnabled').value = auto.fan_enabled ? 'true' : 'false';
  document.getElementById('fanRhHigh').value = auto.fan_rh_high ?? 80;
  document.getElementById('fanRhLow').value = auto.fan_rh_low ?? 70;
  document.getElementById('fanMaxMinutes').value = auto.fan_max_minutes ?? 3;
  document.getElementById('fanMinOffMinutes').value = auto.fan_min_off_minutes ?? 2;
  document.getElementById('fanManualOverrideMinutes').value = auto.fan_manual_override_minutes ?? 10;
  document.getElementById('fanNightEnabled').value = auto.fan_night_enabled ? 'true' : 'false';
  document.getElementById('fanNightStart').value = auto.fan_night_start ?? '22:00';
  document.getElementById('fanNightEnd').value = auto.fan_night_end ?? '06:00';
  document.getElementById('fanNightRhHigh').value = auto.fan_night_rh_high ?? 85;
  document.getElementById('fanNightRhLow').value = auto.fan_night_rh_low ?? 75;
  document.getElementById('fanPeriodicEnabled').value = auto.fan_periodic_enabled ? 'true' : 'false';
  document.getElementById('fanPeriodicEvery').value = auto.fan_periodic_every_minutes ?? 60;
  document.getElementById('fanPeriodicDuration').value = auto.fan_periodic_duration_minutes ?? 2;
  document.getElementById('fanPeriodicNightEnabled').value = auto.fan_periodic_night_enabled ? 'true' : 'false';
  document.getElementById('fanPeriodicNightEvery').value = auto.fan_periodic_night_every_minutes ?? 90;
  document.getElementById('fanPeriodicNightDuration').value = auto.fan_periodic_night_duration_minutes ?? 2;
  const alertsCfg = data.alerts_config || {};
  document.getElementById('alertOfflineMinutes').value = alertsCfg.sensor_offline_minutes ?? 5;
  document.getElementById('alertTempHigh').value = alertsCfg.temp_high_c ?? 30;
  document.getElementById('alertTempLow').value = alertsCfg.temp_low_c ?? 0;
  document.getElementById('alertHumHigh').value = alertsCfg.hum_high_pct ?? 85;
  document.getElementById('alertHumLow').value = alertsCfg.hum_low_pct ?? 0;
  const calibration = auto.soil_calibration || {};
  ['ch0', 'ch1', 'ch2', 'ch3'].forEach(channel => {
    const entry = calibration[channel] || {};
    const dryInput = document.getElementById(calibrationInputId(channel, 'dry'));
    const wetInput = document.getElementById(calibrationInputId(channel, 'wet'));
    if (dryInput) dryInput.value = entry.dry ?? '';
    if (wetInput) wetInput.value = entry.wet ?? '';
  });
};

window.initPins = function() {
  poll();
  state.poller = setInterval(poll, 4000);
  document.getElementById('savePins').onclick = savePins;
};

window.renderPins = function(data) {
  const body = document.querySelector('#pinsTable tbody');
  if (!body) return;
  body.innerHTML = '';
  const channels = Object.entries(data.actuator_state || {}).map(([name, info]) => ({
    name,
    gpio_pin: info.gpio_pin,
    active_low: info.active_low,
    description: info.description || name,
    power_w: info.power_w,
    quantity: info.quantity,
    voltage_v: info.voltage_v,
  }));
  channels.forEach(ch => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><input class="form-control form-control-sm" data-field="name" value="${ch.name}"></td>
      <td><input class="form-control form-control-sm" data-field="gpio_pin" type="number" value="${ch.gpio_pin}"></td>
      <td class="text-center"><input class="form-check-input" data-field="active_low" type="checkbox" ${ch.active_low ? 'checked' : ''}></td>
      <td><input class="form-control form-control-sm" data-field="description" value="${ch.description}"></td>
      <td><input class="form-control form-control-sm" data-field="power_w" type="number" step="0.1" value="${ch.power_w ?? ''}"></td>
      <td><input class="form-control form-control-sm" data-field="quantity" type="number" step="1" value="${ch.quantity ?? 1}"></td>
      <td><input class="form-control form-control-sm" data-field="voltage_v" type="number" step="0.1" value="${ch.voltage_v ?? ''}"></td>`;
    body.appendChild(tr);
  });
};

function savePins() {
  const rows = Array.from(document.querySelectorAll('#pinsTable tbody tr'));
  const channels = rows.map(r => {
    const nameI = r.querySelector('[data-field="name"]');
    const gpioI = r.querySelector('[data-field="gpio_pin"]');
    const activeI = r.querySelector('[data-field="active_low"]');
    const descI = r.querySelector('[data-field="description"]');
    const powerI = r.querySelector('[data-field="power_w"]');
    const quantityI = r.querySelector('[data-field="quantity"]');
    const voltageI = r.querySelector('[data-field="voltage_v"]');
    const powerRaw = powerI ? powerI.value.trim() : '';
    const quantityRaw = quantityI ? quantityI.value.trim() : '';
    const voltageRaw = voltageI ? voltageI.value.trim() : '';
    const powerVal = powerRaw === '' ? 0 : parseFloat(powerRaw);
    const quantityVal = quantityRaw === '' ? 1 : parseInt(quantityRaw, 10);
    const voltageVal = voltageRaw === '' ? null : parseFloat(voltageRaw);
    return {
      name: nameI.value.trim().toUpperCase(),
      gpio_pin: parseInt(gpioI.value, 10),
      active_low: activeI.checked,
      description: descI.value.trim(),
      power_w: Number.isFinite(powerVal) ? powerVal : 0,
      quantity: Number.isFinite(quantityVal) ? quantityVal : 1,
      voltage_v: Number.isFinite(voltageVal) ? voltageVal : null,
      safe_default: false,
    };
  });
  fetch('/api/config', {
    method: 'POST',
    headers: adminHeaders(),
    body: JSON.stringify({ channels }),
  }).then(r => r.json()).then(() => poll());
}

window.initHardware = function() {
  poll();
  if (state.poller) clearInterval(state.poller);
  state.poller = setInterval(poll, 4000);
  const refreshBtn = document.getElementById('hardwareRefresh');
  if (refreshBtn) refreshBtn.onclick = poll;
  const addBtn = document.getElementById('addHardwareRow');
  if (addBtn) addBtn.onclick = addHardwareRow;
  const saveBtn = document.getElementById('saveHardware');
  if (saveBtn) saveBtn.onclick = saveHardware;
  fetchHardwareConfig();
};

function addHardwareRow() {
  const body = document.querySelector('#hardwareTable tbody');
  if (!body) return;
  const roleOptions = [
    { value: 'light', label: 'Light' },
    { value: 'fan', label: 'Fan' },
    { value: 'heater', label: 'Heater' },
    { value: 'pump', label: 'Pump' },
    { value: 'other', label: 'Other' },
  ];
  const roleSelect = `
    <select class="form-select form-select-sm" data-field="role">
      ${roleOptions.map(opt => `<option value="${opt.value}">${opt.label}</option>`).join('')}
    </select>
  `;
  const tr = document.createElement('tr');
  tr.innerHTML = `
    <td><input class="form-control form-control-sm" data-field="name" value=""></td>
    <td class="text-center"><input class="form-check-input" data-field="enabled" type="checkbox" checked></td>
    <td>${roleSelect}</td>
    <td><input class="form-control form-control-sm" data-field="gpio_pin" type="number" value=""></td>
    <td class="text-center"><input class="form-check-input" data-field="active_low" type="checkbox" checked></td>
    <td><input class="form-control form-control-sm" data-field="description" value=""></td>
    <td><input class="form-control form-control-sm" data-field="power_w" type="number" step="0.1" value=""></td>
    <td><input class="form-control form-control-sm" data-field="quantity" type="number" step="1" value="1"></td>
    <td class="small text-secondary">0.0 W</td>
    <td><input class="form-control form-control-sm" data-field="voltage_v" type="number" step="0.1" value=""></td>
    <td><input class="form-control form-control-sm" data-field="notes" value=""></td>`;
  body.appendChild(tr);
}

window.renderHardware = function(data) {
  const body = document.querySelector('#hardwareTable tbody');
  if (!body) return;
  body.innerHTML = '';
  const channels = Object.entries(data.actuator_state || {}).map(([name, info]) => ({
    name,
    role: info.role || 'other',
    gpio_pin: info.gpio_pin,
    active_low: info.active_low,
    description: info.description || name,
    power_w: info.power_w,
    quantity: info.quantity,
    voltage_v: info.voltage_v,
    notes: info.notes || '',
    enabled: info.enabled !== false,
  }));
  const roleOptions = [
    { value: 'light', label: 'Light' },
    { value: 'fan', label: 'Fan' },
    { value: 'heater', label: 'Heater' },
    { value: 'pump', label: 'Pump' },
    { value: 'other', label: 'Other' },
  ];
  channels.forEach(ch => {
    const tr = document.createElement('tr');
    const totalPower = (Number(ch.power_w || 0) * Number(ch.quantity || 1)) || 0;
    const roleSelect = `
      <select class="form-select form-select-sm" data-field="role">
        ${roleOptions.map(opt => `<option value="${opt.value}" ${opt.value === ch.role ? 'selected' : ''}>${opt.label}</option>`).join('')}
      </select>
    `;
    tr.innerHTML = `
      <td><input class="form-control form-control-sm" data-field="name" value="${ch.name}"></td>
      <td class="text-center"><input class="form-check-input" data-field="enabled" type="checkbox" ${ch.enabled ? 'checked' : ''}></td>
      <td>${roleSelect}</td>
      <td><input class="form-control form-control-sm" data-field="gpio_pin" type="number" value="${ch.gpio_pin}"></td>
      <td class="text-center"><input class="form-check-input" data-field="active_low" type="checkbox" ${ch.active_low ? 'checked' : ''}></td>
      <td><input class="form-control form-control-sm" data-field="description" value="${ch.description}"></td>
      <td><input class="form-control form-control-sm" data-field="power_w" type="number" step="0.1" value="${ch.power_w ?? ''}"></td>
      <td><input class="form-control form-control-sm" data-field="quantity" type="number" step="1" value="${ch.quantity ?? 1}"></td>
      <td class="small text-secondary">${totalPower.toFixed(1)} W</td>
      <td><input class="form-control form-control-sm" data-field="voltage_v" type="number" step="0.1" value="${ch.voltage_v ?? ''}"></td>
      <td><input class="form-control form-control-sm" data-field="notes" value="${ch.notes ?? ''}"></td>`;
    body.appendChild(tr);
  });
};

function saveHardware() {
  const rows = Array.from(document.querySelectorAll('#hardwareTable tbody tr'));
  const channels = rows.map(r => {
    const nameI = r.querySelector('[data-field="name"]');
    const roleI = r.querySelector('[data-field="role"]');
    const gpioI = r.querySelector('[data-field="gpio_pin"]');
    const activeI = r.querySelector('[data-field="active_low"]');
    const descI = r.querySelector('[data-field="description"]');
    const powerI = r.querySelector('[data-field="power_w"]');
    const quantityI = r.querySelector('[data-field="quantity"]');
    const voltageI = r.querySelector('[data-field="voltage_v"]');
    const notesI = r.querySelector('[data-field="notes"]');
    const enabledI = r.querySelector('[data-field="enabled"]');
    const powerRaw = powerI ? powerI.value.trim() : '';
    const quantityRaw = quantityI ? quantityI.value.trim() : '';
    const voltageRaw = voltageI ? voltageI.value.trim() : '';
    const powerVal = powerRaw === '' ? 0 : parseFloat(powerRaw);
    const quantityVal = quantityRaw === '' ? 1 : parseInt(quantityRaw, 10);
    const voltageVal = voltageRaw === '' ? null : parseFloat(voltageRaw);
    return {
      name: nameI.value.trim().toUpperCase(),
      role: roleI ? roleI.value.trim() : 'other',
      gpio_pin: parseInt(gpioI.value, 10),
      active_low: activeI.checked,
      description: descI.value.trim(),
      power_w: Number.isFinite(powerVal) ? powerVal : 0,
      quantity: Number.isFinite(quantityVal) ? quantityVal : 1,
      voltage_v: Number.isFinite(voltageVal) ? voltageVal : null,
      notes: notesI ? notesI.value.trim() : '',
      safe_default: false,
      enabled: enabledI ? enabledI.checked : true,
    };
  });
  fetch('/api/config', {
    method: 'POST',
    headers: adminHeaders(),
    body: JSON.stringify({ channels, sensors: collectSensorSettings() }),
  }).then(r => r.json()).then(() => poll());
}

function fetchHardwareConfig() {
  fetch('/api/config', { headers: adminHeaders() })
    .then(r => r.json())
    .then(data => {
      const sensors = data.sensors || {};
      const dht = document.getElementById('sensorDhtGpio');
      const bh = document.getElementById('sensorBhAddr');
      const ads = document.getElementById('sensorAdsAddr');
      const ds = document.getElementById('sensorDsEnabled');
      if (dht) dht.value = sensors.dht22_gpio ?? 17;
      if (bh) bh.value = sensors.bh1750_addr ?? '0x23';
      if (ads) ads.value = sensors.ads1115_addr ?? '0x48';
      if (ds) ds.value = sensors.ds18b20_enabled === false ? 'false' : 'true';
    })
    .catch(() => {});
}

function collectSensorSettings() {
  const dht = document.getElementById('sensorDhtGpio');
  const bh = document.getElementById('sensorBhAddr');
  const ads = document.getElementById('sensorAdsAddr');
  const ds = document.getElementById('sensorDsEnabled');
  return {
    dht22_gpio: dht ? parseInt(dht.value || '17', 10) : 17,
    bh1750_addr: bh ? bh.value.trim() || '0x23' : '0x23',
    ads1115_addr: ads ? ads.value.trim() || '0x48' : '0x48',
    ds18b20_enabled: ds ? ds.value === 'true' : true,
  };
}

function fmtMaybe(value, digits) {
  if (value === null || value === undefined) return '--';
  const num = Number(value);
  if (Number.isNaN(num)) return '--';
  const precision = digits == null ? 1 : digits;
  return num.toFixed(precision);
}

function sensorLogQuery() {
  const fromEl = document.getElementById('sensorLogFrom');
  const toEl = document.getElementById('sensorLogTo');
  const limitEl = document.getElementById('sensorLogLimit');
  const intervalEl = document.getElementById('sensorLogInterval');
  const orderEl = document.getElementById('sensorLogOrder');
  const from = ((fromEl && fromEl.value) || '').trim();
  const to = ((toEl && toEl.value) || '').trim();
  const limit = ((limitEl && limitEl.value) || '200').trim();
  const interval = ((intervalEl && intervalEl.value) || '').trim();
  const order = ((orderEl && orderEl.value) || 'desc').trim();
  const params = new URLSearchParams();
  if (from) params.set('from', from);
  if (to) params.set('to', to);
  if (limit) params.set('limit', limit);
  if (interval) params.set('interval', interval);
  if (order) params.set('order', order);
  return params;
}

function updateSensorLogDownloadLink() {
  const a = document.getElementById('sensorLogDownload');
  if (!a) return;
  const params = sensorLogQuery();
  params.set('format', 'csv');
  a.href = `/api/sensor_log?${params.toString()}`;
}

function renderSensorLogTable(rows) {
  const body = document.querySelector('#sensorLogTable tbody');
  const empty = document.getElementById('sensorLogEmpty');
  if (!body) return;
  body.innerHTML = '';
  if (!rows || rows.length === 0) {
    if (empty) empty.classList.remove('d-none');
    return;
  }
  if (empty) empty.classList.add('d-none');
  rows.forEach(row => {
    const tr = document.createElement('tr');
    const ts = row.ts;
    const tsLabel = ts ? new Date(Number(ts) * 1000).toLocaleString() : '--';
    tr.innerHTML = `
      <td class="text-nowrap">${tsLabel}</td>
      <td>${fmtMaybe(row.dht_temp, 1)}</td>
      <td>${fmtMaybe(row.dht_hum, 1)}</td>
      <td>${fmtMaybe(row.ds18_temp, 1)}</td>
      <td>${fmtMaybe(row.lux, 1)}</td>
      <td>${fmtMaybe(row.soil_ch0, 0)}</td>
      <td>${fmtMaybe(row.soil_ch1, 0)}</td>
      <td>${fmtMaybe(row.soil_ch2, 0)}</td>
      <td>${fmtMaybe(row.soil_ch3, 0)}</td>
    `;
    body.appendChild(tr);
  });
}

function refreshSensorLog() {
  updateSensorLogDownloadLink();
  const params = sensorLogQuery();
  fetch(`/api/sensor_log?${params.toString()}`)
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        const note = document.getElementById('sensorLogNote');
        if (note) note.textContent = `Hata: ${data.error}`;
        renderSensorLogTable([]);
        return;
      }
      renderSensorLogTable(data.rows || []);
      const updated = document.getElementById('sensorLogUpdated');
      if (updated) updated.textContent = `Güncelleme: ${new Date().toLocaleTimeString()}`;
      const note = document.getElementById('sensorLogNote');
      const count = data.rows ? data.rows.length : 0;
      const intervalSec = data.interval_sec || 0;
      const intervalLabel = intervalSec ? `${Math.round(intervalSec / 60)} dk ort.` : 'ham';
      if (note) note.textContent = `SQLite: ${count} satır · ${intervalLabel} · CSV: data/sensor_logs/`;
    })
    .catch(() => {});
}

function clearSensorLog() {
  const fromEl = document.getElementById('sensorLogFrom');
  const from = ((fromEl && fromEl.value) || '').trim();
  const scopeLabel = from ? `(${from} öncesi)` : '(tümü)';
  const ok = window.prompt(`Sensör log temizlenecek ${scopeLabel}. Onay için YES yaz:`);
  if (ok !== 'YES') return;
  const payload = { confirm: 'yes' };
  if (from) payload.before = from;
  fetch('/api/sensor_log/clear', {
    method: 'POST',
    headers: adminHeaders(),
    body: JSON.stringify(payload),
  }).then(r => r.json()).then(data => {
    const note = document.getElementById('sensorLogNote');
    if (note) note.textContent = data.ok ? `Silindi: ${data.deleted ?? 0}` : `Hata: ${data.error || 'unknown'}`;
    refreshSensorLog();
  });
}

window.initLogs = function() {
  poll();
  state.poller = setInterval(poll, 4000);
  const refreshBtn = document.getElementById('sensorLogRefresh');
  const clearBtn = document.getElementById('sensorLogClear');
  if (refreshBtn) refreshBtn.onclick = refreshSensorLog;
  if (clearBtn) clearBtn.onclick = clearSensorLog;
  const limit = document.getElementById('sensorLogLimit');
  const order = document.getElementById('sensorLogOrder');
  const from = document.getElementById('sensorLogFrom');
  const to = document.getElementById('sensorLogTo');
  const interval = document.getElementById('sensorLogInterval');
  [limit, order, from, to, interval].forEach(el => {
    if (!el) return;
    el.addEventListener('change', () => {
      updateSensorLogDownloadLink();
      refreshSensorLog();
    });
  });
  updateSensorLogDownloadLink();
  refreshSensorLog();
};

function renderLcdPreview(lines) {
  const wrap = document.getElementById('lcdPreview');
  if (!wrap) return;
  const safeLines = Array.isArray(lines) ? lines : [];
  wrap.innerHTML = safeLines.map(line => `<div class="lcd-preview-line">${line ?? ''}</div>`).join('');
}

function lcdTokenValues() {
  const status = state.status || {};
  const readings = status.sensor_readings || {};
  const dht = readings.dht22 || {};
  const ds = readings.ds18b20 || {};
  const lux = readings.bh1750 || {};
  const soil = readings.soil || {};
  const automation = status.automation || {};
  const calibration = automation.soil_calibration || {};
  const soilCal = calibration.ch0 || calibration['ch0'] || {};
  const fmtFloat = (value, fallback) => {
    const n = Number(value);
    if (Number.isFinite(n)) return n.toFixed(1);
    return fallback;
  };
  const fmtInt = (value, fallback) => {
    const n = Number(value);
    if (Number.isFinite(n)) return Math.round(n).toString();
    return fallback;
  };
  const soilRaw = soil.ch0;
  const dry = Number(soilCal.dry);
  const wet = Number(soilCal.wet);
  const raw = Number(soilRaw);
  let soilPct = null;
  if (Number.isFinite(dry) && Number.isFinite(wet) && dry !== wet && Number.isFinite(raw)) {
    soilPct = Math.round((dry - raw) / (dry - wet) * 100);
    soilPct = Math.min(100, Math.max(0, soilPct));
  }
  const now = new Date();
  return {
    temp: fmtFloat(dht.temperature, '--.-'),
    hum: fmtInt(dht.humidity, '--'),
    lux: fmtInt(lux.lux, '----'),
    soil_pct: soilPct == null ? '--' : soilPct.toString(),
    soil_raw: fmtInt(soilRaw, '----'),
    ds_temp: fmtFloat(ds.temperature, '--.-'),
    safe: status.safe_mode ? 'SAFE' : 'AKTIF',
    time: now.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' }),
  };
}

function applyLcdTemplateLine(line) {
  const ctx = lcdTokenValues();
  return (line || '').replace(/\{\s*([a-zA-Z0-9_]+)\s*\}/g, (_, key) => ctx[key.toLowerCase()] ?? '');
}

function lcdLinesFromInputs() {
  const lines = [];
  for (let i = 0; i < 4; i += 1) {
    const el = document.getElementById(`lcdLine${i}`);
    lines.push(el ? el.value : '');
  }
  return lines;
}

function updateLcdCounters(rawLines, resolvedLines) {
  const maxCols = Number(document.getElementById('lcdCols')?.value || 20);
  for (let i = 0; i < 4; i += 1) {
    const counter = document.getElementById(`lcdCount${i}`);
    if (!counter) continue;
    const rawLen = (rawLines[i] || '').length;
    const resolvedLen = (resolvedLines[i] || '').length;
    counter.textContent = `Şablon: ${rawLen} | Örnek: ${resolvedLen}/${maxCols}`;
  }
}

function refreshLcdPreviewFromInputs() {
  const modeEl = document.getElementById('lcdMode');
  const mode = modeEl ? modeEl.value : 'auto';
  const rawLines = lcdLinesFromInputs();
  let previewLines = rawLines;
  if (mode === 'template') {
    previewLines = rawLines.map(applyLcdTemplateLine);
  } else if (mode === 'auto') {
    previewLines = (state.status && state.status.lcd && state.status.lcd.lines) ? state.status.lcd.lines : previewLines;
  }
  renderLcdPreview(previewLines);
  updateLcdCounters(rawLines, previewLines);
}

function bindLcdInputs() {
  const inputs = document.querySelectorAll('.lcd-line');
  inputs.forEach((input) => {
    input.addEventListener('focus', () => { state.lcdActiveInput = input; });
    input.addEventListener('input', refreshLcdPreviewFromInputs);
  });
}

function fillLcdTemplatePreset() {
  const mode = document.getElementById('lcdMode');
  if (mode) mode.value = 'template';
  const defaults = [
    'Sic:{temp}C Nem:{hum}%',
    'Isik:{lux}lx Top:{soil_pct}%',
    'DS:{ds_temp}C Ham:{soil_raw}',
    'Durum:{safe} Saat:{time}',
  ];
  defaults.forEach((val, idx) => {
    const el = document.getElementById(`lcdLine${idx}`);
    if (el) el.value = val;
  });
  refreshLcdPreviewFromInputs();
}

function clearLcdLines() {
  for (let i = 0; i < 4; i += 1) {
    const el = document.getElementById(`lcdLine${i}`);
    if (el) el.value = '';
  }
  refreshLcdPreviewFromInputs();
}

function insertLcdToken(token) {
  const target = state.lcdActiveInput || document.getElementById('lcdLine0');
  if (!target) return;
  const start = target.selectionStart ?? target.value.length;
  const end = target.selectionEnd ?? target.value.length;
  target.value = `${target.value.slice(0, start)}${token}${target.value.slice(end)}`;
  target.focus();
  const pos = start + token.length;
  target.setSelectionRange(pos, pos);
  refreshLcdPreviewFromInputs();
}

window.initLcd = function() {
  poll();
  if (state.poller) clearInterval(state.poller);
  state.poller = setInterval(poll, 4000);
  const refreshBtn = document.getElementById('lcdRefresh');
  const saveBtn = document.getElementById('lcdSave');
  if (refreshBtn) refreshBtn.onclick = () => fetchLcdConfig();
  if (saveBtn) saveBtn.onclick = saveLcd;
  const templateBtn = document.getElementById('lcdTemplatePreset');
  if (templateBtn) templateBtn.onclick = fillLcdTemplatePreset;
  const clearBtn = document.getElementById('lcdClearLines');
  if (clearBtn) clearBtn.onclick = clearLcdLines;
  const tokenButtons = document.querySelectorAll('[data-lcd-token]');
  tokenButtons.forEach((btn) => {
    btn.addEventListener('click', () => insertLcdToken(btn.dataset.lcdToken));
  });
  const mode = document.getElementById('lcdMode');
  if (mode) mode.addEventListener('change', refreshLcdPreviewFromInputs);
  const cols = document.getElementById('lcdCols');
  if (cols) cols.addEventListener('input', refreshLcdPreviewFromInputs);
  bindLcdInputs();
  fetchLcdConfig();
};

window.renderLcd = function(data) {
  const lcd = data.lcd || {};
  state.lastLcdStatus = lcd;
  if (document.getElementById('lcdPreview')) {
    refreshLcdPreviewFromInputs();
  } else {
    renderLcdPreview(lcd.lines || []);
  }
};

function fetchLcdConfig() {
  fetch('/api/lcd')
    .then(r => r.json())
    .then(data => {
      const cfg = data.config || {};
      const lcd = data.lcd || {};
      const enabled = document.getElementById('lcdEnabled');
      const mode = document.getElementById('lcdMode');
      const addr = document.getElementById('lcdAddr');
      const port = document.getElementById('lcdPort');
      const cols = document.getElementById('lcdCols');
      const rows = document.getElementById('lcdRows');
      const expander = document.getElementById('lcdExpander');
      const charmap = document.getElementById('lcdCharmap');
      if (enabled) enabled.value = cfg.lcd_enabled === false ? 'false' : 'true';
      if (mode) mode.value = cfg.lcd_mode || 'auto';
      if (addr) addr.value = cfg.lcd_addr || '0x27';
      if (port) port.value = cfg.lcd_port ?? 1;
      if (cols) cols.value = cfg.lcd_cols ?? 20;
      if (rows) rows.value = cfg.lcd_rows ?? 4;
      if (expander) expander.value = cfg.lcd_expander || 'PCF8574';
      if (charmap) charmap.value = cfg.lcd_charmap || 'A00';
      const lines = cfg.lcd_lines || ["", "", "", ""];
      const l0 = document.getElementById('lcdLine0');
      const l1 = document.getElementById('lcdLine1');
      const l2 = document.getElementById('lcdLine2');
      const l3 = document.getElementById('lcdLine3');
      if (l0) l0.value = lines[0] || '';
      if (l1) l1.value = lines[1] || '';
      if (l2) l2.value = lines[2] || '';
      if (l3) l3.value = lines[3] || '';
      refreshLcdPreviewFromInputs();
    })
    .catch(() => {});
}

function saveLcd() {
  const enabled = document.getElementById('lcdEnabled');
  const mode = document.getElementById('lcdMode');
  const addr = document.getElementById('lcdAddr');
  const port = document.getElementById('lcdPort');
  const cols = document.getElementById('lcdCols');
  const rows = document.getElementById('lcdRows');
  const expander = document.getElementById('lcdExpander');
  const charmap = document.getElementById('lcdCharmap');
  const l0 = document.getElementById('lcdLine0');
  const l1 = document.getElementById('lcdLine1');
  const l2 = document.getElementById('lcdLine2');
  const l3 = document.getElementById('lcdLine3');
  const payload = {
    config: {
      lcd_enabled: enabled ? enabled.value === 'true' : true,
      lcd_mode: mode ? mode.value : 'auto',
      lcd_addr: addr ? addr.value.trim() : '0x27',
      lcd_port: port ? parseInt(port.value || '1', 10) : 1,
      lcd_cols: cols ? parseInt(cols.value || '20', 10) : 20,
      lcd_rows: rows ? parseInt(rows.value || '4', 10) : 4,
      lcd_expander: expander ? expander.value.trim() : 'PCF8574',
      lcd_charmap: charmap ? charmap.value.trim() : 'A00',
    },
    lines: [
      l0 ? l0.value : '',
      l1 ? l1.value : '',
      l2 ? l2.value : '',
      l3 ? l3.value : '',
    ],
  };
  fetch('/api/lcd', {
    method: 'POST',
    headers: adminHeaders(),
    body: JSON.stringify(payload),
  }).then(r => r.json()).then(() => fetchLcdConfig());
}

window.addEventListener('beforeunload', () => {
  if (state.poller) clearInterval(state.poller);
  if (state.historyTimer) clearInterval(state.historyTimer);
  if (state.eventsTimer) clearInterval(state.eventsTimer);
});
