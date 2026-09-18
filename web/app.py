"""
PyreSwarm - Web Görev Kontrol Merkezi (Web Mission Control GCS)
FastAPI tabanlı REST API, MJPEG video akışı ve gerçek zamanlı WebSocket telemetrisi.
"""

import os
import asyncio
import json
from typing import List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Response, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.swarm_manager import SwarmManager
from core.geofence_manager import ZoneType
from hardware.simulated_drone import SimulatedDrone
from hardware.mavlink_drone import MAVLinkDrone


# FastAPI uygulaması
app = FastAPI(
    title="PyreSwarm Mission Control",
    description="Profesyonel Yangın Tespit ve PSO Tabanlı Sürü Drone Yönetim Sistemi",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dizin yolları
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "web", "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "web", "templates")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)
DOCS_DIR = os.path.join(BASE_DIR, "docs")
os.makedirs(DOCS_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/docs", StaticFiles(directory=DOCS_DIR), name="docs")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

from core.metrics_engine import MetricsEngine
metrics_engine = MetricsEngine()

# Görev Yapılandırması Yükleme & Kalıcı Kayıt
CONFIG_PATH = os.path.join(BASE_DIR, "config", "mission_config.json")

def load_mission_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Config] Okuma hatası: {e}")
    return {
        "base_station": {
            "name": "Antalya Manavgat Orman Şefliği İleri Harekat Üssü",
            "lat": 36.8850,
            "lon": 30.7100,
            "alt": 30.0
        },
        "presets": []
    }

def save_mission_config(cfg: dict):
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Config] Kaydetme hatası: {e}")

mission_cfg = load_mission_config()
base_cfg = mission_cfg.get("base_station", {})
default_lat = float(base_cfg.get("lat", 36.8850))
default_lon = float(base_cfg.get("lon", 30.7100))
default_name = str(base_cfg.get("name", "Antalya Manavgat Orman Şefliği İleri Harekat Üssü"))

# Global Sürü Yöneticisi
swarm_mgr = SwarmManager(
    model_path=os.path.join(BASE_DIR, "best.pt"),
    center_lat=default_lat,
    center_lon=default_lon,
    base_name=default_name,
    update_hz=4.0
)

# Başlangıçta gerçekçi çevresel yangın odakları ve arama filosu
def initialize_default_swarm():
    # Üs çevresinde 2 adet gerçekçi duman/yangın odağı
    swarm_mgr.environmental_fires = [
        (swarm_mgr.center_lat + 0.0035, swarm_mgr.center_lon + 0.0040, 0.95),  # Kuzeydoğu odağı
        (swarm_mgr.center_lat - 0.0030, swarm_mgr.center_lon - 0.0025, 0.88),  # Güneybatı odağı
    ]
    for f_lat, f_lon, intensity in swarm_mgr.environmental_fires:
        swarm_mgr.pso._update_fire_cluster(f_lat, f_lon, intensity)

    # 4 Arama Dronu
    offsets = [
        ("ALPHA-01", 0.0015, 0.0010),
        ("BRAVO-02", -0.0015, 0.0015),
        ("CHARLIE-03", 0.0010, -0.0015),
        ("DELTA-04", -0.0010, -0.0010)
    ]

    for name, d_lat, d_lon in offsets:
        drone = SimulatedDrone(
            drone_id=name,
            initial_lat=swarm_mgr.center_lat + d_lat,
            initial_lon=swarm_mgr.center_lon + d_lon,
            initial_alt=40.0,
            fire_targets=list(swarm_mgr.environmental_fires)
        )
        drone.telemetry.is_in_air = True
        drone.telemetry.is_armed = True
        swarm_mgr.register_drone(drone)

    # Örnek bir su birikintisi / göl bölgesini kapatalım
    lake_coords = [
        (swarm_mgr.center_lat + 0.0060, swarm_mgr.center_lon - 0.0040),
        (swarm_mgr.center_lat + 0.0080, swarm_mgr.center_lon - 0.0020),
        (swarm_mgr.center_lat + 0.0070, swarm_mgr.center_lon + 0.0010),
        (swarm_mgr.center_lat + 0.0045, swarm_mgr.center_lon - 0.0010)
    ]
    swarm_mgr.geofence_mgr.add_zone(
        name="Orman Su Kaynağı (Arama Dışı)",
        zone_type=ZoneType.WATER_BODY,
        coordinates=lake_coords,
        zone_id="lake_default"
    )

initialize_default_swarm()
swarm_mgr.start()


