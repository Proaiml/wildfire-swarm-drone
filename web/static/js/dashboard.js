/**
 * PyreSwarm - Next-Gen Autonomous Wildfire Mission Control JavaScript
 * Gerçek zamanlı Leaflet harita, Google Maps hibrit katmanı, WebSocket telemetrisi,
 * dinamik kalıcı üs yönetimi, tıkla-konuşlandır drone ekleme, rüzgar pusulası ve saha araçları.
 */

let map;
let droneMarkers = {};
let fireMarkers = {};
let geofenceLayers = [];
let aoiLayer = null;
let baseMarker = null;
let currentSelectedDrone = "ALPHA-01";
let baseStation = {
    name: "Antalya Manavgat Orman Şefliği İleri Üssü",
    lat: 36.8850,
    lon: 30.7100
};
let alertedLowBatteryDrones = new Set();

// Çizim ve Etkileşim Modları
let interactionMode = null; // 'spawn_drone', 'add_fire', 'aoi', 'water_body', 'fire_extinguished', 'no_fly_zone'
let activeDrawPoints = [];
let activeDrawPolyline = null;
let contextMenuLatLng = null;

document.addEventListener("DOMContentLoaded", () => {
    initMap();
    initWebSocket();
    initControls();
    initBaseManagement();
    initAddDroneModal();
    initDispatchModal();
    initLocationSearch();
    initWindModal();
    initContextMenu();
    initVideoFeed();
    initMetricsCalculator();
});

/* 1. Harita ve Üs Kurulumu */
function initMap() {
    map = L.map("map", {
        center: [baseStation.lat, baseStation.lon],
        zoom: 14,
        zoomControl: false
    });

    L.control.zoom({ position: "bottomright" }).addTo(map);

    // Google Maps Katmanları
    const googleHybrid = L.tileLayer("https://mt{s}.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", {
        subdomains: ["0", "1", "2", "3"],
        maxZoom: 21,
        attribution: '&copy; Google Maps'
    });

    const googleSatellite = L.tileLayer("https://mt{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}", {
        subdomains: ["0", "1", "2", "3"],
        maxZoom: 21,
        attribution: '&copy; Google Maps'
    });

    const googleStreets = L.tileLayer("https://mt{s}.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", {
        subdomains: ["0", "1", "2", "3"],
        maxZoom: 21,
        attribution: '&copy; Google Maps'
    });

    const osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap'
    });

    googleHybrid.addTo(map);

    const baseMaps = {
        "Google Uydu (Hibrit)": googleHybrid,
        "Google Saf Uydu": googleSatellite,
        "Google Harita": googleStreets,
        "OpenStreetMap": osm
    };
    L.control.layers(baseMaps, null, { position: "topright" }).addTo(map);

    map.on("click", handleMapClick);
    map.on("contextmenu", handleMapContextMenu);

    setTimeout(() => { map.invalidateSize(); }, 200);
    window.addEventListener("resize", () => { map.invalidateSize(); });

    // Backend'den kalıcı kayıtlı üssü al ve haritayı oraya odakla
    fetchBaseStation();
}

/* 2. Özel Marker İkonları */
function createBaseIcon() {
    const html = `
        <div class="base-marker-container">
            <div class="base-radar-pulse"></div>
            <div class="base-shelter-icon" title="Ana Operasyon Üssü (Kalkış / RTL)">
                <i class="fa-solid fa-anchor"></i>
            </div>
        </div>
    `;
    return L.divIcon({
        className: "custom-base-icon",
        html: html,
        iconSize: [44, 44],
        iconAnchor: [22, 22]
    });
}

function createDroneIcon(heading, isArmed, score, isLowBattery) {
    let glowClass = "";
    if (isLowBattery) glowClass = "battery-critical";
    else if (score > 0.3) glowClass = "drone-glow-fire";

    const html = `
        <div class="drone-marker-container ${glowClass}">
            <div class="drone-heading-arrow" style="transform: rotate(${heading}deg);">
                <i class="fa-solid fa-plane-up"></i>
            </div>
            <div class="drone-pulse"></div>
        </div>
    `;
    return L.divIcon({
        className: "custom-drone-icon",
        html: html,
        iconSize: [36, 36],
        iconAnchor: [18, 18]
    });
}

function createFireIcon() {
    const html = `
        <div class="fire-marker-pulse">
            <i class="fa-solid fa-fire"></i>
        </div>
    `;
    return L.divIcon({
        className: "custom-fire-icon",
        html: html,
        iconSize: [32, 32],
        iconAnchor: [16, 16]
    });
}

/* 3. Kalıcı Üs Yönetimi & Harita Senkronizasyonu */
function fetchBaseStation() {
    fetch("/api/mission/base")
        .then(r => r.json())
        .then(data => {
            if (data && data.lat && data.lon) {
                baseStation = {
                    name: data.name || "Ana Operasyon Üssü",
                    lat: data.lat,
                    lon: data.lon
                };
                updateBaseMarker();
                map.panTo([baseStation.lat, baseStation.lon]);
                document.getElementById("text-base-name").innerText = baseStation.name;

                // Preset dropdown doldur
                const selectPreset = document.getElementById("select-base-preset");
                if (selectPreset && data.presets) {
                    selectPreset.innerHTML = '<option value="">-- Bölge Seçiniz (Örn: Antalya, Muğla, Çanakkale) --</option>';
                    data.presets.forEach((p, idx) => {
                        const opt = document.createElement("option");
                        opt.value = idx;
                        opt.innerText = `${p.name} (${p.lat.toFixed(4)}, ${p.lon.toFixed(4)})`;
                        opt.dataset.lat = p.lat;
                        opt.dataset.lon = p.lon;
                        opt.dataset.name = p.name;
                        selectPreset.appendChild(opt);
                    });
                }
            }
        })
        .catch(err => console.error("Üs konumu alınamadı:", err));
}

