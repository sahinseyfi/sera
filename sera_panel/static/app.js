const API_PREFIX = "/test/api";

function adminHeaders(includeJson) {
  const headers = {};
  const token = localStorage.getItem("adminToken");
  if (token) headers["X-Admin-Token"] = token;
  if (includeJson) headers["Content-Type"] = "application/json";
  return headers;
}

async function jget(path) {
  const r = await fetch(`${API_PREFIX}${path}`, { headers: adminHeaders(false) });
  return await r.json();
}
async function jpost(path, body) {
  const r = await fetch(`${API_PREFIX}${path}`, {
    method: "POST",
    headers: adminHeaders(true),
    body: JSON.stringify(body || {})
  });
  return await r.json();
}

let lastStatus = null;
let fullConfig = null;

function fmtTs(ts) {
  if (!ts) return "—";
  const d = new Date(ts * 1000);
  return d.toLocaleString();
}

function setText(id, txt) {
  const el = document.getElementById(id);
  if (el) el.textContent = txt;
}

function setHTML(id, html) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = html;
}

function renderSensors(s) {
  const bh = s.bh1750 || {};
  setText("luxVal", (bh.lux === null || bh.lux === undefined) ? "—" : `${bh.lux.toFixed(1)} lux`);
  setText("luxErr", bh.err ? `Hata: ${bh.err}` : "");

  const ads = s.ads1115 || {};
  const a0 = ads.a0, a1 = ads.a1, a2 = ads.a2, a3 = ads.a3;
  const adsTxt = [a0,a1,a2,a3].map((v,i)=> v==null ? `A${i}:—` : `A${i}:${v.toFixed(3)}V`).join(" | ");
  setText("adsVal", adsTxt);
  setText("adsErr", ads.err ? `Hata: ${ads.err}` : "");

  const ds = s.ds18b20 || {};
  if (ds.sensors && ds.sensors.length) {
    setText("dsVal", ds.sensors.map(x => `${x.id}: ${x.c}°C`).join(" • "));
  } else {
    setText("dsVal", "—");
  }
  setText("dsErr", ds.err ? `Hata: ${ds.err}` : "");

  const dht = s.dht22 || {};
  if (dht.temp != null && dht.hum != null) {
    setText("dhtVal", `${dht.temp.toFixed(1)}°C • ${dht.hum.toFixed(1)}%`);
  } else {
    setText("dhtVal", "—");
  }
  setText("dhtErr", dht.err ? `Hata: ${dht.err}` : "");
}

function relayRow(key, r) {
  const locked = (r.type === "pump" && r.locked);
  const st = r.state ? "ON" : "OFF";
  const cls = r.state ? "pill on" : "pill off";

  return `
    <div class="relay">
      <div class="relay-left">
        <div class="relay-name">${r.name}</div>
        <div class="small">GPIO${r.gpio} • ${r.type}${locked ? " • kilitli" : ""}</div>
      </div>

      <div class="relay-mid">
        <span class="${cls}">${st}</span>
      </div>

      <div class="relay-actions">
        <button class="btn" onclick="relayOff('${key}')">OFF</button>
        <button class="btn primary" onclick="relayOn('${key}')">ON</button>
        <button class="btn" onclick="relayPulse('${key}',2)">PULSE 2s</button>
        <button class="btn" onclick="relayPulse('${key}',5)">5s</button>
        <button class="btn" onclick="relayPulse('${key}',10)">10s</button>
      </div>
    </div>
  `;
}

async function relayOn(key) {
  const res = await jpost(`/relay/${key}`, {action:"on"});
  if (!res.ok) alert(res.error || "Hata");
}
async function relayOff(key) {
  const res = await jpost(`/relay/${key}`, {action:"off"});
  if (!res.ok) alert(res.error || "Hata");
}
async function relayPulse(key, sec) {
  const res = await jpost(`/relay/${key}`, {action:"pulse", sec});
  if (!res.ok) alert(res.error || "Hata");
}

