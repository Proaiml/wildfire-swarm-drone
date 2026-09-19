"""
PyreSwarm - Web Görev Kontrol Merkezi (Web Mission Control GCS)
FastAPI tabanlı REST API, MJPEG video akışı ve gerçek zamanlı WebSocket telemetrisi.
"""

import os
import asyncio
import json
from typing import List, Optional, Literal, Annotated
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Response, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field, ConfigDict, model_validator

from core.swarm_manager import SwarmManager
from core.geofence_manager import ZoneType
from hardware.simulated_drone import SimulatedDrone
from hardware.mavlink_drone import MAVLinkDrone


@asynccontextmanager
async def lifespan(app):
    swarm_mgr.start()
    yield
    swarm_mgr.stop()

# FastAPI uygulaması
app = FastAPI(lifespan=lifespan,
    title="PyreSwarm Mission Control",
    description="Profesyonel Yangın Tespit ve PSO Tabanlı Sürü Drone Yönetim Sistemi",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def guard_mutations(request: Request, call_next):
    from fastapi.responses import JSONResponse
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            return JSONResponse(status_code=403, content={"detail": "Çapraz kaynaklı kontrol isteği reddedildi"})
    return await call_next(request)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"])

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
        drone.telemetry.is_in_air = drone.telemetry.alt > 0
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


# Pydantic Modelleri
Latitude = Annotated[float, Field(ge=-85, le=85, allow_inf_nan=False)]
Longitude = Annotated[float, Field(ge=-180, le=180, allow_inf_nan=False)]
Altitude = Annotated[float, Field(ge=0, le=120, allow_inf_nan=False)]

class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

class Capabilities(APIModel):
    max_speed_ms: float = Field(default=10, ge=1, le=14)
    max_altitude_m: float = Field(default=120, ge=25, le=120)
    camera_hfov_deg: float = Field(default=84, ge=20, le=120)
    search_altitude_m: float = Field(default=60, ge=25, le=120)

    @model_validator(mode="after")
    def within_limits(self):
        if self.search_altitude_m > self.max_altitude_m:
            raise ValueError("Arama irtifası drone sınırını aşamaz")
        return self

class GeofenceAddRequest(APIModel):
    name: str
    zone_type: ZoneType = ZoneType.FIRE_EXTINGUISHED # fire_extinguished, water_body, no_fly_zone
    coordinates: List[tuple[Latitude, Longitude]] = Field(min_length=3, max_length=200) #       # [[lat, lon], ...]
    min_alt: float = Field(default=0, ge=0, le=500)
    max_alt: float = Field(default=500, ge=0, le=500)


class VolunteerRegisterRequest(APIModel):
    capabilities: Capabilities = Field(default_factory=Capabilities)
    pilot_name: str
    lat: Latitude
    lon: Longitude
    alt: Altitude = 30.0
    camera_url: Optional[str] = None


class MAVLinkRegisterRequest(APIModel):
    drone_id: str = Field(min_length=1, max_length=48, pattern=r"^[A-Za-z0-9_-]+$")
    connection_string: str = "udpin:0.0.0.0:14550"
    video_stream_url: Optional[str] = None


class RelocateRequest(APIModel):
    lat: Latitude
    lon: Longitude
    name: Optional[str] = "Ana Operasyon Üssü"
    regenerate_fires: bool = True
    save_permanent: bool = True


class BaseStationUpdateRequest(APIModel):
    name: str = "Ana Operasyon Üssü"
    lat: Latitude
    lon: Longitude
    redeploy_drones: bool = True
    save_permanent: bool = True
    regenerate_fires: bool = True


class AddDroneRequest(APIModel):
    capabilities: Capabilities = Field(default_factory=Capabilities)
    drone_id: Optional[str] = Field(default=None, max_length=48, pattern=r"^[A-Za-z0-9_-]+$")
    drone_type: Literal["simulated", "mavlink", "volunteer"] = "simulated"        # simulated, mavlink, volunteer
    spawn_location: str = "base"         # base, map_center, custom
    lat: Optional[Latitude] = None
    lon: Optional[Longitude] = None
    alt: Altitude = 40.0
    pilot_name: Optional[str] = None
    connection_string: Optional[str] = "udpin:0.0.0.0:14550"
    camera_url: Optional[str] = None


class SpawnAtRequest(APIModel):
    lat: Latitude
    lon: Longitude
    name: Optional[str] = None


class WindRequest(APIModel):
    speed_ms: float = Field(ge=0, le=30)
    direction_deg: float = Field(ge=0, le=360)


class AOIRequest(APIModel):
    min_lat: Latitude
    max_lat: Latitude
    min_lon: Longitude
    max_lon: Longitude

    @model_validator(mode="after")
    def check_bounds(self):
        if self.min_lat >= self.max_lat or self.min_lon >= self.max_lon:
            raise ValueError("AOI köşeleri sıralı ve farklı olmalı")
        if self.max_lat-self.min_lat > .2 or self.max_lon-self.min_lon > .2:
            raise ValueError("Yerel operasyon alanı en fazla 0.2 derece olabilir")
        return self


class FireSpotRequest(APIModel):
    lat: Latitude
    lon: Longitude
    intensity: float = Field(default=.95, ge=0, le=1)


class MissionKindRequest(APIModel):
    kind: Literal["fire", "sar"]

class IncidentStatusRequest(APIModel):
    status: Literal["confirmed", "dismissed", "resolved"]

class VolunteerTelemetryRequest(APIModel):
    captured_at: float = Field(gt=0, description="UTC Unix seconds at actual drone measurement")
    lat: Latitude
    lon: Longitude
    alt: Altitude
    battery: float = Field(ge=0, le=100)

@app.exception_handler(ValueError)
async def invalid_operation(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=409, content={"detail": str(exc)})

@app.post("/api/mission/kind")
async def set_mission_kind(req: MissionKindRequest):
    swarm_mgr.set_mission_kind(req.kind)
    return {"status": "success", "kind": req.kind}

@app.post("/api/mission/scenario/target")
async def scenario_target(req: FireSpotRequest):
    swarm_mgr.add_scenario_target(req.lat, req.lon, req.intensity)
    return {"status": "success", "source": "hidden_simulation_truth"}

@app.post("/api/incidents/report")
async def report_candidate(req: FireSpotRequest):
    return swarm_mgr.record_candidate(req.lat, req.lon, req.intensity)

@app.post("/api/incidents/{incident_id}/status")
async def incident_status(incident_id: str, req: IncidentStatusRequest):
    try:
        return swarm_mgr.update_incident(incident_id, req.status)
    except KeyError:
        raise HTTPException(404, "Olay bulunamadı")

@app.post("/api/volunteer/{drone_id}/telemetry")
async def volunteer_telemetry(drone_id: str, req: VolunteerTelemetryRequest):
    from hardware.volunteer_bridge import VolunteerDrone
    with swarm_mgr._lock:
        drone = swarm_mgr.drones.get(drone_id)
        if not isinstance(drone, VolunteerDrone):
            raise HTTPException(404, "Gönüllü bulunamadı")
        drone.update_from_external(req.lat, req.lon, req.alt, req.battery, req.captured_at)
    return {"status": "success"}

@app.get("/api/volunteer/{drone_id}/guidance")
async def volunteer_guidance(drone_id: str):
    from hardware.volunteer_bridge import VolunteerDrone
    import time
    with swarm_mgr._lock:
        drone = swarm_mgr.drones.get(drone_id)
        if not isinstance(drone, VolunteerDrone):
            raise HTTPException(404, "Gönüllü bulunamadı")
        fresh = time.time()-drone.telemetry.last_heartbeat <= 3
        eligible = fresh and drone.telemetry.battery_percentage > 20 and drone.telemetry.alt > 1 and drone_id in swarm_mgr.pso.waypoints
        guidance = drone.get_guidance_command() if eligible and swarm_mgr.is_mission_active else None
        return {"advisory_only": True, "telemetry_fresh": fresh, "guidance": guidance,
                "waypoint": swarm_mgr.pso.waypoints.get(drone_id) if guidance else None}

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
        raise HTTPException(422, "Geçersiz alan türü")

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
    v.capabilities.update(req.capabilities.model_dump())
    return {"status": "success", "drone_id": v.drone_id, "pilot_name": v.pilot_name, "advisory_only": True}


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
    if not req.redeploy_drones:
        with swarm_mgr._lock:
            swarm_mgr.center_lat, swarm_mgr.center_lon, swarm_mgr.base_name = req.lat, req.lon, req.name
    else:
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
        success = await asyncio.to_thread(swarm_mgr.register_drone, drone)
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
        drone.telemetry.is_in_air = drone.telemetry.alt > 0
        drone.telemetry.is_armed = True
        drone.capabilities.update(req.capabilities.model_dump())
        swarm_mgr.register_drone(drone)

    swarm_mgr.drones[drone_id].capabilities.update(req.capabilities.model_dump())
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
    swarm_mgr.add_scenario_target(f_lat, f_lon, confidence=0.96)
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
    success = await asyncio.to_thread(swarm_mgr.register_drone, drone)
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
    if drone_id not in swarm_mgr.drones:
        raise HTTPException(404, "Drone bulunamadı")
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