function updateBaseMarker() {
    if (!baseMarker) {
        baseMarker = L.marker([baseStation.lat, baseStation.lon], {
            icon: createBaseIcon(),
            draggable: true,
            zIndexOffset: 1000
        }).addTo(map);

        baseMarker.bindPopup(`
            <div style="font-family:'Inter', sans-serif;">
                <b style="color:#ffcc00;"><i class="fa-solid fa-anchor"></i> ${baseStation.name}</b><br>
                <span style="font-size:11px; color:#888;">GPS: ${baseStation.lat.toFixed(5)}, ${baseStation.lon.toFixed(5)}</span><br>
                <div style="margin-top:6px;">
                    <button class="btn btn-warning btn-sm" onclick="openBaseModal()" style="font-size:10px; padding:2px 8px;">Üs Ayarlarını Aç</button>
                </div>
            </div>
        `);

        baseMarker.on("dragend", (e) => {
            const pos = e.target.getLatLng();
            if (confirm(`Ana Operasyon Üssü bu yeni koordinata (${pos.lat.toFixed(5)}, ${pos.lng.toFixed(5)}) taşınsın mı?`)) {
                updateBaseStation(pos.lat, pos.lng, baseStation.name, true, true, true);
            } else {
                baseMarker.setLatLng([baseStation.lat, baseStation.lon]);
            }
        });
    } else {
        baseMarker.setLatLng([baseStation.lat, baseStation.lon]);
    }
}

function updateBaseStation(lat, lon, name, redeploy = true, savePermanent = true, regenFires = true) {
    fetch("/api/mission/base", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            name: name,
            lat: lat,
            lon: lon,
            redeploy_drones: redeploy,
            save_permanent: savePermanent,
            regenerate_fires: regenFires
        })
    })
    .then(r => r.json())
    .then(data => {
        baseStation.lat = lat;
        baseStation.lon = lon;
        baseStation.name = name;
        updateBaseMarker();
        map.flyTo([lat, lon], 14);
        document.getElementById("text-base-name").innerText = name;
        showToast(`Operasyon üssü taşındı: ${name}`, "success");
    })
    .catch(err => showToast("Üs güncellenirken hata oluştu: " + err, "danger"));
}

