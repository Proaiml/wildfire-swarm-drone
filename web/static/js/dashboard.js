"use strict";
const $ = (id) => document.getElementById(id);
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
let state = null,
  selected = null,
  lastMessage = 0,
  tool = null,
  points = [],
  draft = null;
let map,
  aoi,
  base,
  zoneKey = "",
  incidentKey = "",
  fleetKey = "",
  sectorsKey = "",
  firstState = true;
const markers = new Map(),
  tracks = new Map(),
  incidentMarkers = new Map(),
  sectorLayers = new Map();
let zonesLayer, toastTimer, coverageLayer, coverageKey = "";
const controlNames = {
  observe: "GÖZLEM",
  ready: "HUB KONTROLÜNDE · hazır",
  takeoff: "HUB KONTROLÜNDE · kalkış",
  mission: "HUB KONTROLÜNDE · görevde",
  hold: "YERİNDE TUTULUYOR",
  rtl: "EVE DÖNÜŞ (RTL)",
  landing: "İNİŞ",
  pilot_override: "PİLOT DEVRALDI",
  lost: "BAĞLANTI KOPTU · otopilot failsafe",
};
const colors = [
  "#61d6cb",
  "#86b7f3",
  "#caabfa",
  "#e8c278",
  "#ee9da9",
  "#93c5a0",
];
const roles = {
  search: "Şerit tarama",
  revisit: "Yeniden ziyaret (en eski alan)",
  ember: "Kıvılcım bölgesi devriyesi",
  inspect: "Kanıt inceleme",
  blocked: "Rota engelli",
  standby: "Beklemede",
  observer: "Telemetri gözlemi",
  pilot_advisory: "Pilot rehberliği",
};
const statusNames = {
  candidate: "ŞÜPHELİ",
  confirmed: "OPERATÖR TEYİDİ",
  dismissed: "REDDEDİLDİ",
  resolved: "TAMAMLANDI",
};
function toast(message, error = false) {
  $("toast").textContent = message;
  $("toast").className = error ? "error" : "";
  $("toast").hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => ($("toast").hidden = true), 6000);
}
async function api(path, body, method = "POST") {
  const response = await fetch(path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await response.json();
  if (!response.ok) {
    let detail = data.detail;
    throw new Error(
      Array.isArray(detail)
        ? detail.map((x) => `${x.loc.slice(1).join(".")}: ${x.msg}`).join("; ")
        : detail || `HTTP ${response.status}`,
    );
  }
  return data;
}
function action(fn) {
  return async (event) => {
    try {
      await fn(event);
    } catch (error) {
      toast(error.message, true);
    }
  };
}
function selectDrone(id) {
  selected = id;
  fleetKey = "";
  if (!id) {
    $("video").removeAttribute("src");
    return;
  }
  $("camera-id").textContent = id;
  $("video").src = `/api/video_feed/${encodeURIComponent(id)}`;
  if (state) renderFleet();
}
function initMap() {
  if (typeof L === "undefined") {
    $("map").textContent = "Harita kütüphanesi yüklenemedi. Sayfayı yenileyin.";
    return;
  }
  map = L.map("map", { zoomControl: false }).setView([36.885, 30.71], 14);
  const osm = L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    { maxZoom: 19, attribution: "© OpenStreetMap contributors" },
  );
  const satellite = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    {
      maxZoom: 19,
      attribution: "Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics",
    },
  );
  osm.addTo(map);
  L.control
    .layers({ "Sokak haritası": osm, "Uydu görüntüsü": satellite }, null, {
      position: "topright",
    })
    .addTo(map);
  L.control.zoom({ position: "bottomright" }).addTo(map);
  L.control.scale({ imperial: false, position: "bottomleft" }).addTo(map);
  osm.on("tileerror", () => {
    $("last-update").textContent =
      "Altlık haritası çevrimdışı; telemetri katmanı kullanılabilir";
  });
  zonesLayer = L.layerGroup().addTo(map);
  map.on("click", action(onMapClick));
  new ResizeObserver(() => map.invalidateSize()).observe($("map"));
}
function renderFleet() {
  const ids = Object.keys(state.drones);
  $("fleet-count").textContent = ids.length;
  const key = JSON.stringify([state.drones, selected]);
  if (key === fleetKey) return;
  fleetKey = key;
  $("fleet").innerHTML =
    ids
      .map((id, i) => {
        const d = state.drones[id];
        const stale =
          d.type !== "SIMULATED" &&
          (d.telemetry_age_s === null || d.telemetry_age_s > 3);
        const ap = d.autopilot;
        let autopilotHtml = "";
        if (ap) {
          const badgeClass = ap.control_enabled ? "" : ["pilot_override", "lost", "rtl", "landing"].includes(ap.control_state) ? "warn" : "off";
          autopilotHtml = `<div class="autopilot-line"><span class="control-badge ${badgeClass}">${controlNames[ap.control_state] || esc(ap.control_state)}</span> ${esc(ap.autopilot)} · sistem ${esc(ap.system_id)} · mod ${esc(ap.flight_mode)} · GPS fix ${ap.gps_fix} / ${ap.gps_sats} uydu</div>`;
          if (d.preflight)
            autopilotHtml += `<ul class="preflight">${d.preflight.map((c) => `<li class="${c.ok ? "ok" : "bad"}"><span>${esc(c.label)}</span><small>${esc(c.detail)}</small></li>`).join("")}</ul>`;
          if (ap.messages && ap.messages.length)
            autopilotHtml += `<div class="autopilot-line">Otopilot: ${esc(ap.messages.at(-1))}</div>`;
        }
        const physical = d.type === "MAVLINK";
        const controlButton = physical
          ? ap && ap.control_enabled
            ? `<button data-control="${esc(id)}" data-enable="0" title="Hub komut göndermeyi keser; araç yerinde tutulur">Kontrolü bırak</button>`
            : `<button data-control="${esc(id)}" data-enable="1" title="Uçuş öncesi kontroller geçerse hub bu drone’u sürüye katar">Hub kontrolüne al</button>`
          : "";
        const safety = d.control_enabled || physical
          ? `<button data-rtl="${esc(id)}" title="Kalkış noktasına dön (RTL)">RTL</button> <button data-land="${esc(id)}" title="Olduğu yere in">İn</button>`
          : "";
        return `<article class="drone-card ${selected === id ? "selected" : ""}"><div class="drone-title"><button data-select="${esc(id)}">${esc(id)}</button><span class="type-label">${d.type === "SIMULATED" ? "SİMÜLASYON" : d.type === "VOLUNTEER" ? "GÖNÜLLÜ" : "OTOPİLOT"}</span></div><div class="telemetry-grid"><div><small>İRTİFA</small><strong>${d.alt.toFixed(0)} m</strong></div><div><small>HIZ</small><strong>${d.speed.toFixed(1)} m/s</strong></div><div><small>BATARYA</small><strong style="color:${d.battery <= 20 ? "var(--red)" : "inherit"}">%${d.battery.toFixed(0)}</strong></div></div>${autopilotHtml}<div class="drone-bottom"><span>${stale ? "Telemetri bekleniyor" : d.safety_hold ? "EMNİYET BEKLEMESİ" : d.mode === "RTL" ? "Üsse dönüş" : d.mode === "LANDING" ? "İniş" : d.mode === "TAKEOFF" ? "Kalkış" : roles[d.role] || esc(d.mode)}</span><span>${controlButton} ${safety} <button data-remove="${esc(id)}" aria-label="${esc(id)} filodan çıkar">×</button></span></div></article>`;
      })
      .join("") || '<div class="empty">Filoya bir drone ekleyin.</div>';
}
function renderMap() {
  if (!map) return;
  const ids = Object.keys(state.drones);
  for (const [id, m] of markers) {
    if (!ids.includes(id)) {
      map.removeLayer(m);
      markers.delete(id);
      if (tracks.has(id)) {
        map.removeLayer(tracks.get(id).layer);
        tracks.delete(id);
      }
    }
  }
  ids.forEach((id, i) => {
    const d = state.drones[id],
      position = [d.lat, d.lon],
      color = colors[i % colors.length];
    if (!markers.has(id)) {
      const icon = L.divIcon({
        className: "drone-map-icon",
        html: `<span class="drone-glyph" style="background:${color}">↑</span>`,
        iconSize: [26, 26],
        iconAnchor: [13, 13],
      });
      const marker = L.marker(position, { icon })
        .addTo(map)
        .bindTooltip(esc(id), { direction: "top", offset: [0, -12] });
      marker.on("click", () => selectDrone(id));
      markers.set(id, marker);
      tracks.set(id, {
        points: [],
        layer: L.polyline([], { color, weight: 2, opacity: 0.65 }).addTo(map),
      });
    }
    const marker = markers.get(id);
    marker.setLatLng(position);
    const glyph = marker.getElement()?.querySelector(".drone-glyph");
    if (glyph) glyph.style.transform = `rotate(${d.heading}deg)`;
    const track = tracks.get(id),
      last = track.points.at(-1);
    if (last && map.distance(last, position) > 200) track.points = [];
    if (!last || map.distance(last, position) > 1) {
      track.points.push(position);
      if (track.points.length > 300) track.points.shift();
      track.layer.setLatLngs(track.points);
    }
  });
  const b = state.aoi_bounds;
  if (b) {
    const bounds = [
      [b.min_lat, b.min_lon],
      [b.max_lat, b.max_lon],
    ];
    if (!aoi)
      aoi = L.rectangle(bounds, {
        color: "#67d8d0",
        weight: 2,
        dashArray: "6 5",
        fillOpacity: 0.02,
      }).addTo(map);
    else aoi.setBounds(bounds);
    if (firstState) {
      map.fitBounds(bounds, { padding: [30, 30] });
      firstState = false;
    }
  }
  const pos = [state.base_station.lat, state.base_station.lon];
  if (!base)
    base = L.circleMarker(pos, {
      radius: 7,
      color: "#fff",
      fillColor: "#152f39",
      fillOpacity: 1,
      weight: 2,
    })
      .addTo(map)
      .bindTooltip("Operasyon üssü");
  else base.setLatLng(pos);
  const newSectorKey = JSON.stringify([
    ids.map((id) => [id, state.drones[id].sector]),
    $("sectors-toggle").checked,
  ]);
  if (newSectorKey !== sectorsKey) {
    sectorsKey = newSectorKey;
    for (const layer of sectorLayers.values()) map.removeLayer(layer);
    sectorLayers.clear();
    if ($("sectors-toggle").checked)
      ids.forEach((id, i) => {
        const d = state.drones[id];
        if (d.sector)
          sectorLayers.set(
            id,
            L.rectangle(d.sector, {
              color: colors[i % colors.length],
              weight: 1,
              dashArray: "3 6",
              fillOpacity: 0.025,
              interactive: false,
            }).addTo(map),
          );
      });
  }
  renderCoverage();
  const newZoneKey = JSON.stringify(state.geofence_zones);
  if (newZoneKey !== zoneKey) {
    zoneKey = newZoneKey;
    zonesLayer.clearLayers();
    L.geoJSON(state.geofence_zones, {
      style: (f) => ({
        color: f.properties.zone_type === "water_body" ? "#83b4eb" : "#ed8b86",
        weight: 2,
        fillOpacity: 0.18,
      }),
      onEachFeature: (f, l) => l.bindTooltip(esc(f.properties.name)),
    }).addTo(zonesLayer);
    const zones = state.geofence_zones.features;
    $("zone-count").textContent = zones.length;
    $("zones").innerHTML =
      zones
        .map(
          (z) =>
            `<div class="zone-row"><span>${esc(z.properties.name)}</span><button data-zone="${esc(z.properties.id)}">Aramaya aç</button></div>`,
        )
        .join("") || "Kapalı alan yok.";
  }
}
function renderCoverage() {
  const cov = state.coverage;
  const show = $("coverage-toggle").checked && cov;
  const key = show ? JSON.stringify([cov.age, cov.bounds]) : "off";
  if (key === coverageKey) return;
  coverageKey = key;
  if (coverageLayer) {
    map.removeLayer(coverageLayer);
    coverageLayer = null;
  }
  if (!show) return;
  const canvas = document.createElement("canvas");
  canvas.width = cov.cols;
  canvas.height = cov.rows;
  const ctx = canvas.getContext("2d");
  const img = ctx.createImageData(cov.cols, cov.rows);
  for (let r = 0; r < cov.rows; r++)
    for (let c = 0; c < cov.cols; c++) {
      const age = cov.age[r * cov.cols + c];
      const i = ((cov.rows - 1 - r) * cov.cols + c) * 4;      // satır 0 = güney
      img.data[i] = 245;
      img.data[i + 1] = 158;
      img.data[i + 2] = 60;
      img.data[i + 3] = Math.round(110 * age);               // az önce görülen şeffaf, uzun süredir görülmeyen turuncu
    }
  ctx.putImageData(img, 0, 0);
  const b = cov.bounds;
  coverageLayer = L.imageOverlay(canvas.toDataURL(), [[b.min_lat, b.min_lon], [b.max_lat, b.max_lon]], {
    opacity: 0.8, interactive: false,
  }).addTo(map);
  coverageLayer.getElement() && (coverageLayer.getElement().style.imageRendering = "pixelated");
}
function renderIncidents() {
  const incidents = state.fire_clusters;
  const key = JSON.stringify(incidents);
  if (key === incidentKey) return;
  incidentKey = key;
  $("incident-count").textContent = incidents.length;
  $("incidents").innerHTML =
    incidents
      .map(
        (c) =>
          `<article class="incident"><strong>${c.kind === "sar" ? "Kişi / yardım ihbarı" : "Yangın / duman"} · ${esc(c.id)}</strong><p>${statusNames[c.status] || "ŞÜPHELİ"} · %${(c.confidence * 100).toFixed(0)}</p><p>${c.lat.toFixed(5)}, ${c.lon.toFixed(5)}<br>Kaynak: ${c.source === "simulation" ? "SİMÜLASYON" : c.source === "operator_report" ? "Operatör ihbarı" : "Kamera tahmini"}</p><div class="incident-actions">${c.status === "candidate" ? `<button data-incident="${esc(c.id)}" data-status="confirmed">Teyit et</button><button data-incident="${esc(c.id)}" data-status="dismissed">Reddet</button>` : ""}${c.status === "confirmed" ? `<button data-incident="${esc(c.id)}" data-status="resolved">Tamamlandı</button>` : ""}<button data-focus="${c.lat},${c.lon}">Konuma git</button><button data-close-area="${c.lat},${c.lon}">Alanı kapat</button></div></article>`,
      )
      .join("") ||
    '<div class="empty"><b>Henüz bir olay yok.</b>Drone gözlemleri veya operatör ihbarları burada görünür. Tatbikat hedefi keşfedilene kadar gizlidir.</div>';
  if (!map) return;
  for (const marker of incidentMarkers.values()) map.removeLayer(marker);
  incidentMarkers.clear();
  for (const c of incidents) {
    if (["dismissed", "resolved"].includes(c.status)) continue;
    incidentMarkers.set(
      c.id,
      L.circleMarker([c.lat, c.lon], {
        radius: 9,
        color: c.verified ? "#f28d88" : "#efb66a",
        fillOpacity: 0.65,
      })
        .addTo(map)
        .bindTooltip(
          esc(
            `${c.kind === "sar" ? "SAR" : "Yangın"} · ${statusNames[c.status]}`,
          ),
        ),
    );
  }
}
function render(next) {
  state = next;
  $("social-state").textContent = state.gbest.found_by && state.gbest.fitness > 0 ? `PSO ortak gözlem: ${state.gbest.found_by} · skor ${state.gbest.fitness.toFixed(2)}. Yakın drone’lar inceler; diğerleri taramayı sürdürür.` : "PSO: geçerli ortak yangın gözlemi yok; sektör keşfi sürüyor.";
  lastMessage = Date.now();
  $("connection").textContent = "● Telemetri bağlı";
  $("connection").className = "connection";
  $("mission-kind").value = state.mission_kind;
  $("mission-kind").disabled = state.is_mission_active;
  $("start").disabled = state.is_mission_active;
  $("pause").disabled = !state.is_mission_active;
  $("mission-status").textContent = state.is_mission_active
    ? "GÖREV AKTİF"
    : "BEKLEMEDE";
  $("mission-time").textContent =
    `${String(Math.floor(state.mission_elapsed_seconds / 60)).padStart(2, "0")}:${String(state.mission_elapsed_seconds % 60).padStart(2, "0")}`;
  $("base-name").textContent = state.base_station.name;
  const w = state.wind;
  const names = ["K", "KD", "D", "GD", "G", "GB", "B", "KB"];
  const dirName = (deg) => names[Math.round(((deg % 360) + 360) % 360 / 45) % 8];
  $("wind-status").textContent = w.speed_ms >= 1
    ? `Şu an: ${w.speed_ms.toFixed(1)} m/s, ${dirName(w.direction_deg)} yönünden esiyor → kıvılcımlar ${dirName(w.direction_deg + 180)} yönüne taşınır (artçı yangın önceliği orada).`
    : "Şu an: rüzgâr yok / girilmedi (artçı önceliği yalnızca yangın çevresinde).";
  if (document.activeElement?.form !== $("wind-form")) {
    $("wind-form").elements.speed.value = w.speed_ms;
    $("wind-form").elements.direction.value = Math.round(w.direction_deg);
  }
  $("last-update").textContent =
    `Son telemetri ${new Date().toLocaleTimeString("tr-TR")}`;
  $("model-note").textContent =
    state.mission_kind === "sar"
      ? "SAR: sentetik sensör + operatör ihbarı. Gerçek insan algılama modeli bağlı değil."
      : state.readiness.fire_model_loaded
        ? "Yangın modeli yüklü. Sentetik kamera, saha başarımının kanıtı değildir."
        : "Yangın modeli yüklenemedi. Kamera tespiti kullanılamıyor.";
  const controlled = Object.values(state.drones).filter((x) => x.type === "MAVLINK" && x.control_enabled).length;
  const autopilots = Object.values(state.drones).filter((x) => x.type === "MAVLINK").length;
  $("environment").textContent = controlled
    ? `OTOPİLOT KONTROLÜ · ${controlled} ARAÇ`
    : autopilots ? "SİMÜLASYON + OTOPİLOT GÖZLEMİ" : "SİMÜLASYON + PİLOT DESTEĞİ";
  $("readiness").textContent = state.readiness.control_error
    ? `Kontrol uyarısı: ${state.readiness.control_error}`
    : controlled
      ? `${controlled} otopilot hub kontrolünde (ArduPilot; SITL ile doğrulandı, saha kabulü operatörün sorumluluğunda) • Kapsama: %${Math.round(100 * (state.coverage?.seen_ratio || 0))}`
      : `Simülasyon + otopilot gözlemi • Gönüllü katılım: pilot rehberliği • Kapsama: %${Math.round(100 * (state.coverage?.seen_ratio || 0))}`;
  if (!selected || !state.drones[selected])
    selectDrone(Object.keys(state.drones)[0] || null);
  const d = state.drones[selected];
  if (d) {
    $("camera-label").textContent =
      d.type === "SIMULATED" ? "SENTETİK KAMERA" : d.type === "MAVLINK" ? "OTOPİLOT KAMERASI" : "HARİCİ KAMERA";
    $("camera-status").textContent =
      `${d.alt.toFixed(1)} m · ${d.speed.toFixed(1)} m/s · skor ${d.current_score.toFixed(2)}`;
  }
  renderFleet();
  renderMap();
  renderIncidents();
}
function connect() {
  const ws = new WebSocket(
    `${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}/ws/telemetry`,
  );
  ws.onmessage = (e) => {
    try {
      render(JSON.parse(e.data));
    } catch (error) {
      console.error(error);
    }
  };
  ws.onclose = () => {
    $("connection").textContent = "● Bağlantı kesildi";
    $("connection").className = "connection offline";
    setTimeout(connect, 2000);
  };
}
function cancelDraw() {
  tool = null;
  points = [];
  if (draft) {
    map.removeLayer(draft);
    draft = null;
  }
  $("draw-help").hidden = true;
  document
    .querySelectorAll("[data-tool]")
    .forEach((b) => b.classList.remove("active"));
}
function beginDraw(kind) {
  cancelDraw();
  tool = kind;
  $("draw-help").hidden = false;
  $("finish-draw").hidden = ["aoi", "report", "scenario"].includes(kind);
  $("draw-text").textContent =
    kind === "aoi"
      ? "Alan için iki karşı köşeye tıklayın."
      : kind === "report"
        ? "İhbar konumuna tıklayın. Teyit ayrıca yapılır."
        : kind === "scenario"
          ? "Gizli tatbikat hedefi için haritaya tıklayın."
          : "En az 3 köşe seçin; sonra Alanı tamamla düğmesine basın.";
  document.querySelector(`[data-tool="${kind}"]`).classList.add("active");
}
async function onMapClick(event) {
  if (!tool) return;
  const { lat, lng: lon } = event.latlng;
  if (["report", "scenario"].includes(tool)) {
    await api(
      tool === "report"
        ? "/api/incidents/report"
        : "/api/mission/scenario/target",
      { lat, lon, intensity: 0.95, ...(tool === "scenario" ? {delay_seconds: Number($("scenario-delay").value)} : {}) },
    );
    toast(
      tool === "report"
        ? "İhbar kaydedildi; operatör teyidi bekliyor."
        : "Tatbikat hedefi eklendi. Drone tarafından keşfedilmesi gerekiyor.",
    );
    cancelDraw();
    return;
  }
  points.push([lat, lon]);
  if (draft) draft.setLatLngs(points);
  else
    draft = L.polyline(points, { color: "#fff", dashArray: "4 4" }).addTo(map);
  if (tool === "aoi" && points.length === 2) {
    await api("/api/mission/set_aoi", {
      min_lat: Math.min(points[0][0], lat),
      max_lat: Math.max(points[0][0], lat),
      min_lon: Math.min(points[0][1], lon),
      max_lon: Math.max(points[0][1], lon),
    });
    cancelDraw();
    toast("Arama alanı güncellendi; sektörler yeniden paylaşılacak.");
  }
}
async function finishDraw() {
  if (points.length < 3) throw new Error("En az 3 köşe seçin.");
  await api("/api/geofence/add", {
    name: tool === "water_body" ? "Arama dışı alan" : "Uçuşa yasak alan",
    zone_type: tool,
    coordinates: points,
  });
  cancelDraw();
  toast("Alan kapatıldı.");
}
function formNumbers(form, names) {
  return Object.fromEntries(
    names.map((n) => [n, Number(form.elements[n].value)]),
  );
}
initMap();
connect();
setInterval(() => {
  if (Date.now() - lastMessage > 4000) {
    $("connection").textContent = "● Telemetri güncel değil";
    $("connection").className = "connection offline";
    $("start").disabled = true;
    $("mission-kind").disabled = true;
  }
}, 1000);
$("start").onclick = action(async () => {
  await api("/api/mission/start");
  toast("Görev başladı: simülasyon ve hub kontrolündeki otopilotlar kalkıyor.");
});
$("pause").onclick = action(async () => {
  await api("/api/mission/pause");
  toast("Görev duraklatıldı. RTL ve iniş devam eder.");
});
$("rtl").onclick = action(async () => {
  if (
    confirm(
      "Hub kontrolündeki tüm drone'lar üsse dönsün mü (RTL)? Gönüllü pilotlar kendi dönüşünü yönetir.",
    )
  ) {
    await api("/api/mission/rtl");
    toast("Hub kontrolündeki filoya RTL verildi.");
  }
});
$("mission-kind").onchange = action(async (e) => {
  await api("/api/mission/kind", { kind: e.target.value });
  incidentKey = "";
  toast("Görev türü değişti; önceki olay listesi temizlendi.");
});
$("fit-map").onclick = () => {
  if (aoi) map.fitBounds(aoi.getBounds(), { padding: [25, 25] });
};
$("sectors-toggle").onchange = () => state && renderMap();
$("coverage-toggle").onchange = () => state && renderMap();
$("wind-form").onsubmit = action(async (e) => {
  e.preventDefault();
  const f = e.target;
  await api("/api/mission/set_wind", { speed_ms: Number(f.elements.speed.value), direction_deg: Number(f.elements.direction.value) });
  toast("Rüzgâr güncellendi.");
});
document
  .querySelectorAll("[data-tool]")
  .forEach((b) => (b.onclick = () => beginDraw(b.dataset.tool)));
