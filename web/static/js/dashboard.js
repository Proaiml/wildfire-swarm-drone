/**
 * PyreSwarm - Next-Gen Autonomous Mission Control JavaScript
 * Gerçek zamanlı Leaflet harita, WebSocket telemetrisi, dinamik poligon çizimi ve video yönetimi.
 */

let map;
let droneMarkers = {};
let fireMarkers = {};
let geofenceLayers = [];
let currentSelectedDrone = "ALPHA-01";
let drawingMode = null; // 'water_body', 'fire_extinguished', 'no_fly_zone'
let activeDrawPoints = [];
let activeDrawPolyline = null;

document.addEventListener("DOMContentLoaded", () => {
    initMap();
    initWebSocket();
    initControls();
    initVideoFeed();
    initMetricsCalculator();
});

/* 1. Harita Kurulumu */
function initMap() {
    // Muğla/Ege ormanlık operasyon merkezi
    map = L.map("map", {
        center: [37.0500, 28.3200],
        zoom: 14,
        zoomControl: false
    });

    L.control.zoom({ position: "bottomright" }).addTo(map);

    // Koyu Havacılık Harita Katmanı (CartoDB DarkMatter)
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
        attribution: '&copy; OpenStreetMap &copy; CARTO',
        subdomains: 'abcd',
        maxZoom: 19
    }).addTo(map);

    // Harita Tıklama Dinleyicisi (Poligon Çizimi için)
    map.on("click", handleMapClick);
}

/* 2. Özel Drone İkonu Üretimi */
function createDroneIcon(heading, isArmed, score) {
    const glowClass = score > 0.4 ? "drone-glow-fire" : "";
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

/* 3. WebSocket Telemetri Dinleyicisi */
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
        console.warn("WebSocket bağlantısı koptu, 2 saniye sonra tekrar deneniyor...");
        setTimeout(initWebSocket, 2000);
    };
}