/* 4. WebSocket Telemetri Dinleyicisi */
function initWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/telemetry`;
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            updateDashboard(data);
        } catch (err) {
            console.error("Telemetri ayrıştırma hatası:", err);
        }
    };

    ws.onclose = () => {
        setTimeout(initWebSocket, 2000);
    };
}

/* 5. Arayüz ve Harita Güncellemesi */
function updateDashboard(state) {
    // Üst Bar Sayaçları
    document.getElementById("stat-drone-count").innerText = state.drones_count;
    document.getElementById("stat-gbest-score").innerText = state.gbest.fitness.toFixed(2);
    document.getElementById("stat-fire-count").innerText = state.fire_clusters ? state.fire_clusters.length : 0;

    // Üs Adı
    if (state.base_station && state.base_station.name) {
        document.getElementById("text-base-name").innerText = state.base_station.name;
    }

    // Rüzgar Göstergesi
    if (state.wind) {
        document.getElementById("wind-speed-text").innerText = `${state.wind.speed_ms.toFixed(1)} m/s`;
        document.getElementById("wind-arrow-icon").style.transform = `rotate(${state.wind.direction_deg}deg)`;
    }

    // Görev Durumu
    const modeBadge = document.getElementById("swarm-mode-badge");
    if (state.is_mission_active) {
        modeBadge.innerText = "DEVRİYEDE (PSO)";
        modeBadge.className = "badge";
        const mins = String(Math.floor(state.mission_elapsed_seconds / 60)).padStart(2, '0');
        const secs = String(state.mission_elapsed_seconds % 60).padStart(2, '0');
        document.getElementById("stat-mission-time").innerText = `${mins}:${secs}`;
    } else {
        modeBadge.innerText = "BEKLEMEDE";
        modeBadge.className = "badge badge-warning";
    }

    // Drone Tablosu ve Harita Marker'ları
    const tbody = document.getElementById("drone-table-body");
    const videoSelect = document.getElementById("video-drone-select");
    let tbodyHtml = "";

    const droneIds = Object.keys(state.drones);

    // Video select opsiyonlarını güncelle
    if (videoSelect.options.length !== droneIds.length) {
        const currentVal = videoSelect.value;
        videoSelect.innerHTML = "";
        droneIds.forEach(id => {
            const opt = document.createElement("option");
            opt.value = id;
            opt.innerText = id;
            videoSelect.appendChild(opt);
        });
        if (currentVal && droneIds.includes(currentVal)) {
            videoSelect.value = currentVal;
        } else if (droneIds.length > 0) {
            videoSelect.value = droneIds[0];
            currentSelectedDrone = droneIds[0];
        }
    }

    droneIds.forEach(id => {
        const d = state.drones[id];
        const isFire = d.current_score > 0.3;
        const scoreStyle = isFire ? "color: #ff5500; font-weight: bold;" : "";
        const isLow = d.battery <= 20 || d.is_low_battery;
        const battClass = isLow ? "battery-critical" : "";
        const battIcon = isLow ? '<i class="fa-solid fa-triangle-exclamation"></i> ' : '';

        // Düşük batarya sesli/görsel uyarı
        if (d.battery <= 15 && !alertedLowBatteryDrones.has(id)) {
            alertedLowBatteryDrones.add(id);
            showToast(`⚠️ [${id}] Bataryası %15 altına düştü! Otonom RTL ile üsse dönüyor.`, "danger", 6000);
        }

        tbodyHtml += `
            <tr style="cursor: pointer;">
                <td onclick="selectDrone('${d.drone_id}')"><strong>${d.drone_id}</strong></td>
                <td onclick="selectDrone('${d.drone_id}')"><span style="font-size:9px; color:#8b9bb4;">${d.type}</span></td>
                <td onclick="selectDrone('${d.drone_id}')">${d.alt.toFixed(1)}m</td>
                <td onclick="selectDrone('${d.drone_id}')">${d.speed.toFixed(1)}m/s</td>
                <td onclick="selectDrone('${d.drone_id}')" class="${battClass}">${battIcon}${d.battery.toFixed(0)}%</td>
                <td onclick="selectDrone('${d.drone_id}')" style="${scoreStyle}">${d.current_score > 0.1 ? d.current_score.toFixed(2) : d.pbest_score.toFixed(2)}</td>
                <td style="text-align:center; white-space:nowrap;">
                    <button class="btn-table-action action-rtl" onclick="droneRtl('${d.drone_id}')" title="Üsse Çağır (RTL)">🏠 RTL</button>
                    <button class="btn-table-action action-land" onclick="droneLand('${d.drone_id}')" title="Olduğu Yere İndir">🔻</button>
                    <button class="btn-table-action action-del" onclick="droneDelete('${d.drone_id}')" title="Filodan Çıkar">❌</button>
                </td>
            </tr>
        `;

        if (!droneMarkers[id]) {
            const m = L.marker([d.lat, d.lon], {
                icon: createDroneIcon(d.heading, d.is_armed, d.current_score, isLow)
            }).addTo(map);
            m.bindPopup(`
                <b>${d.drone_id}</b> (${d.type})<br>
                İrtifa: ${d.alt}m | Hız: ${d.speed}m/s<br>
                Batarya: %${d.battery.toFixed(0)} | Mod: ${d.mode}<br>
                <div style="margin-top:6px; display:flex; gap:4px;">
                    <button class="btn btn-warning btn-sm" onclick="droneRtl('${d.drone_id}')">RTL</button>
                    <button class="btn btn-outline btn-sm" onclick="selectDrone('${d.drone_id}')">Kamera</button>
                </div>
            `);
            droneMarkers[id] = m;
        } else {
            droneMarkers[id].setLatLng([d.lat, d.lon]);
            droneMarkers[id].setIcon(createDroneIcon(d.heading, d.is_armed, d.current_score, isLow));
        }
    });
    tbody.innerHTML = tbodyHtml;

    // Liderlik Kartı
    if (state.leaderboard && state.leaderboard.length > 0) {
        const top = state.leaderboard[0];
        document.getElementById("top-hunter-id").innerText = top.drone_id;
        document.getElementById("top-hunter-desc").innerText =
            `Toplam ${top.total_detections} tespit | En Yüksek Skor: ${top.pbest_score.toFixed(2)}`;
    }

    // Yangın Kümeleri & Saha İhbarları
    if (state.fire_clusters) {
        const fireList = document.getElementById("fire-clusters-list");
        if (state.fire_clusters.length === 0) {
            fireList.innerHTML = '<div class="empty-state">Henüz teyit edilmiş yangın odağı yok.</div>';
        } else {
            let fireHtml = "";
            state.fire_clusters.forEach(f => {
                fireHtml += `
                    <div class="cluster-item">
                        <div class="cluster-info">
                            <span class="cluster-title"><i class="fa-solid fa-fire"></i> ${f.id.toUpperCase()}</span>
                            <span class="cluster-sub">GPS: ${f.lat.toFixed(5)}, ${f.lon.toFixed(5)} | Güven: %${(f.confidence*100).toFixed(0)}</span>
                        </div>
                        <div style="display:flex; gap:4px; margin-top:6px; flex-wrap:wrap;">
                            <button class="btn btn-outline btn-sm" style="padding:3px 6px; font-size:9px; color:#00ff88; border-color:#00ff88;" onclick="openDispatchModal(${f.lat}, ${f.lon}, ${f.confidence}, '${f.id}')">
                                <i class="fa-brands fa-whatsapp"></i> TELSİZ / WHATSAPP
                            </button>
                            <button class="btn btn-outline btn-sm" style="padding:3px 6px; font-size:9px;" onclick="copyGpsCoords(${f.lat}, ${f.lon})">
                                <i class="fa-solid fa-copy"></i> GPS
                            </button>
                            <button class="btn btn-warning btn-sm" style="padding:3px 6px; font-size:9px;" onclick="dispatchAndClose(${f.lat}, ${f.lon})">
                                <i class="fa-solid fa-ban"></i> SÖNDÜRÜLDÜ (KAPAT)
                            </button>
                        </div>
                    </div>
                `;

                if (!fireMarkers[f.id]) {
                    const fm = L.marker([f.lat, f.lon], { icon: createFireIcon() }).addTo(map);
                    fm.bindPopup(`
                        <b>YANGIN ODAĞI: ${f.id}</b><br>
                        GPS: ${f.lat.toFixed(5)}, ${f.lon.toFixed(5)}<br>
                        Güven: %${(f.confidence*100).toFixed(0)}<br>
                        <div style="margin-top:6px; display:flex; gap:4px;">
                            <button class="btn btn-primary btn-sm" onclick="openDispatchModal(${f.lat}, ${f.lon}, ${f.confidence}, '${f.id}')">Telsiz İhbarı</button>
                            <button class="btn btn-warning btn-sm" onclick="dispatchAndClose(${f.lat}, ${f.lon})">Kapat</button>
                        </div>
                    `);
                    fireMarkers[f.id] = fm;
                } else {
                    fireMarkers[f.id].setLatLng([f.lat, f.lon]);
                }
            });
            fireList.innerHTML = fireHtml;
        }
    }

    // Kapatılmış Bölgeler
    updateGeofenceZones(state.geofence_zones);

    // Canlı HUD Telemetrisi
    if (state.drones[currentSelectedDrone]) {
        const cd = state.drones[currentSelectedDrone];
        document.getElementById("hud-cam-drone-id").innerText = cd.drone_id;
        document.getElementById("hud-cam-telemetry").innerText =
            `ALT: ${cd.alt.toFixed(1)}m | HIZ: ${cd.speed.toFixed(1)}m/s | SKOR: ${cd.current_score.toFixed(2)}`;
    }
}

/* 6. Kapatılmış Bölgeleri Gösterme */
function updateGeofenceZones(geojson) {
    if (!geojson || !geojson.features) return;
    geofenceLayers.forEach(l => map.removeLayer(l));
    geofenceLayers = [];

    const zoneList = document.getElementById("geofence-zones-list");
    let listHtml = "";

    geojson.features.forEach(f => {
        const props = f.properties;
        const color = props.color || "#ff8800";
        const layer = L.geoJSON(f, {
            style: { color: color, weight: 2, fillColor: color, fillOpacity: 0.25 }
        }).addTo(map);

        layer.bindPopup(`<b>${props.name}</b><br>Tip: ${props.zone_type}<br><button class="btn btn-danger btn-sm" onclick="deleteZone('${props.id}')">Alanı Aç</button>`);
        geofenceLayers.push(layer);

        listHtml += `
            <div class="zone-item" style="border-left-color: ${color};">
                <div class="zone-info">
                    <span class="zone-title">${props.name}</span>
                    <span class="zone-sub">${props.zone_type} (${props.safety_margin}m)</span>
                </div>
                <button class="btn btn-danger btn-sm" onclick="deleteZone('${props.id}')">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </div>
        `;
    });
    zoneList.innerHTML = listHtml || '<div class="empty-state">Henüz kapatılmış bölge yok.</div>';
}

/* 7. Bireysel Drone Kontrol Fonksiyonları */
function droneRtl(droneId) {
    fetch(`/api/drone/${droneId}/rtl`, { method: "POST" })
        .then(r => r.json())
        .then(d => showToast(`🏠 ${droneId} için üsse dönüş (RTL) emri verildi.`, "warning"))
        .catch(e => showToast(`Hata: ${e}`, "danger"));
}

function droneLand(droneId) {
    fetch(`/api/drone/${droneId}/land`, { method: "POST" })
        .then(r => r.json())
        .then(d => showToast(`🔻 ${droneId} için iniş emri verildi.`, "warning"))
        .catch(e => showToast(`Hata: ${e}`, "danger"));
}

function droneDelete(droneId) {
    if (confirm(`${droneId} kodlu drone'u filodan çıkarmak istediğinize emin misiniz?`)) {
        fetch(`/api/drone/${droneId}`, { method: "DELETE" })
            .then(r => r.json())
            .then(d => {
                if (droneMarkers[droneId]) {
                    map.removeLayer(droneMarkers[droneId]);
                    delete droneMarkers[droneId];
                }
                showToast(`❌ ${droneId} filodan çıkarıldı.`, "info");
            })
            .catch(e => showToast(`Hata: ${e}`, "danger"));
    }
}