$("finish-draw").onclick = action(finishDraw);
$("cancel-draw").onclick = cancelDraw;
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") cancelDraw();
});
$("fleet").onclick = action(async (e) => {
  const b = e.target.closest("button");
  if (!b) return;
  if (b.dataset.select) {
    selectDrone(b.dataset.select);
    return;
  }
  if (b.dataset.control) {
    const enable = b.dataset.enable === "1";
    if (enable && !confirm(`${b.dataset.control} hub kontrolüne alınsın mı? Görev aktifse drone kalkar ve sürüye katılır. Pilot kumandadan modu değiştirerek her an devralabilir.`)) return;
    b.disabled = true;
    const r = await api(`/api/drone/${encodeURIComponent(b.dataset.control)}/control`, { enable });
    toast(r.control_enabled ? `${b.dataset.control} hub kontrolünde.` : r.failed ? `Kontrol verilmedi: ${r.failed.join(", ")}` : `${b.dataset.control}: kontrol bırakıldı, araç yerinde tutuluyor.`, !r.control_enabled && !!r.failed);
    return;
  }
  if (b.dataset.rtl)
    await api(`/api/drone/${encodeURIComponent(b.dataset.rtl)}/rtl`);
  if (b.dataset.land)
    await api(`/api/drone/${encodeURIComponent(b.dataset.land)}/land`);
  const flyingAutopilot = b.dataset.remove && state.drones[b.dataset.remove]?.type === "MAVLINK" && state.drones[b.dataset.remove]?.is_in_air;
  if (
    b.dataset.remove &&
    confirm(flyingAutopilot
      ? `${b.dataset.remove} HAVADA. Filodan çıkarılırsa hub bağlantısı kesilir ve otopilot kendi bağlantı kaybı davranışını (genelde RTL) uygular. Devam edilsin mi?`
      : `${b.dataset.remove} filodan çıkarılsın mı?`)
  ) {
    await api(
      `/api/drone/${encodeURIComponent(b.dataset.remove)}`,
      undefined,
      "DELETE",
    );
  }
});
$("incidents").onclick = action(async (e) => {
  const b = e.target.closest("button");
  if (!b) return;
  if (b.dataset.incident) {
    await api(
      `/api/incidents/${encodeURIComponent(b.dataset.incident)}/status`,
      { status: b.dataset.status },
    );
    toast("Olay durumu güncellendi.");
  }
  if (b.dataset.focus) map.setView(b.dataset.focus.split(",").map(Number), 17);
  if (b.dataset.closeArea) {
    const [lat, lon] = b.dataset.closeArea.split(",").map(Number),
      d = 0.0006;
    await api("/api/geofence/add", {
      name:
        state.mission_kind === "sar"
          ? "Tamamlanmış arama alanı"
          : "İncelemesi tamamlanmış alan",
      zone_type: "fire_extinguished",
      coordinates: [
        [lat - d, lon - d],
        [lat - d, lon + d],
        [lat + d, lon + d],
        [lat + d, lon - d],
      ],
    });
    toast("Alan yeniden aramaya kapatıldı.");
  }
});
$("zones").onclick = action(async (e) => {
  const b = e.target.closest("[data-zone]");
  if (b)
    await api(
      `/api/geofence/${encodeURIComponent(b.dataset.zone)}`,
      undefined,
      "DELETE",
    );
});
$("add-drone").onclick = () => {
  if (!state) return;
  const f = $("drone-form");
  f.elements.lat.value = state.base_station.lat;
  f.elements.lon.value = state.base_station.lon;
  $("join-result").textContent = "";
  $("drone-dialog").showModal();
};
const droneTypeNotes = {
  simulated: "Simülasyon drone’u eğitim ve tatbikat içindir; gerçek drone’larla aynı planlayıcıyla uçar.",
  volunteer: "Gönüllü pilot gerçek telemetriyle katılır. Hub rota önerir; pilot kendi drone’unun kontrolünü korur.",
  mavlink: "Otopilotlu drone (ArduPilot / PX4) MAVLink ile bağlanır. Konum otopilottan okunur; enlem/boylam alanları kullanılmaz.",
};
$("drone-type").onchange = (e) => {
  $("mavlink-field").hidden = e.target.value !== "mavlink";
  $("drone-type-note").textContent = droneTypeNotes[e.target.value] || "";
};
$("drone-form").onsubmit = action(async (e) => {
  e.preventDefault();
  const f = e.target;
  const payload = {
    ...formNumbers(f, ["lat", "lon"]),
    drone_type: f.elements.drone_type.value,
    spawn_location: "custom",
    alt: 0,
    pilot_name: f.elements.pilot_name.value || null,
    capabilities: formNumbers(f, [
      "max_speed_ms",
      "max_altitude_m",
      "search_altitude_m",
      "camera_hfov_deg",
    ]),
  };
  if (f.elements.drone_id.value) payload.drone_id = f.elements.drone_id.value;
  if (payload.drone_type === "mavlink") {
    payload.connection_string = f.elements.connection_string.value;
    if (f.elements.target_system.value) payload.target_system = Number(f.elements.target_system.value);
    payload.camera_url = f.elements.camera_url.value || null;
    payload.synthetic_camera = f.elements.synthetic_camera.checked;
    $("join-result").textContent = "Otopilota bağlanılıyor (heartbeat bekleniyor, en fazla 10 s)...";
  }
  const d = await api("/api/swarm/add_drone", payload);
  toast(d.message || `${d.drone_id} filoya eklendi.`);
  $("drone-dialog").close();
});
$("base-settings").onclick = () => {
  if (!state) return;
  const f = $("base-form");
  for (const key of ["lat", "lon", "name"])
    f.elements[key].value = state.base_station[key];
  $("base-dialog").showModal();
};
$("base-form").onsubmit = action(async (e) => {
  e.preventDefault();
  const f = e.target;
  await api("/api/mission/base", {
    ...formNumbers(f, ["lat", "lon"]),
    name: f.elements.name.value,
    save_permanent: f.elements.save.checked,
    redeploy_drones: true,
    regenerate_fires: true,
  });
  firstState = true;
  $("base-dialog").close();
  toast("Simülasyon üssü güncellendi.");
});
document
  .querySelectorAll("[data-close]")
  .forEach((b) => (b.onclick = () => $(b.dataset.close).close()));