/* 4. Arayüz ve Harita Güncellemesi */
function updateDashboard(state) {
    // Üst Bar Sayaçları
    document.getElementById("stat-drone-count").innerText = state.drones_count;
    document.getElementById("stat-gbest-score").innerText = state.gbest.fitness.toFixed(2);
    document.getElementById("stat-fire-count").innerText = state.fire_clusters ? state.fire_clusters.length : 0;
    
    // Görev Durumu
    const modeBadge = document.getElementById("swarm-mode-badge");
    if (state.is_mission_active) {
        modeBadge.innerText = "DEVİREDE (PSO)";
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
    
    // Dropdown senkronizasyonu
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
        
        // Tablo satırı
        const isFire = d.current_score > 0.3;
        const scoreStyle = isFire ? "color: #ff5500; font-weight: bold;" : "";

        tbodyHtml += `
            <tr onclick="selectDrone('${d.drone_id}')" style="cursor: pointer;">
                <td><strong>${d.drone_id}</strong></td>
                <td><span style="font-size:9px; color:#8b9bb4;">${d.type}</span></td>
                <td>${d.alt.toFixed(1)}m</td>
                <td>${d.speed.toFixed(1)}m/s</td>
                <td>${d.battery.toFixed(0)}%</td>
                <td style="${scoreStyle}">${d.pbest_score.toFixed(2)}</td>
            </tr>
        `;

        // Harita İkonu
        if (!droneMarkers[id]) {
            const m = L.marker([d.lat, d.lon], {
                icon: createDroneIcon(d.heading, d.is_armed, d.current_score)
            }).addTo(map);
            m.bindPopup(`<b>${d.drone_id}</b><br>İrtifa: ${d.alt}m<br>Hız: ${d.speed}m/s`);
            droneMarkers[id] = m;
        } else {
            droneMarkers[id].setLatLng([d.lat, d.lon]);
            droneMarkers[id].setIcon(createDroneIcon(d.heading, d.is_armed, d.current_score));
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

    // Yangın Odakları
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
                            <span class="cluster-sub">GPS: ${f.lat.toFixed(4)}, ${f.lon.toFixed(4)} | Güven: %${(f.confidence*100).toFixed(0)}</span>
                        </div>
                        <button class="btn btn-warning btn-sm" onclick="closeFireCluster(${f.lat}, ${f.lon})">
                            <i class="fa-solid fa-check"></i> Söndürüldü Olarak Kapat
                        </button>
                    </div>
                `;

                // Haritada Yangın İkonu
                if (!fireMarkers[f.id]) {
                    const fm = L.marker([f.lat, f.lon], { icon: createFireIcon() }).addTo(map);
                    fm.bindPopup(`<b>YANGIN ODAĞI: ${f.id}</b><br>Güven: %${(f.confidence*100).toFixed(0)}`);
                    fireMarkers[f.id] = fm;
                } else {
                    fireMarkers[f.id].setLatLng([f.lat, f.lon]);
                }
            });
            fireList.innerHTML = fireHtml;
        }
    }

    // Kapatılmış Bölgeler (Geofence)
    updateGeofenceZones(state.geofence_zones);

    // Canlı HUD Güncellemesi
    if (state.drones[currentSelectedDrone]) {
        const cd = state.drones[currentSelectedDrone];
        document.getElementById("hud-cam-drone-id").innerText = cd.drone_id;
        document.getElementById("hud-cam-telemetry").innerText = 
            `ALT: ${cd.alt.toFixed(1)}m | HIZ: ${cd.speed.toFixed(1)}m/s | SKOR: ${cd.current_score.toFixed(2)}`;
    }
}

/* 5. Kapatılmış Bölgeleri Haritada Gösterme */
function updateGeofenceZones(geojson) {
    if (!geojson || !geojson.features) return;

    // Eski katmanları temizle
    geofenceLayers.forEach(l => map.removeLayer(l));
    geofenceLayers = [];

    const zoneList = document.getElementById("geofence-zones-list");
    let listHtml = "";

    geojson.features.forEach(f => {
        const props = f.properties;
        const color = props.color || "#ff8800";
        
        const layer = L.geoJSON(f, {
            style: {
                color: color,
                weight: 2,
                fillColor: color,
                fillOpacity: 0.25
            }
        }).addTo(map);
        
        layer.bindPopup(`<b>${props.name}</b><br>Tip: ${props.zone_type}<br><button class="btn btn-danger btn-sm" onclick="deleteZone('${props.id}')">Alanı Aç</button>`);
        geofenceLayers.push(layer);

        listHtml += `
            <div class="zone-item" style="border-left-color: ${color};">
                <div class="zone-info">
                    <span class="zone-title">${props.name}</span>
                    <span class="zone-sub">${props.zone_type} (${props.safety_margin}m tampon)</span>
                </div>
                <button class="btn btn-danger btn-sm" onclick="deleteZone('${props.id}')">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </div>
        `;
    });

    zoneList.innerHTML = listHtml || '<div class="empty-state">Henüz kapatılmış bölge yok.</div>';
}

/* 6. Poligon Çizim Araçları */
function startDrawing(mode) {
    drawingMode = mode;
    activeDrawPoints = [];
    document.getElementById("draw-instruction").style.display = "block";
    document.getElementById("btn-clear-draw").style.display = "flex";
    
    // Buton aktiflik sınıfları
    document.querySelectorAll(".tool-btn").forEach(b => b.classList.remove("active"));
    if (mode === "water_body") document.getElementById("btn-draw-lake").classList.add("active");
    if (mode === "fire_extinguished") document.getElementById("btn-draw-extinguished").classList.add("active");
    if (mode === "no_fly_zone") document.getElementById("btn-draw-nofly").classList.add("active");
}

function cancelDrawing() {
    drawingMode = null;
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
    if (!drawingMode) return;

    const lat = e.latlng.lat;
    const lon = e.latlng.lng;

    // İlk noktaya yakın bir yere tekrar tıklandıysa veya 4+ nokta olduysa tamamla
    if (activeDrawPoints.length >= 3) {
        const first = activeDrawPoints[0];
        const dist = Math.hypot(lat - first[0], lon - first[1]);
        if (dist < 0.001) { // ~100 metre yakınlık
            finishDrawing();
            return;
        }
    }

    activeDrawPoints.push([lat, lon]);

    if (!activeDrawPolyline) {
        activeDrawPolyline = L.polyline(activeDrawPoints, { color: '#ff5500', weight: 2, dashArray: '5, 5' }).addTo(map);
    } else {
        activeDrawPolyline.setLatLngs(activeDrawPoints);
    }

    if (activeDrawPoints.length >= 4) {
        // 4 nokta girilince otomatik kaydet seçeneği
        finishDrawing();
    }
}

function finishDrawing() {
    if (activeDrawPoints.length < 3) {
        alert("Bölge kapatmak için en az 3 köşe noktası tıklamalısınız!");
        return;
    }

    const typeNames = {
        "water_body": "Göl / Su Bölgesi",
        "fire_extinguished": "Söndürülmüş Yangın Bölgesi",
        "no_fly_zone": "Uçuşa Yasak Bölge"
    };

    const name = prompt("Kapatılacak alanın adı:", typeNames[drawingMode] || "Kapatılmış Alan");
    if (!name) {
        cancelDrawing();
        return;
    }

    fetch("/api/geofence/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            name: name,
            zone_type: drawingMode,
            coordinates: activeDrawPoints
        })
    })
    .then(r => r.json())
    .then(data => {
        cancelDrawing();
    })
    .catch(err => {
        console.error("Geofence kayıt hatası:", err);
        cancelDrawing();
    });
}

/* 7. Kontrol Butonları Dinleyicileri */
function initControls() {
    document.getElementById("btn-start").addEventListener("click", () => {
        fetch("/api/mission/start", { method: "POST" });
    });

    document.getElementById("btn-pause").addEventListener("click", () => {
        fetch("/api/mission/pause", { method: "POST" });
    });

    document.getElementById("btn-rtl").addEventListener("click", () => {
        if (confirm("Tüm sürüye kalkış noktasına geri dönme (RTL) emri verilsin mi?")) {
            fetch("/api/mission/rtl", { method: "POST" });
        }
    });

    document.getElementById("btn-spawn-sim").addEventListener("click", () => {
        fetch("/api/swarm/spawn_simulated", { method: "POST" });
    });

    // Çizim Butonları
    document.getElementById("btn-draw-lake").addEventListener("click", () => startDrawing("water_body"));
    document.getElementById("btn-draw-extinguished").addEventListener("click", () => startDrawing("fire_extinguished"));
    document.getElementById("btn-draw-nofly").addEventListener("click", () => startDrawing("no_fly_zone"));
    document.getElementById("btn-clear-draw").addEventListener("click", cancelDrawing);

    // Gönüllü Modal
    const modal = document.getElementById("volunteer-modal");
    document.getElementById("btn-open-volunteer").addEventListener("click", () => modal.classList.add("active"));
    document.getElementById("btn-close-volunteer").addEventListener("click", () => modal.classList.remove("active"));
    document.getElementById("btn-cancel-volunteer").addEventListener("click", () => modal.classList.remove("active"));

    document.getElementById("btn-submit-volunteer").addEventListener("click", () => {
        const name = document.getElementById("vol-pilot-name").value || "Gönüllü Pilot";
        const lat = parseFloat(document.getElementById("vol-lat").value);
        const lon = parseFloat(document.getElementById("vol-lon").value);
        const cam = document.getElementById("vol-cam-url").value || null;

        fetch("/api/swarm/register_volunteer", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                pilot_name: name,
                lat: lat,
                lon: lon,
                camera_url: cam
            })
        })
        .then(r => r.json())
        .then(data => {
            modal.classList.remove("active");
            alert(`Gönüllü Drone (${data.drone_id}) başarıyla sürü koordinasyon ağına katıldı!`);
        });
    });

    // Video Dropdown
    document.getElementById("video-drone-select").addEventListener("change", (e) => {
        selectDrone(e.target.value);
    });
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
        fetch(`/api/geofence/${zoneId}`, { method: "DELETE" });
    }
}

function closeFireCluster(lat, lon) {
    // Yangın söndürüldü, etrafındaki 60m alanı otomatik kapat
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
            name: "Söndürülmüş Yangın Alanı",
            zone_type: "fire_extinguished",
            coordinates: coords
        })
    });
}

/* 8. Matematiksel Kapsama ve Süre Hesaplayıcı */
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