/* 8. Yeni Drone Ekleme Modalı Mantığı */
function initAddDroneModal() {
    const modal = document.getElementById("add-drone-modal");
    const btnOpen = document.getElementById("btn-open-add-drone");
    const btnFleet = document.getElementById("btn-add-drone-fleet");
    const btnClose = document.getElementById("btn-close-add-drone");
    const btnCancel = document.getElementById("btn-cancel-add-drone");
    const btnSubmit = document.getElementById("btn-submit-add-drone");

    const selectType = document.getElementById("select-new-drone-type");
    const mavlinkExtra = document.getElementById("field-mavlink-extra");
    const volunteerExtra = document.getElementById("field-volunteer-extra");
    const selectSpawn = document.getElementById("select-spawn-location");
    const customCoords = document.getElementById("field-custom-spawn-coords");

    const openModal = (customLat = null, customLon = null) => {
        // Otomatik önerilen ID
        const count = Object.keys(droneMarkers).length + 1;
        document.getElementById("input-new-drone-id").value = `ALPHA-${String(count).padStart(2, '0')}`;

        if (customLat && customLon) {
            selectSpawn.value = "custom";
            customCoords.style.display = "flex";
            document.getElementById("input-spawn-lat").value = customLat.toFixed(5);
            document.getElementById("input-spawn-lon").value = customLon.toFixed(5);
        } else {
            selectSpawn.value = "base";
            customCoords.style.display = "none";
        }
        modal.classList.add("active");
    };

    if (btnOpen) btnOpen.addEventListener("click", () => openModal());
    if (btnFleet) btnFleet.addEventListener("click", () => openModal());
    if (btnClose) btnClose.addEventListener("click", () => modal.classList.remove("active"));
    if (btnCancel) btnCancel.addEventListener("click", () => modal.classList.remove("active"));

    selectType.addEventListener("change", () => {
        const val = selectType.value;
        mavlinkExtra.style.display = val === "mavlink" ? "block" : "none";
        volunteerExtra.style.display = val === "volunteer" ? "block" : "none";
    });

    selectSpawn.addEventListener("change", () => {
        const val = selectSpawn.value;
        customCoords.style.display = val === "custom" ? "flex" : "none";
        if (val === "map_center") {
            const c = map.getCenter();
            document.getElementById("input-spawn-lat").value = c.lat.toFixed(5);
            document.getElementById("input-spawn-lon").value = c.lng.toFixed(5);
        }
    });

    btnSubmit.addEventListener("click", () => {
        const dId = document.getElementById("input-new-drone-id").value.trim();
        const dType = selectType.value;
        const spawnLoc = selectSpawn.value;
        const alt = parseFloat(document.getElementById("input-spawn-alt").value) || 40.0;
        let lat = null;
        let lon = null;

        if (spawnLoc === "custom" || spawnLoc === "map_center") {
            lat = parseFloat(document.getElementById("input-spawn-lat").value);
            lon = parseFloat(document.getElementById("input-spawn-lon").value);
        }

        const payload = {
            drone_id: dId || null,
            drone_type: dType,
            spawn_location: spawnLoc,
            lat: lat,
            lon: lon,
            alt: alt,
            connection_string: document.getElementById("input-mavlink-conn") ? document.getElementById("input-mavlink-conn").value : null,
            camera_url: document.getElementById("input-mavlink-cam") ? document.getElementById("input-mavlink-cam").value : null,
            pilot_name: document.getElementById("input-vol-pilot") ? document.getElementById("input-vol-pilot").value : null
        };

        btnSubmit.disabled = true;
        btnSubmit.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Ekleniyor...';

        fetch("/api/swarm/add_drone", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        })
        .then(r => r.json())
        .then(res => {
            btnSubmit.disabled = false;
            btnSubmit.innerHTML = '<i class="fa-solid fa-plus"></i> SÜRÜYE DAHİL ET';
            modal.classList.remove("active");
            if (res.status === "success") {
                showToast(`✓ ${res.drone_id} başarıyla sürüye eklendi ve kalkışa geçti!`, "success");
                selectDrone(res.drone_id);
            } else {
                showToast(res.message || "Drone eklenemedi.", "danger");
            }
        })
        .catch(err => {
            btnSubmit.disabled = false;
            btnSubmit.innerHTML = '<i class="fa-solid fa-plus"></i> SÜRÜYE DAHİL ET';
            showToast("Hata: " + err, "danger");
        });
    });

    window.openAddDroneModal = openModal;
}