# Pydantic Modelleri
class GeofenceAddRequest(BaseModel):
    name: str
    zone_type: str = "fire_extinguished" # fire_extinguished, water_body, no_fly_zone
    coordinates: List[List[float]]       # [[lat, lon], ...]
    min_alt: float = 0.0
    max_alt: float = 500.0


class VolunteerRegisterRequest(BaseModel):
    pilot_name: str
    lat: float
    lon: float
    alt: float = 30.0
    camera_url: Optional[str] = None


class MAVLinkRegisterRequest(BaseModel):
    drone_id: str
    connection_string: str = "udpin:0.0.0.0:14550"
    video_stream_url: Optional[str] = None


class RelocateRequest(BaseModel):
    lat: float
    lon: float
    name: Optional[str] = "Ana Operasyon Üssü"
    regenerate_fires: bool = True
    save_permanent: bool = True


class BaseStationUpdateRequest(BaseModel):
    name: str = "Ana Operasyon Üssü"
    lat: float
    lon: float
    redeploy_drones: bool = True
    save_permanent: bool = True
    regenerate_fires: bool = True


class AddDroneRequest(BaseModel):
    drone_id: Optional[str] = None
    drone_type: str = "simulated"        # simulated, mavlink, volunteer
    spawn_location: str = "base"         # base, map_center, custom
    lat: Optional[float] = None
    lon: Optional[float] = None
    alt: float = 40.0
    pilot_name: Optional[str] = None
    connection_string: Optional[str] = "udpin:0.0.0.0:14550"
    camera_url: Optional[str] = None


class SpawnAtRequest(BaseModel):
    lat: float
    lon: float
    name: Optional[str] = None


class WindRequest(BaseModel):
    speed_ms: float
    direction_deg: float


class AOIRequest(BaseModel):
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float


class FireSpotRequest(BaseModel):
    lat: float
    lon: float
    intensity: float = 0.95


# REST API Uç Noktaları
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/swarm/state")
async def get_state():
    return swarm_mgr.get_swarm_state()


@app.post("/api/mission/start")
async def start_mission():
    swarm_mgr.start_mission()
    return {"status": "success", "message": "PSO Yangın Arama Görevi Başlatıldı"}


@app.post("/api/mission/pause")
async def pause_mission():
    swarm_mgr.pause_mission()
    return {"status": "success", "message": "Görev Duraklatıldı"}


@app.post("/api/mission/rtl")
async def rtl_mission():
    swarm_mgr.return_to_launch_all()
    return {"status": "success", "message": "Tüm Sürüye RTL Komutu Verildi"}


@app.post("/api/geofence/add")
async def add_geofence(req: GeofenceAddRequest):
    try:
        z_type = ZoneType(req.zone_type)
    except ValueError:
        z_type = ZoneType.FIRE_EXTINGUISHED

    coords = [(c[0], c[1]) for c in req.coordinates]
    zone = swarm_mgr.close_zone(
        name=req.name,
        zone_type=z_type,
        coordinates=coords,
        min_alt=req.min_alt,
        max_alt=req.max_alt
    )
    return {"status": "success", "zone_id": zone.id, "name": zone.name}


