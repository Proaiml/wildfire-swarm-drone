"""
PyreSwarm - Web Görev Kontrol Merkezi (Web Mission Control GCS)
FastAPI tabanlı REST API, MJPEG video akışı ve gerçek zamanlı WebSocket telemetrisi.
"""

import os
import asyncio
import json
from typing import List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Response
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

# Global Sürü Yöneticisi
# Varsayılan merkez: Muğla ormanlık alanı (37.0500 N, 28.3200 E)
swarm_mgr = SwarmManager(
    model_path=os.path.join(BASE_DIR, "best.pt"),
    center_lat=37.0500,
    center_lon=28.3200,
    update_hz=4.0
)

# Başlangıçta 4 adet simüle drone ve 2 adet sentetik yangın odağı oluşturalım
def initialize_default_swarm():
    fire_targets = [
        (37.0535, 28.3240, 0.95),  # Kuzeydoğu yangın odağı
        (37.0470, 28.3150, 0.85),  # Güneybatı ikincil yangın odağı
    ]

    # 4 Arama Dronu
    offsets = [
        ("ALPHA-01", 0.002, 0.001),
        ("BRAVO-02", -0.002, 0.002),
        ("CHARLIE-03", 0.001, -0.002),
        ("DELTA-04", -0.001, -0.001)
    ]

    for name, d_lat, d_lon in offsets:
        drone = SimulatedDrone(
            drone_id=name,
            initial_lat=swarm_mgr.center_lat + d_lat,
            initial_lon=swarm_mgr.center_lon + d_lon,
            initial_alt=40.0,
            fire_targets=fire_targets
        )
        drone.telemetry.is_in_air = True
        drone.telemetry.is_armed = True
        swarm_mgr.register_drone(drone)

    # Başlangıçta örnek bir göl bölgesi kapatalım
    lake_coords = [
        (37.0560, 28.3120),
        (37.0580, 28.3150),
        (37.0570, 28.3190),
        (37.0545, 28.3160)
    ]
    swarm_mgr.geofence_mgr.add_zone(
        name="Orman Golu (Arama Disi)",
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


# REST API Uç Noktaları
@app.get("/", response_class=HTMLResponse)
async def index(request: Response):
    return templates.TemplateResponse("index.html", {"request": request})


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


@app.post("/api/swarm/spawn_simulated")
async def spawn_simulated():
    count = len(swarm_mgr.drones) + 1
    new_id = f"SWARM-{count:02d}"
    # Merkeze yakın rastgele konum
    import random
    d_lat = (random.random() - 0.5) * 0.006
    d_lon = (random.random() - 0.5) * 0.006

    fire_targets = [
        (37.0535, 28.3240, 0.95),
        (37.0470, 28.3150, 0.85)
    ]
    drone = SimulatedDrone(
        drone_id=new_id,
        initial_lat=swarm_mgr.center_lat + d_lat,
        initial_lon=swarm_mgr.center_lon + d_lon,
        initial_alt=40.0,
        fire_targets=fire_targets
    )
    drone.telemetry.is_in_air = True
    drone.telemetry.is_armed = True
    swarm_mgr.register_drone(drone)
    return {"status": "success", "drone_id": new_id}


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
