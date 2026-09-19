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
let zonesLayer, toastTimer;
const colors = [
  "#61d6cb",
  "#86b7f3",
  "#caabfa",
  "#e8c278",
  "#ee9da9",
  "#93c5a0",
];
const roles = {
  search: "Sektör tarama",
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
        return `<article class="drone-card ${selected === id ? "selected" : ""}"><div class="drone-title"><button data-select="${esc(id)}">${esc(id)}</button><span class="type-label">${d.type === "SIMULATED" ? "SİMÜLASYON" : d.type === "VOLUNTEER" ? "GÖNÜLLÜ" : "MAVLINK"}</span></div><div class="telemetry-grid"><div><small>İRTİFA</small><strong>${d.alt.toFixed(0)} m</strong></div><div><small>HIZ</small><strong>${d.speed.toFixed(1)} m/s</strong></div><div><small>BATARYA</small><strong style="color:${d.battery <= 20 ? "var(--red)" : "inherit"}">%${d.battery.toFixed(0)}</strong></div></div><div class="drone-bottom"><span>${stale ? "Telemetri bekleniyor" : d.safety_hold ? "EMNİYET BEKLEMESİ" : d.mode === "RTL" ? "Üsse dönüş" : d.mode === "LANDING" ? "İniş" : roles[d.role] || esc(d.mode)}</span><span>${d.control_enabled ? `<button data-rtl="${esc(id)}" title="Simülasyon drone’unu üsse çağır">RTL</button> <button data-land="${esc(id)}" title="Simülasyon drone’unu indir">İn</button>` : ""} <button data-remove="${esc(id)}" aria-label="${esc(id)} filodan çıkar">×</button></span></div></article>`;
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
  $("last-update").textContent =
    `Son telemetri ${new Date().toLocaleTimeString("tr-TR")}`;
  $("model-note").textContent =
    state.mission_kind === "sar"
      ? "SAR: sentetik sensör + operatör ihbarı. Gerçek insan algılama modeli bağlı değil."
      : state.readiness.fire_model_loaded
        ? "Yangın modeli yüklü. Sentetik kamera, saha başarımının kanıtı değildir."
        : "Yangın modeli yüklenemedi. Kamera tespiti kullanılamıyor.";
  $("readiness").textContent = state.readiness.control_error
    ? `Kontrol uyarısı: ${state.readiness.control_error}`
    : "Fiziksel otonom uçuş doğrulanmadı • Gönüllü katılım: pilot rehberliği";
  if (!selected || !state.drones[selected])
    selectDrone(Object.keys(state.drones)[0] || null);
  const d = state.drones[selected];
  if (d) {
    $("camera-label").textContent =
      d.type === "SIMULATED" ? "SENTETİK KAMERA" : "HARİCİ KAMERA";
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
      { lat, lon, intensity: 0.95 },
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
  toast("Simülasyon ve uygun gönüllü rehberliği başladı.");
});
$("pause").onclick = action(async () => {
  await api("/api/mission/pause");
  toast("Görev duraklatıldı. RTL ve iniş devam eder.");
});
$("rtl").onclick = action(async () => {
  if (
    confirm(
      "Simülasyon filosu üsse dönsün mü? Gönüllü pilotlar kendi dönüşünü yönetir.",
    )
  ) {
    await api("/api/mission/rtl");
    toast("Simülasyon filosuna RTL verildi.");
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
  if (b.dataset.rtl)
    await api(`/api/drone/${encodeURIComponent(b.dataset.rtl)}/rtl`);
  if (b.dataset.land)
    await api(`/api/drone/${encodeURIComponent(b.dataset.land)}/land`);
  if (
    b.dataset.remove &&
    confirm(`${b.dataset.remove} filodan çıkarılsın mı?`)
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
$("drone-type").onchange = (e) =>
  ($("mavlink-field").hidden = e.target.value !== "mavlink");
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
  if (payload.drone_type === "mavlink")
    payload.connection_string = f.elements.connection_string.value;
  const d = await api("/api/swarm/add_drone", payload);
  toast(`${d.drone_id} filoya eklendi.`);
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