$("export").onclick = action(async () => {
  const data = await api("/api/mission/export_report", undefined, "GET");
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = `pyreswarm-${state.mission_kind}-${Date.now()}.json`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});


const truthLayer = L.layerGroup().addTo(map);
async function refreshScenarioTruth() {
  try {
    const response = await fetch("/api/mission/scenario/truth");
    if (!response.ok) return;
    const data = await response.json();
    truthLayer.clearLayers();
    const found = data.targets.filter((t) => t.delay_s !== null && t.delay_s !== undefined);
    const first = found.filter((t) => !t.aftershock).map((t) => t.delay_s);
    const after = found.filter((t) => t.aftershock).map((t) => t.delay_s);
    $("scenario-status").textContent = `Görev saati ${Math.floor(data.simulation_seconds)} s • ${found.length}/${data.targets.length} hedef bulundu` +
      (first.length ? ` • ilk yangın ${Math.min(...first).toFixed(0)} s` : "") +
      (after.length ? ` • artçı yangın tutuşmadan ${Math.min(...after).toFixed(0)} s sonra` : "");
    $("drill-table").hidden = !data.targets.length;
    $("drill-table").querySelector("tbody").innerHTML = data.targets.map((t) => {
      const waiting = !t.active;
      const delay = t.delay_s === null || t.delay_s === undefined ? null : t.delay_s;
      return `<tr><td>${esc(t.id)}</td><td>${t.aftershock ? "artçı" : "ilk"}</td><td>${t.ignition_s.toFixed(0)} s</td>` +
        `<td>${waiting ? `${Math.ceil(t.ignition_s - data.simulation_seconds)} s sonra tutuşacak` : delay === null ? "aranıyor" : t.detected_s.toFixed(0) + " s"}</td>` +
        `<td class="${delay === null ? (waiting ? "" : "miss") : "fast"}">${delay === null ? "–" : delay.toFixed(0) + " s"}</td><td>${esc(t.detected_by || "")}</td></tr>`;
    }).join("");
    if (!$("truth-toggle").checked) return;
    for (const t of data.targets) L.circleMarker([t.lat,t.lon], {
      radius: 10, color: t.nearby_sensor_candidate ? "#67e6a5" : "#e6a4ff",
      fillOpacity: t.active ? .35 : .05, dashArray: "3 5"
    }).bindTooltip(`${t.id} • SADECE OPERATÖR • ${t.active ? "aktif" : "bekliyor"}`).addTo(truthLayer);
  } catch (_) { /* Connection status is handled by the telemetry watchdog. */ }
}
$("truth-toggle").addEventListener("change", refreshScenarioTruth);
setInterval(refreshScenarioTruth, 2000);
$("benchmark-results").addEventListener("click", async () => {
  try {
    const r = await fetch("/api/benchmarks/results");
    if (!r.ok) throw new Error("Sonuçlar okunamadı");
    const data = await r.json();
    $("benchmark-summary").textContent = data.status === "not_run" ? "Henüz tamamlanmış karşılaştırma yok." :
      `${data.status} • ${data.completed_runs} koşu. Sentetik sensör / fiziksel uçuş kanıtı değildir. ` +
      data.ranking.slice(0,5).map((v,i) => `${i+1}. ${v.algorithm}: %${(100*v.recall).toFixed(1)} keşif`).join(" | ");
  } catch(e) { toast(e.message); }
});
refreshScenarioTruth();