/* 9. Operasyon Üssü ve Başlangıç Konumu Modalı */
function openBaseModal() {
    const modal = document.getElementById("base-modal");
    document.getElementById("input-base-name").value = baseStation.name;
    document.getElementById("input-base-lat").value = baseStation.lat.toFixed(5);
    document.getElementById("input-base-lon").value = baseStation.lon.toFixed(5);
    modal.classList.add("active");
}

function initBaseManagement() {
    const modal = document.getElementById("base-modal");
    const widget = document.getElementById("widget-base-station");
    const btnOpen = document.getElementById("btn-open-base-modal");
    const btnClose = document.getElementById("btn-close-base");
    const btnCancel = document.getElementById("btn-cancel-base");
    const btnSubmit = document.getElementById("btn-submit-base");

    const selectPreset = document.getElementById("select-base-preset");
    const btnGps = document.getElementById("btn-base-get-gps");
    const btnCenter = document.getElementById("btn-base-get-center");

    if (widget) widget.addEventListener("click", openBaseModal);
    if (btnOpen) btnOpen.addEventListener("click", openBaseModal);
    if (btnClose) btnClose.addEventListener("click", () => modal.classList.remove("active"));
    if (btnCancel) btnCancel.addEventListener("click", () => modal.classList.remove("active"));

    selectPreset.addEventListener("change", (e) => {
        const selectedOpt = selectPreset.options[selectPreset.selectedIndex];
        if (selectedOpt && selectedOpt.dataset.lat) {
            document.getElementById("input-base-name").value = selectedOpt.dataset.name + " İleri Harekat Üssü";
            document.getElementById("input-base-lat").value = parseFloat(selectedOpt.dataset.lat).toFixed(5);
            document.getElementById("input-base-lon").value = parseFloat(selectedOpt.dataset.lon).toFixed(5);
        }
    });

    btnGps.addEventListener("click", () => {
        if (navigator.geolocation) {
            btnGps.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Alınıyor...';
            navigator.geolocation.getCurrentPosition(
                pos => {
                    btnGps.innerHTML = '<i class="fa-solid fa-crosshairs"></i> Cihazımın GPS\'ini Al';
                    document.getElementById("input-base-lat").value = pos.coords.latitude.toFixed(5);
                    document.getElementById("input-base-lon").value = pos.coords.longitude.toFixed(5);
                    document.getElementById("input-base-name").value = "Saha Mobil Operasyon Üssü (GPS)";
                    showToast("Cihaz GPS konumu alındı.", "info");
                },
                err => {
                    btnGps.innerHTML = '<i class="fa-solid fa-crosshairs"></i> Cihazımın GPS\'ini Al';
                    showToast("GPS hatası: " + err.message, "danger");
                },
                { enableHighAccuracy: true }
            );
        }
    });

    btnCenter.addEventListener("click", () => {
        const c = map.getCenter();
        document.getElementById("input-base-lat").value = c.lat.toFixed(5);
        document.getElementById("input-base-lon").value = c.lng.toFixed(5);
        showToast("Harita merkez koordinatları aktarıldı.", "info");
    });

    btnSubmit.addEventListener("click", () => {
        const name = document.getElementById("input-base-name").value.trim() || "Ana Operasyon Üssü";
        const lat = parseFloat(document.getElementById("input-base-lat").value);
        const lon = parseFloat(document.getElementById("input-base-lon").value);
        const redeploy = document.getElementById("chk-redeploy-drones").checked;
        const savePerm = document.getElementById("chk-save-permanent").checked;
        const regenFires = document.getElementById("chk-regen-fires").checked;

        if (isNaN(lat) || isNaN(lon)) {
            showToast("Geçerli bir koordinat giriniz.", "danger");
            return;
        }

        updateBaseStation(lat, lon, name, redeploy, savePerm, regenFires);
        modal.classList.remove("active");
    });
}

/* 10. Telsiz & WhatsApp İhbar Modalı */
function openDispatchModal(lat, lon, confidence, fireId = "YANGIN-01") {
    const modal = document.getElementById("dispatch-modal");
    const textarea = document.getElementById("text-dispatch-content");
    const dateStr = new Date().toLocaleString("tr-TR");

    const text = `🚨 [PYRESWARM OTONOM YANGIN TESPİT RAPORU] 🚨
⏱️ Tarih / Saat: ${dateStr}
📍 Yangın Koordinatı: ${lat.toFixed(6)} N, ${lon.toFixed(6)} E
🔥 Güven Skoru: %${(confidence * 100).toFixed(1)} (${confidence > 0.85 ? "YÜKSEK ŞİDDET" : "DUMAN İHBARI"})
🗺️ Google Haritalar: https://maps.google.com/?q=${lat.toFixed(6)},${lon.toFixed(6)}
⚓ Operasyon Üssü: ${baseStation.name}
🚒 Durum: OGM ve İtfaiye müdahale ekiplerinin acilen bölgeye sevki gerekmektedir.`;

    textarea.value = text;
    modal.classList.add("active");
}

function initDispatchModal() {
    const modal = document.getElementById("dispatch-modal");
    const btnClose = document.getElementById("btn-close-dispatch");
    const btnClose2 = document.getElementById("btn-close-dispatch-btn");
    const btnCopy = document.getElementById("btn-copy-dispatch");

    if (btnClose) btnClose.addEventListener("click", () => modal.classList.remove("active"));
    if (btnClose2) btnClose2.addEventListener("click", () => modal.classList.remove("active"));

    btnCopy.addEventListener("click", () => {
        const text = document.getElementById("text-dispatch-content").value;
        navigator.clipboard.writeText(text).then(() => {
            showToast("Telsiz ihbar metni panoya kopyalandı!", "success");
            modal.classList.remove("active");
        });
    });
}