function buildConfigForm(cfg) {
  const relays = cfg.relays || {};
  let html = "";
  for (const [key, r] of Object.entries(relays)) {
    html += `
      <div class="inline">
        <label>${r.name}</label>
        <input type="number" min="0" max="27" data-relaykey="${key}" value="${r.gpio}">
      </div>
    `;
  }
  setHTML("configForm", html);

  document.getElementById("cfgActiveLow").checked = !!cfg.active_low;
  document.getElementById("cfgDhtGpio").value = (cfg.sensors && cfg.sensors.dht22_gpio != null) ? cfg.sensors.dht22_gpio : 17;
  document.getElementById("cfgHeaterMax").value = (cfg.safety && cfg.safety.heater_max_on_sec != null) ? cfg.safety.heater_max_on_sec : 10;
  document.getElementById("cfgPumpMax").value = (cfg.safety && cfg.safety.pump_max_on_sec != null) ? cfg.safety.pump_max_on_sec : 3;
}

async function saveConfig() {
  const out = document.getElementById("saveCfgOut");
  out.textContent = "Kaydediliyor...";

  const inputs = document.querySelectorAll("#configForm input[data-relaykey]");
  const newCfg = JSON.parse(JSON.stringify(fullConfig));

  newCfg.active_low = document.getElementById("cfgActiveLow").checked;
  newCfg.sensors.dht22_gpio = parseInt(document.getElementById("cfgDhtGpio").value || "17", 10);
  newCfg.safety.heater_max_on_sec = parseInt(document.getElementById("cfgHeaterMax").value || "10", 10);
  newCfg.safety.pump_max_on_sec = parseInt(document.getElementById("cfgPumpMax").value || "3", 10);

  for (const inp of inputs) {
    const key = inp.getAttribute("data-relaykey");
    newCfg.relays[key].gpio = parseInt(inp.value, 10);
  }

  const j = await jpost("/config", newCfg);
  if (!j.ok) {
    out.textContent = `Hata: ${j.error || "unknown"}`;
    return;
  }
  out.textContent = "Kaydedildi. (runtime yeniden yüklendi)";
  fullConfig = newCfg;
}

async function refresh() {
  const st = await jget("/status");
  lastStatus = st;

  setText("backendOk", st.sensors && st.sensors.ok ? "OK" : "Hata var");
  setText("nowTs", fmtTs(st.time));
  setText("safeModeVal", st.safe_mode ? "ON" : "OFF");
  setText("activeLow", st.config && st.config.active_low ? "Evet" : "Hayır");

  // safety toggles
  const tm = document.getElementById("testMode");
  tm.checked = !!st.safety.test_mode;

  const pumpMax = (st.config.safety && st.config.safety.pump_max_on_sec != null) ? st.config.safety.pump_max_on_sec : "—";
  setText("pumpMax", pumpMax);

  const pumpUnlock = document.getElementById("pumpUnlock");
  pumpUnlock.checked = !!st.safety.pump_unlocked;

  // relays
  let html = "";
  for (const [key, r] of Object.entries(st.relays || {})) {
    html += relayRow(key, r);
  }
  setHTML("relayList", html);

  // sensors
  renderSensors(st.sensors || {});
}

async function init() {
  // fetch full config for form
  fullConfig = await jget("/config");
  buildConfigForm(fullConfig);

  document.getElementById("saveCfgBtn").addEventListener("click", saveConfig);

  document.getElementById("testMode").addEventListener("change", async (e) => {
    await jpost("/safety", {test_mode: e.target.checked});
  });

  document.getElementById("estopBtn").addEventListener("click", async () => {
    const want = !(lastStatus && lastStatus.safety && lastStatus.safety.estop);
    await jpost("/safety", {estop: want});
  });

  document.getElementById("allOffBtn").addEventListener("click", async () => {
    await jpost("/all-off", {});
  });

  document.getElementById("pumpUnlock").addEventListener("change", async (e) => {
    await jpost("/safety", {pump_unlocked: e.target.checked});
  });

  document.getElementById("i2cScanBtn").addEventListener("click", async () => {
    const res = await jpost("/i2c-scan", {});
    if (!res.ok) {
      setText("i2cScanOut", "Hata");
      return;
    }
    const r = res.result || {};
    if (r.err) {
      setText("i2cScanOut", `Hata: ${r.err}`);
    } else {
      setText("i2cScanOut", `Bulunan adresler: ${r.found.join(", ")}`);
    }
  });

  await refresh();
  setInterval(refresh, 1200);
}

window.relayOn = relayOn;
window.relayOff = relayOff;
window.relayPulse = relayPulse;

init();