@app.delete("/api/geofence/{zone_id}")
async def delete_geofence(zone_id: str):
    removed = swarm_mgr.geofence_mgr.remove_zone(zone_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Bölge bulunamadı")
    return {"status": "success", "message": f"{zone_id} kaldırıldı"}


@app.post("/api/swarm/register_volunteer")
async def register_volunteer(req: VolunteerRegisterRequest):
    v = swarm_mgr.register_volunteer(
        pilot_name=req.pilot_name,
        lat=req.lat,
        lon=req.lon,
        alt=req.alt,
        camera_url=req.camera_url
    )
    return {"status": "success", "drone_id": v.drone_id, "pilot_name": v.pilot_name}


@app.get("/api/mission/base")
async def get_base_station():
    cfg = load_mission_config()
    return {
        "status": "success",
        "name": swarm_mgr.base_name,
        "lat": swarm_mgr.center_lat,
        "lon": swarm_mgr.center_lon,
        "presets": cfg.get("presets", [])
    }


@app.post("/api/mission/base")
async def update_base_station(req: BaseStationUpdateRequest):
    swarm_mgr.relocate_swarm(
        new_lat=req.lat,
        new_lon=req.lon,
        base_name=req.name,
        regenerate_fires=req.regenerate_fires
    )
    if req.save_permanent:
        cfg = load_mission_config()
        cfg["base_station"] = {
            "name": req.name,
            "lat": req.lat,
            "lon": req.lon,
            "alt": 30.0
        }
        save_mission_config(cfg)
    return {
        "status": "success",
        "name": swarm_mgr.base_name,
        "lat": swarm_mgr.center_lat,
        "lon": swarm_mgr.center_lon,
        "message": f"Operasyon üssü güncellendi: {req.name}"
    }


@app.post("/api/mission/relocate")
async def relocate_mission(req: RelocateRequest):
    swarm_mgr.relocate_swarm(
        new_lat=req.lat,
        new_lon=req.lon,
        base_name=req.name,
        regenerate_fires=req.regenerate_fires
    )
    if req.save_permanent:
        cfg = load_mission_config()
        cfg["base_station"] = {
            "name": req.name or swarm_mgr.base_name,
            "lat": req.lat,
            "lon": req.lon,
            "alt": 30.0
        }
        save_mission_config(cfg)
    return {"status": "success", "message": f"Sürü yeni üsse taşındı: ({req.lat:.4f}, {req.lon:.4f})"}


@app.post("/api/swarm/add_drone")
async def add_drone_api(req: AddDroneRequest):
    import random
    count = len(swarm_mgr.drones) + 1
    drone_id = req.drone_id.strip() if req.drone_id and req.drone_id.strip() else f"SWARM-{count:02d}"

    # Koordinat belirleme
    if req.spawn_location == "custom" and req.lat is not None and req.lon is not None:
        spawn_lat = req.lat
        spawn_lon = req.lon
    elif req.spawn_location == "map_center" and req.lat is not None and req.lon is not None:
        spawn_lat = req.lat
        spawn_lon = req.lon
    else: # "base"
        jitter_lat = (random.random() - 0.5) * 0.0015
        jitter_lon = (random.random() - 0.5) * 0.0015
        spawn_lat = swarm_mgr.center_lat + jitter_lat
        spawn_lon = swarm_mgr.center_lon + jitter_lon

    d_type = req.drone_type.lower()
    if d_type == "mavlink":
        drone = MAVLinkDrone(
            drone_id=drone_id,
            connection_string=req.connection_string or "udpin:0.0.0.0:14550",
            video_stream_url=req.camera_url
        )
        success = swarm_mgr.register_drone(drone)
        if not success:
            raise HTTPException(status_code=500, detail="MAVLink otopilotuna bağlanılamadı")
    elif d_type == "volunteer":
        v_drone = swarm_mgr.register_volunteer(
            pilot_name=req.pilot_name or "Saha Gönüllüsü",
            lat=spawn_lat,
            lon=spawn_lon,
            alt=req.alt,
            camera_url=req.camera_url
        )
        drone_id = v_drone.drone_id
    else: # simulated
        drone = SimulatedDrone(
            drone_id=drone_id,
            initial_lat=spawn_lat,
            initial_lon=spawn_lon,
            initial_alt=req.alt,
            fire_targets=list(swarm_mgr.environmental_fires)
        )
        drone.telemetry.is_in_air = True
        drone.telemetry.is_armed = True
        swarm_mgr.register_drone(drone)

    return {
        "status": "success",
        "drone_id": drone_id,
        "type": d_type,
        "lat": spawn_lat,
        "lon": spawn_lon,
        "alt": req.alt,
        "message": f"{drone_id} ({d_type.upper()}) başarıyla filoya eklendi ve göreve dahil edildi."
    }


@app.post("/api/swarm/spawn_simulated")
async def spawn_simulated():
    count = len(swarm_mgr.drones) + 1
    new_id = f"SWARM-{count:02d}"
    import random
    d_lat = (random.random() - 0.5) * 0.003
    d_lon = (random.random() - 0.5) * 0.003
    drone = SimulatedDrone(
        drone_id=new_id,
        initial_lat=swarm_mgr.center_lat + d_lat,
        initial_lon=swarm_mgr.center_lon + d_lon,
        initial_alt=swarm_mgr.pso.config.search_altitude,
        fire_targets=list(swarm_mgr.environmental_fires)
    )
    drone.telemetry.is_in_air = True
    drone.telemetry.is_armed = True
    swarm_mgr.register_drone(drone)
    return {"status": "success", "drone_id": new_id}


@app.post("/api/mission/spawn_at")
async def spawn_drone_at(req: SpawnAtRequest):
    drone_name = req.name or f"DRONE-{len(swarm_mgr.drones) + 1:02d}"
    drone = SimulatedDrone(
        drone_id=drone_name,
        initial_lat=req.lat,
        initial_lon=req.lon,
        initial_alt=swarm_mgr.pso.config.search_altitude,
        fire_targets=list(swarm_mgr.environmental_fires)
    )
    drone.telemetry.is_in_air = True
    drone.telemetry.is_armed = True
    swarm_mgr.register_drone(drone)
    return {"status": "success", "drone_id": drone_name, "lat": req.lat, "lon": req.lon}


@app.post("/api/drone/{drone_id}/rtl")
async def drone_rtl_api(drone_id: str):
    ok = swarm_mgr.drone_rtl(drone_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Drone bulunamadı")
    return {"status": "success", "drone_id": drone_id, "message": f"{drone_id} üsse dönüyor"}


@app.post("/api/drone/{drone_id}/land")
async def drone_land_api(drone_id: str):
    ok = swarm_mgr.drone_land(drone_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Drone bulunamadı")
    return {"status": "success", "drone_id": drone_id, "message": f"{drone_id} iniş yapıyor"}


@app.delete("/api/drone/{drone_id}")
async def delete_drone_api(drone_id: str):
    removed = swarm_mgr.remove_drone(drone_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Drone bulunamadı")
    return {"status": "success", "drone_id": drone_id, "message": f"{drone_id} filodan çıkarıldı"}


@app.post("/api/mission/scenario/quick_fire")
async def quick_fire_api():
    import random
    d_lat = (random.random() - 0.5) * 0.007
    d_lon = (random.random() - 0.5) * 0.007
    f_lat = swarm_mgr.center_lat + d_lat
    f_lon = swarm_mgr.center_lon + d_lon
    swarm_mgr.add_manual_fire_spot(f_lat, f_lon, intensity=0.96)
    return {"status": "success", "lat": f_lat, "lon": f_lon, "message": "Hızlı yangın ihbarı oluşturuldu"}


@app.post("/api/mission/set_wind")
async def set_wind_api(req: WindRequest):
    swarm_mgr.set_wind(req.speed_ms, req.direction_deg)
    return {"status": "success", "speed_ms": req.speed_ms, "direction_deg": req.direction_deg}


@app.post("/api/mission/set_aoi")
async def set_aoi_api(req: AOIRequest):
    swarm_mgr.set_aoi(req.min_lat, req.max_lat, req.min_lon, req.max_lon)
    return {"status": "success", "aoi": swarm_mgr.pso.aoi_bounds}


@app.post("/api/mission/add_fire_spot")
async def add_fire_spot_api(req: FireSpotRequest):
    swarm_mgr.add_manual_fire_spot(req.lat, req.lon, req.intensity)
    return {"status": "success", "lat": req.lat, "lon": req.lon}


@app.get("/api/mission/export_report")
async def export_report_api():
    return swarm_mgr.export_incident_report()


@app.post("/api/swarm/register_mavlink")
async def register_mavlink(req: MAVLinkRegisterRequest):
    drone = MAVLinkDrone(
        drone_id=req.drone_id,
        connection_string=req.connection_string,
        video_stream_url=req.video_stream_url
    )
    success = swarm_mgr.register_drone(drone)
    if not success:
        raise HTTPException(status_code=500, detail="MAVLink drone bağlanamadı")
    return {"status": "success", "drone_id": drone.drone_id}


# MJPEG Canlı Video Akışı
def gen_frames(drone_id: str):
    while True:
        frame_bytes = swarm_mgr.get_annotated_frame_jpeg(drone_id)
        if frame_bytes is not None:
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
        import time
        time.sleep(0.1)


@app.get("/api/video_feed/{drone_id}")
async def video_feed(drone_id: str):
    return StreamingResponse(
        gen_frames(drone_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# Metrikler ve Simülasyon Hesaplayıcı API
@app.get("/api/metrics/calculate")
async def calculate_metrics(area_km2: float = 10.0, num_drones: int = 4):
    acr = metrics_engine.get_area_coverage_rate(num_drones=num_drones)
    times = metrics_engine.get_analytical_detection_time(area_km2=area_km2, num_drones=num_drones, confidence_percent=95.0)
    w, l, f_area = metrics_engine.get_ground_footprint()
    return {
        "area_km2": area_km2,
        "num_drones": num_drones,
        "footprint": {
            "width_m": round(w, 1),
            "length_m": round(l, 1),
            "area_m2": round(f_area, 1)
        },
        "coverage_rate": acr,
        "detection_times": times
    }


# WebSocket Telemetri Akışı
@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            state = swarm_mgr.get_swarm_state()
            await websocket.send_json(state)
            await asyncio.sleep(0.25)  # 4 Hz güncelleme
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WebSocket] Bağlantı kapandı: {e}")