/* 11. Toast Bildirim Sistemi */
function showToast(message, type = "info", duration = 4000) {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast-item toast-${type}`;
    let icon = "fa-circle-info";
    if (type === "success") icon = "fa-circle-check";
    if (type === "danger") icon = "fa-triangle-exclamation";
    if (type === "warning") icon = "fa-bell";

    toast.innerHTML = `<i class="fa-solid ${icon}" style="font-size:14px;"></i> <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(50px)";
        toast.style.transition = "all 0.3s ease";
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

/* 12. Sağ Tık Bağlam Menüsü (Context Menu) */
function handleMapContextMenu(e) {
    contextMenuLatLng = e.latlng;
    const menu = document.getElementById("map-context-menu");
    menu.style.display = "block";
    menu.style.left = `${e.containerPoint.x + 10}px`;
    menu.style.top = `${e.containerPoint.y + 10}px`;
}

function hideContextMenu() {
    const menu = document.getElementById("map-context-menu");
    if (menu) menu.style.display = "none";
}

function initContextMenu() {
    document.addEventListener("click", (e) => {
        if (!e.target.closest("#map-context-menu")) hideContextMenu();
    });

    document.getElementById("ctx-set-base").addEventListener("click", () => {
        if (contextMenuLatLng) {
            updateBaseStation(contextMenuLatLng.lat, contextMenuLatLng.lng, baseStation.name, true, true, true);
            hideContextMenu();
        }
    });

    document.getElementById("ctx-spawn-drone").addEventListener("click", () => {
        if (contextMenuLatLng) {
            hideContextMenu();
            if (window.openAddDroneModal) {
                window.openAddDroneModal(contextMenuLatLng.lat, contextMenuLatLng.lng);
            }
        }
    });

    document.getElementById("ctx-add-fire").addEventListener("click", () => {
        if (contextMenuLatLng) {
            fetch("/api/mission/add_fire_spot", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ lat: contextMenuLatLng.lat, lon: contextMenuLatLng.lng, intensity: 0.95 })
            }).then(() => {
                showToast("Yangın ihbarı eklendi. Sürü hedefe yönlendiriliyor!", "warning");
            });
            hideContextMenu();
        }
    });

    document.getElementById("ctx-close-extinguished").addEventListener("click", () => {
        if (contextMenuLatLng) {
            dispatchAndClose(contextMenuLatLng.lat, contextMenuLatLng.lng);
            hideContextMenu();
        }
    });
}

/* 13. Çizim ve İnteraktif Araçlar */
function setInteractionMode(mode, instruction) {
    interactionMode = mode;
    activeDrawPoints = [];
    document.getElementById("draw-instruction").style.display = "block";
    document.getElementById("draw-instruction-text").innerText = instruction;
    document.getElementById("btn-clear-draw").style.display = "flex";

    document.querySelectorAll(".tool-btn").forEach(b => b.classList.remove("active"));
    if (mode === "spawn_drone") document.getElementById("btn-mode-spawn").classList.add("active");
    if (mode === "add_fire") document.getElementById("btn-mode-firespot").classList.add("active");
    if (mode === "aoi") document.getElementById("btn-draw-aoi").classList.add("active");
    if (mode === "water_body") document.getElementById("btn-draw-lake").classList.add("active");
    if (mode === "fire_extinguished") document.getElementById("btn-draw-extinguished").classList.add("active");
}

function cancelInteractionMode() {
    interactionMode = null;
    activeDrawPoints = [];
    if (activeDrawPolyline) {
        map.removeLayer(activeDrawPolyline);
        activeDrawPolyline = null;
    }
    document.getElementById("draw-instruction").style.display = "none";
    document.getElementById("btn-clear-draw").style.display = "none";
    document.querySelectorAll(".tool-btn").forEach(b => b.classList.remove("active"));
}

function handleMapClick(e) {
    hideContextMenu();
    if (!interactionMode) return;

    const lat = e.latlng.lat;
    const lon = e.latlng.lng;

    if (interactionMode === "spawn_drone") {
        cancelInteractionMode();
        if (window.openAddDroneModal) {
            window.openAddDroneModal(lat, lon);
        }
        return;
    }

    if (interactionMode === "add_fire") {
        fetch("/api/mission/add_fire_spot", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ lat: lat, lon: lon, intensity: 0.95 })
        }).then(() => {
            showToast(`Yangın ihbarı eklendi: (${lat.toFixed(5)}, ${lon.toFixed(5)})`, "warning");
            cancelInteractionMode();
        });
        return;
    }

    activeDrawPoints.push([lat, lon]);

    if (!activeDrawPolyline) {
        activeDrawPolyline = L.polyline(activeDrawPoints, { color: '#00e5ff', weight: 2, dashArray: '5, 5' }).addTo(map);
    } else {
        activeDrawPolyline.setLatLngs(activeDrawPoints);
    }

    if (interactionMode === "aoi" && activeDrawPoints.length >= 2) {
        const p1 = activeDrawPoints[0];
        const p2 = activeDrawPoints[1];
        const minLat = Math.min(p1[0], p2[0]);
        const maxLat = Math.max(p1[0], p2[0]);
        const minLon = Math.min(p1[1], p2[1]);
        const maxLon = Math.max(p1[1], p2[1]);

        fetch("/api/mission/set_aoi", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ min_lat: minLat, max_lat: maxLat, min_lon: minLon, max_lon: maxLon })
        }).then(() => {
            if (aoiLayer) map.removeLayer(aoiLayer);
            aoiLayer = L.rectangle([[minLat, minLon], [maxLat, maxLon]], {
                color: "#00e5ff", weight: 2, fill: false, dashArray: "6, 6"
            }).addTo(map);
            aoiLayer.bindPopup("<b>Operasyon Arama Sınırı (AOI)</b>");
            showToast("Arama sınırı (AOI) başarıyla tanımlandı!", "success");
            cancelInteractionMode();
        });
        return;
    }

    if (activeDrawPoints.length >= 4) {
        finishPolygonDrawing();
    }
}

function finishPolygonDrawing() {
    if (activeDrawPoints.length < 3) return;

    const typeNames = {
        "water_body": "Göl / Su Bölgesi",
        "fire_extinguished": "Söndürülmüş Yangın Bölgesi"
    };

    const name = prompt("Kapatılacak alanın adı:", typeNames[interactionMode] || "Kapatılmış Alan");
    if (!name) { cancelInteractionMode(); return; }

    fetch("/api/geofence/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            name: name,
            zone_type: interactionMode,
            coordinates: activeDrawPoints
        })
    }).then(() => {
        showToast(`${name} başarıyla haritada kapatıldı.`, "info");
        cancelInteractionMode();
    });
}

/* 14. Şehir ve Bölge Arama */
function initLocationSearch() {
    const input = document.getElementById("input-search-location");
    const btnSearch = document.getElementById("btn-search-location");
    const btnGps = document.getElementById("btn-gps-locate");
    const btnRelocate = document.getElementById("btn-relocate-swarm");

    const doSearch = () => {
        const query = input.value.trim();
        if (!query) return;

        fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}`)
            .then(r => r.json())
            .then(results => {
                if (results && results.length > 0) {
                    const lat = parseFloat(results[0].lat);
                    const lon = parseFloat(results[0].lon);
                    map.flyTo([lat, lon], 14);
                    if (confirm(`Harita "${results[0].display_name}" bölgesine taşındı.\nOperasyon üssünü de buraya konuşlandırmak ister misiniz?`)) {
                        updateBaseStation(lat, lon, `${query} İleri Üssü`, true, true, true);
                    }
                } else {
                    showToast("Konum bulunamadı! İlçe veya il belirtin.", "warning");
                }
            })
            .catch(err => showToast("Arama servisi hatası: " + err, "danger"));
    };

    btnSearch.addEventListener("click", doSearch);
    input.addEventListener("keydown", (e) => { if (e.key === "Enter") doSearch(); });

    btnGps.addEventListener("click", () => {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (pos) => {
                    const lat = pos.coords.latitude;
                    const lon = pos.coords.longitude;
                    map.flyTo([lat, lon], 15);
                    if (confirm(`GPS Konumunuz tespit edildi: (${lat.toFixed(5)}, ${lon.toFixed(5)}).\nOperasyon üssünü buraya taşımak ister misiniz?`)) {
                        updateBaseStation(lat, lon, "Saha Mobil Operasyon Üssü (GPS)", true, true, true);
                    }
                },
                (err) => showToast("GPS konumu alınamadı: " + err.message, "danger"),
                { enableHighAccuracy: true }
            );
        } else {
            showToast("Tarayıcınız GPS servisini desteklemiyor.", "warning");
        }
    });

    btnRelocate.addEventListener("click", () => {
        const c = map.getCenter();
        if (confirm(`Sürü operasyon üssü haritanın merkezine (${c.lat.toFixed(5)}, ${c.lng.toFixed(5)}) taşınsın mı?`)) {
            updateBaseStation(c.lat, c.lng, "Harita Merkez Üssü", true, true, true);
        }
    });
}

/* 15. Saha Rüzgar Modalı */
function initWindModal() {
    const modal = document.getElementById("wind-modal");
    const widget = document.getElementById("widget-wind-ctrl");
    const btnClose = document.getElementById("btn-close-wind");
    const btnCancel = document.getElementById("btn-cancel-wind");
    const btnSubmit = document.getElementById("btn-submit-wind");

    const speedRange = document.getElementById("input-wind-speed");
    const dirRange = document.getElementById("input-wind-dir");
    const speedLabel = document.getElementById("val-wind-speed");
    const dirLabel = document.getElementById("val-wind-dir");

    const getWindName = (deg) => {
        if (deg >= 337.5 || deg < 22.5) return "Yıldız (Kuzey)";
        if (deg >= 22.5 && deg < 67.5) return "Poyraz (Kuzeydoğu)";
        if (deg >= 67.5 && deg < 112.5) return "Gündoğusu (Doğu)";
        if (deg >= 112.5 && deg < 157.5) return "Keşişleme (Güneydoğu)";
        if (deg >= 157.5 && deg < 202.5) return "Kıble (Güney)";
        if (deg >= 202.5 && deg < 247.5) return "Lodos (Güneybatı)";
        if (deg >= 247.5 && deg < 292.5) return "Günbatısı (Batı)";
        return "Karayel (Kuzeybatı)";
    };

    const updateLabels = () => {
        const spd = parseFloat(speedRange.value);
        const dir = parseInt(dirRange.value);
        speedLabel.innerText = `${spd.toFixed(1)} m/s (~${(spd*3.6).toFixed(0)} km/h)`;
        dirLabel.innerText = `${dir}° (${getWindName(dir)})`;
    };

    speedRange.addEventListener("input", updateLabels);
    dirRange.addEventListener("input", updateLabels);

    widget.addEventListener("click", () => modal.classList.add("active"));
    btnClose.addEventListener("click", () => modal.classList.remove("active"));
    btnCancel.addEventListener("click", () => modal.classList.remove("active"));

    btnSubmit.addEventListener("click", () => {
        const spd = parseFloat(speedRange.value);
        const dir = parseInt(dirRange.value);

        fetch("/api/mission/set_wind", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ speed_ms: spd, direction_deg: dir })
        }).then(() => {
            modal.classList.remove("active");
            document.getElementById("wind-speed-text").innerText = `${spd.toFixed(1)} m/s`;
            document.getElementById("wind-arrow-icon").style.transform = `rotate(${dir}deg)`;
            showToast(`Rüzgar güncellendi: ${spd.toFixed(1)} m/s (${getWindName(dir)})`, "info");
        });
    });
}

/* 16. Yangın İhbarı & Koordinat İşlemleri */
function copyGpsCoords(lat, lon) {
    const text = `🚨 PYRESWARM YANGIN: Koordinat: ${lat.toFixed(6)}, ${lon.toFixed(6)} | Harita: https://maps.google.com/?q=${lat},${lon}`;
    navigator.clipboard.writeText(text).then(() => {
        showToast("GPS Koordinatı panoya kopyalandı!", "success");
    });
}

function dispatchAndClose(lat, lon) {
    const d = 0.0006;
    const coords = [
        [lat + d, lon - d],
        [lat + d, lon + d],
        [lat - d, lon + d],
        [lat - d, lon - d]
    ];
    fetch("/api/geofence/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            name: "Söndürülen Yangın Alanı",
            zone_type: "fire_extinguished",
            coordinates: coords
        })
    }).then(() => {
        showToast("Yangın bölgesi söndürüldü olarak işaretlendi ve kapatıldı.", "warning");
    });
}

function exportIncidentReport() {
    fetch("/api/mission/export_report")
        .then(r => r.json())
        .then(data => {
            const str = JSON.stringify(data, null, 2);
            const blob = new Blob([str], { type: "application/json" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `pyreswarm_yangin_kriz_raporu_${Date.now()}.json`;
            a.click();
            URL.revokeObjectURL(url);
            showToast("Kriz koordinat raporu indirildi.", "success");
        });
}

/* 17. Standart Buton Dinleyicileri */
function initControls() {
    document.getElementById("btn-start").addEventListener("click", () => {
        fetch("/api/mission/start", { method: "POST" })
            .then(() => showToast("Sürü otonom yangın devriyesine başladı!", "success"));
    });

    document.getElementById("btn-pause").addEventListener("click", () => {
        fetch("/api/mission/pause", { method: "POST" })
            .then(() => showToast("Sürü havada sabitlendi (Loiter / Bekleme).", "warning"));
    });

    document.getElementById("btn-rtl").addEventListener("click", () => {
        if (confirm("Tüm sürüye kalkış noktasına geri dönme (RTL) emri verilsin mi?")) {
            fetch("/api/mission/rtl", { method: "POST" })
                .then(() => showToast("Tüm sürüye RTL emri verildi!", "danger"));
        }
    });

    document.getElementById("btn-export-incident").addEventListener("click", exportIncidentReport);

    // Hızlı Tatbikat Yangını Butonu
    const btnQuickFire = document.getElementById("btn-quick-fire");
    if (btnQuickFire) {
        btnQuickFire.addEventListener("click", () => {
            fetch("/api/mission/scenario/quick_fire", { method: "POST" })
                .then(r => r.json())
                .then(d => {
                    showToast(`🔥 Saha tatbikatı: ${d.lat.toFixed(4)}, ${d.lon.toFixed(4)} koordinatında yangın odağı başlatıldı!`, "warning", 5000);
                });
        });
    }

    // 10 km2 AOI Butonu
    const btnQuickAoi = document.getElementById("btn-quick-aoi-10");
    if (btnQuickAoi) {
        btnQuickAoi.addEventListener("click", () => {
            const d = 0.015; // ~10 km² kutu
            const minLat = baseStation.lat - d;
            const maxLat = baseStation.lat + d;
            const minLon = baseStation.lon - d * 1.2;
            const maxLon = baseStation.lon + d * 1.2;

            fetch("/api/mission/set_aoi", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ min_lat: minLat, max_lat: maxLat, min_lon: minLon, max_lon: maxLon })
            }).then(() => {
                if (aoiLayer) map.removeLayer(aoiLayer);
                aoiLayer = L.rectangle([[minLat, minLon], [maxLat, maxLon]], {
                    color: "#00e5ff", weight: 2, fill: false, dashArray: "6, 6"
                }).addTo(map);
                showToast("Üs merkezli 10 km² Arama Alanı (AOI) çizildi.", "success");
            });
        });
    }

    // Çizim Araçları
    document.getElementById("btn-mode-spawn").addEventListener("click", () => setInteractionMode("spawn_drone", "Haritada yeni drone konuşlandırmak istediğiniz noktaya tıklayın."));
    document.getElementById("btn-mode-firespot").addEventListener("click", () => setInteractionMode("add_fire", "Haritada yangın/duman ihbarı eklemek istediğiniz noktaya tıklayın."));
    document.getElementById("btn-draw-aoi").addEventListener("click", () => setInteractionMode("aoi", "Arama sınırının (AOI) iki çapraz köşesine tıklayın."));
    document.getElementById("btn-draw-lake").addEventListener("click", () => setInteractionMode("water_body", "Göl/su alanının en az 3 köşe noktasına tıklayın."));
    document.getElementById("btn-draw-extinguished").addEventListener("click", () => setInteractionMode("fire_extinguished", "Söndürülmüş yangın alanının köşelerine tıklayın."));
    document.getElementById("btn-clear-draw").addEventListener("click", cancelInteractionMode);

    document.getElementById("video-drone-select").addEventListener("change", (e) => selectDrone(e.target.value));
}

function selectDrone(droneId) {
    currentSelectedDrone = droneId;
    document.getElementById("video-drone-select").value = droneId;
    document.getElementById("hud-cam-drone-id").innerText = droneId;
    initVideoFeed();
}

function initVideoFeed() {
    const img = document.getElementById("live-video-feed");
    img.src = `/api/video_feed/${currentSelectedDrone}?t=${Date.now()}`;
}

function deleteZone(zoneId) {
    if (confirm("Bu kapatılmış alanı tekrar aramaya açmak istediğinizden emin misiniz?")) {
        fetch(`/api/geofence/${zoneId}`, { method: "DELETE" })
            .then(() => showToast("Bölge aramaya açıldı.", "info"));
    }
}

/* 18. Matematiksel Kapsama ve Süre Hesaplayıcı */
function initMetricsCalculator() {
    const areaInput = document.getElementById("calc-area");
    const dronesInput = document.getElementById("calc-drones");
    if (!areaInput || !dronesInput) return;

    const recalculate = () => {
        const area = parseFloat(areaInput.value) || 10.0;
        const drones = parseInt(dronesInput.value) || 4;

        fetch(`/api/metrics/calculate?area_km2=${area}&num_drones=${drones}`)
            .then(r => r.json())
            .then(data => {
                const speed = data.coverage_rate.swarm_total_km2h;
                const mins = data.detection_times.t_target_conf_minutes;
                document.getElementById("calc-speed-res").innerText = `${speed} km²/h`;
                document.getElementById("calc-time-res").innerText = mins < 60 ? `${mins} dk` : `${(mins/60).toFixed(1)} saat`;
            })
            .catch(err => console.error("Metrik hesaplama hatası:", err));
    };

    areaInput.addEventListener("input", recalculate);
    dronesInput.addEventListener("input", recalculate);
    recalculate();
}
