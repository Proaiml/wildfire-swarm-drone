"""
PyreSwarm - MAVLink sürücüsü (ArduPilot / PX4)

Bir drone'u sürüye katmanın güvenli yolu:

1. Bağlan  : heartbeat beklenir, otopilot türü (ArduPilot / PX4) ve sistem kimliği okunur.
             Hub saniyede bir GCS heartbeat'i gönderir; hub koparsa otopilotun kendi
             "GCS failsafe" davranışı (ArduPilot: FS_GCS_ENABLE, genelde RTL) devreye girer.
2. Gözle   : telemetri (konum, hız, batarya, GPS, EKF, uçuş modu) sürekli okunur.
             Bu aşamada hub drone'a HİÇBİR hareket komutu göndermez.
3. Denetle : uçuş öncesi kontrol (preflight) - bağlantı, GPS 3D fix ve uydu, EKF,
             batarya, ev konumu, GCS failsafe ayarı.
4. Kontrol : operatör "Hub kontrolüne al" dediğinde (ve yalnızca kontroller geçtiyse)
             hub GUIDED moduna alır, motorları kollar, kalkış yaptırır ve PSO hız
             komutlarını en az 2 Hz gönderir. ArduPilot, 3 s yeni hız komutu gelmezse
             aracı durdurur.
5. Pilot   : pilot kumandadan modu değiştirirse (LOITER, RTL, LAND ...) hub bunu
             heartbeat'ten anlar ve kontrolü ANINDA bırakır ("pilot_override").

Hız komutları yalnızca kontrol verilmiş ve araç GUIDED modundayken gönderilir.
RTL ve iniş (LAND) güvenlik komutlarıdır; kontrol verilmemiş araca da gönderilebilir.

Doğrulama durumu: ArduPilot Copter 4.5 SITL ile (Docker, tools/sitl) test edildi.
PX4 için telemetri, RTL ve iniş vardır; hub kontrolü PX4'te henüz doğrulanmadığından kapalıdır.
Fiziksel uçuş kabul testi (kontrollü saha, tek araç sonra çoklu araç) operatörün sorumluluğundadır.
"""

import collections
import math
import threading
import time
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

try:
    from pymavlink import mavutil
    MAVLINK_AVAILABLE = True
except ImportError:  # pragma: no cover
    mavutil = None
    MAVLINK_AVAILABLE = False

from hardware.drone_base import BaseDrone, DroneMode, DroneType

GUIDED_MODES = {"ardupilot": "GUIDED", "px4": "OFFBOARD"}
HOLD_MODES = {"ardupilot": "LOITER", "px4": "LOITER"}
EKF_REQUIRED = 0x0001 | 0x0002 | 0x0010          # attitude | horizontal velocity | absolute horizontal position


class MAVLinkDrone(BaseDrone):
    HEARTBEAT_TIMEOUT_S = 3.0
    MIN_GPS_SATS = 6
    MIN_BATTERY = 40.0

    def __init__(self, drone_id: str, connection_string: str = "udpin:0.0.0.0:14550",
                 video_stream_url: Optional[str] = None, target_system: Optional[int] = None,
                 camera_source=None):
        super().__init__(drone_id=drone_id, drone_type=DroneType.MAVLINK)
        self.connection_string = connection_string
        self.video_stream_url = video_stream_url
        self.target_system = target_system
        self.camera_source = camera_source            # callable(telemetry, capabilities) -> frame (drills)
        self.master = None
        self._running = False
        self._threads: List[threading.Thread] = []
        self._send_lock = threading.Lock()
        self._cap = None
        # otopilot durumu
        self.autopilot = "unknown"
        self.flight_mode = ""
        self.gps_fix = 0
        self.gps_sats = 0
        self.ekf_flags = None
        self.home: Optional[tuple] = None
        self.battery_voltage = 0.0
        self.params: Dict[str, float] = {}
        self.status_text = collections.deque(maxlen=12)
        self.acks: Dict[int, tuple] = {}
        # hub kontrol durumu
        self.control_enabled = False
        self.control_state = "observe"   # observe | ready | takeoff | mission | hold | rtl | landing | pilot_override | lost
        self._expected_mode: Optional[str] = None
        self.last_velocity_sent = 0.0
        if self.video_stream_url:
            self._init_video_capture()

    # ------------------------------------------------------------------ bağlantı
    def _init_video_capture(self):
        try:
            self._cap = cv2.VideoCapture(self.video_stream_url)
        except Exception as exc:  # noqa: BLE001
            print(f"[{self.drone_id}] Video akışı açılamadı: {exc}")

    def connect(self, timeout: float = 10.0) -> bool:
        if not MAVLINK_AVAILABLE:
            print(f"[{self.drone_id}] HATA: pymavlink kurulu değil")
            return False
        try:
            print(f"[{self.drone_id}] MAVLink bağlantısı: {self.connection_string}")
            self.master = mavutil.mavlink_connection(self.connection_string, source_system=255,
                                                     source_component=190, autoreconnect=True)
            end = time.time() + timeout
            hb = None
            while time.time() < end:
                msg = self.master.recv_match(type="HEARTBEAT", blocking=True, timeout=1.0)
                if msg is None or msg.type == mavutil.mavlink.MAV_TYPE_GCS:
                    continue
                if self.target_system and msg.get_srcSystem() != self.target_system:
                    continue
                hb = msg
                break
            if hb is None:
                self.disconnect()
                return False
            self.target_system = hb.get_srcSystem()
            self.master.target_system = self.target_system
            self.master.target_component = hb.get_srcComponent()
            self.autopilot = {mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA: "ardupilot",
                              mavutil.mavlink.MAV_AUTOPILOT_PX4: "px4"}.get(hb.autopilot, "other")
            self._on_heartbeat(hb)
            self._running = True
            for target in (self._receive_loop, self._gcs_heartbeat_loop):
                thread = threading.Thread(target=target, daemon=True, name=f"{self.drone_id}-{target.__name__}")
                thread.start()
                self._threads.append(thread)
            self._request_streams()
            self._request_params(("FS_GCS_ENABLE", "FS_GCS_TIMEOUT", "RTL_ALT", "FENCE_ENABLE", "NAV_DLL_ACT"))
            print(f"[{self.drone_id}] Heartbeat alındı: sistem {self.target_system}, {self.autopilot}, mod {self.flight_mode}")
            return True
        except Exception as exc:  # noqa: BLE001
            print(f"[{self.drone_id}] MAVLink bağlantı hatası: {exc}")
            self.disconnect()
            return False

    def disconnect(self):
        self._running = False
        self.control_enabled = False
        if self._cap:
            self._cap.release()
        if self.master:
            try:
                self.master.close()
            except Exception:  # noqa: BLE001
                pass
        self.mode = DroneMode.DISCONNECTED
        self.telemetry.mode = self.mode

    def _send(self, fn, *args):
        with self._send_lock:
            return fn(*args)

    def _request_streams(self):
        m = mavutil.mavlink
        for msg_id, hz in ((m.MAVLINK_MSG_ID_GLOBAL_POSITION_INT, 5), (m.MAVLINK_MSG_ID_SYS_STATUS, 1),
                           (m.MAVLINK_MSG_ID_GPS_RAW_INT, 1), (m.MAVLINK_MSG_ID_EKF_STATUS_REPORT, 1),
                           (m.MAVLINK_MSG_ID_HOME_POSITION, 0.5), (m.MAVLINK_MSG_ID_ATTITUDE, 2)):
            self._command(m.MAV_CMD_SET_MESSAGE_INTERVAL, msg_id, 1e6 / hz, wait=False)
        # eski ArduPilot sürümleri için yedek
        self._send(self.master.mav.request_data_stream_send, self.target_system, self.master.target_component,
                   m.MAV_DATA_STREAM_ALL, 4, 1)
        self._command(m.MAV_CMD_GET_HOME_POSITION, wait=False)

    def _request_params(self, names):
        for name in names:
            self._send(self.master.mav.param_request_read_send, self.target_system, self.master.target_component,
                       name.encode(), -1)

    def _gcs_heartbeat_loop(self):
        while self._running and self.master:
            try:
                self._send(self.master.mav.heartbeat_send, mavutil.mavlink.MAV_TYPE_GCS,
                           mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0)
            except Exception:  # noqa: BLE001
                pass
            time.sleep(1.0)

    # ------------------------------------------------------------------ telemetri
    def _receive_loop(self):
        while self._running and self.master:
            try:
                msg = self.master.recv_match(blocking=True, timeout=0.5)
            except Exception:  # noqa: BLE001
                time.sleep(0.1)
                continue
            if msg is None or msg.get_srcSystem() != self.target_system:
                continue
            kind = msg.get_type()
            try:
                if kind == "HEARTBEAT" and msg.type != mavutil.mavlink.MAV_TYPE_GCS:
                    self._on_heartbeat(msg)
                elif kind == "GLOBAL_POSITION_INT":
                    t = self.telemetry
                    t.lat, t.lon = msg.lat / 1e7, msg.lon / 1e7
                    t.alt = max(0.0, msg.relative_alt / 1000.0)
                    t.vx, t.vy, t.vz = msg.vy / 100.0, msg.vx / 100.0, -msg.vz / 100.0   # NED -> doğu/kuzey/yukarı
                    t.speed = math.hypot(t.vx, t.vy)
                    if msg.hdg != 65535:
                        t.heading = msg.hdg / 100.0
                    t.is_in_air = t.alt > 1.0 and t.is_armed
                elif kind == "SYS_STATUS":
                    if msg.battery_remaining >= 0:
                        self.telemetry.battery_percentage = float(msg.battery_remaining)
                    self.battery_voltage = msg.voltage_battery / 1000.0
                    self.telemetry.is_low_battery = self.telemetry.battery_percentage <= 20
                elif kind == "GPS_RAW_INT":
                    self.gps_fix, self.gps_sats = msg.fix_type, msg.satellites_visible
                    self.telemetry.gps_satellites = msg.satellites_visible
                elif kind == "EKF_STATUS_REPORT":
                    self.ekf_flags = msg.flags
                elif kind == "HOME_POSITION":
                    self.home = (msg.latitude / 1e7, msg.longitude / 1e7)
                elif kind == "PARAM_VALUE":
                    self.params[msg.param_id if isinstance(msg.param_id, str) else msg.param_id.decode()] = msg.param_value
                elif kind == "STATUSTEXT":
                    self.status_text.append((time.time(), msg.text))
                elif kind == "COMMAND_ACK":
                    self.acks[msg.command] = (msg.result, time.time())
            except Exception:  # noqa: BLE001
                continue

    def _on_heartbeat(self, msg):
        self.telemetry.last_heartbeat = time.time()
        self.telemetry.is_armed = bool(msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
        previous, self.flight_mode = self.flight_mode, mavutil.mode_string_v10(msg)
        if not self.telemetry.is_armed:
            self.telemetry.is_in_air = False
        # Pilot devraldı mı? Hub kontrolündeyken beklenmeyen mod değişikliği = pilot müdahalesi
        guided = GUIDED_MODES.get(self.autopilot)
        if self.control_enabled and previous and self.flight_mode != previous \
                and self.flight_mode != self._expected_mode and self.flight_mode != guided:
            self.control_enabled = False
            self.control_state = "pilot_override"
            self.status_text.append((time.time(), f"Pilot kontrolü devraldı: {previous} -> {self.flight_mode}"))
        self._sync_mode()

    def _sync_mode(self):
        fm = self.flight_mode
        if fm in ("RTL", "AUTO_RTL", "SMART_RTL"):
            self.mode = DroneMode.RTL
        elif fm in ("LAND", "AUTO_LAND"):
            self.mode = DroneMode.LANDING
        elif self.control_enabled and self.control_state == "mission":
            self.mode = DroneMode.MISSION_PSO
        elif self.control_enabled and self.control_state == "takeoff":
            self.mode = DroneMode.TAKEOFF
        elif self.telemetry.is_armed:
            self.mode = DroneMode.IN_FLIGHT if self.telemetry.is_in_air else DroneMode.ARMED
        else:
            self.mode = DroneMode.IDLE
        self.telemetry.mode = self.mode

    def link_ok(self) -> bool:
        return self.master is not None and time.time() - self.telemetry.last_heartbeat <= self.HEARTBEAT_TIMEOUT_S

    # ------------------------------------------------------------------ komutlar (ACK ile)
    def _command(self, command, p1=0, p2=0, p3=0, p4=0, p5=0, p6=0, p7=0, wait: bool = True,
                 timeout: float = 3.0) -> bool:
        if not self.master:
            return False
        sent = time.time()
        self.acks.pop(command, None)
        self._send(self.master.mav.command_long_send, self.target_system, self.master.target_component,
                   command, 0, p1, p2, p3, p4, p5, p6, p7)
        if not wait:
            return True
        while time.time() - sent < timeout:
            ack = self.acks.get(command)
            if ack and ack[1] >= sent:
                return ack[0] == mavutil.mavlink.MAV_RESULT_ACCEPTED
            time.sleep(0.05)
        return False

    def set_flight_mode(self, name: str, timeout: float = 4.0) -> bool:
        """Modu değiştirir ve heartbeat'te gerçekten değiştiğini doğrular."""
        if not self.master:
            return False
        mapping = self.master.mode_mapping() or {}
        if name not in mapping:
            self.status_text.append((time.time(), f"Mod desteklenmiyor: {name}"))
            return False
        self._expected_mode = name
        self._send(self.master.set_mode, mapping[name])
        end = time.time() + timeout
        while time.time() < end:
            if self.flight_mode == name:
                return True
            time.sleep(0.05)
        return False

    def arm(self) -> bool:
        ok = self._command(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 1, timeout=5.0)
        end = time.time() + 5.0
        while ok and time.time() < end and not self.telemetry.is_armed:
            time.sleep(0.05)
        return ok and self.telemetry.is_armed

    def disarm(self) -> bool:
        return self._command(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0)

    def takeoff(self, target_alt: float = 30.0) -> bool:
        """GUIDED + arm + NAV_TAKEOFF (yalnızca hub kontrolü verilmişse, ArduPilot)."""
        if not self.control_enabled or self.autopilot != "ardupilot":
            return False
        self.control_state = "takeoff"
        if not self.set_flight_mode("GUIDED"):
            self.control_state = "ready"
            self.status_text.append((time.time(), "GUIDED moduna geçilemedi"))
            return False
        if not self.telemetry.is_armed and not self.arm():
            self.control_state = "ready"
            self.status_text.append((time.time(), "Motorlar kollanamadı (otopilot ön kontrol mesajlarına bakın)"))
            return False
        ok = self._command(mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, p7=float(target_alt), timeout=5.0)
        if not ok:
            self.control_state = "ready"
            self.status_text.append((time.time(), "Kalkış komutu reddedildi"))
        self._sync_mode()
        return ok

    def land(self) -> bool:
        if not self.master:
            return False
        self.control_enabled = False
        self.control_state = "landing"
        self.master.mav.command_long_send(self.target_system, self.master.target_component,
                                          mavutil.mavlink.MAV_CMD_NAV_LAND, 0, 0, 0, 0, 0, 0, 0, 0)
        self.mode = DroneMode.LANDING
        self.telemetry.mode = self.mode
        return True

    def return_to_launch(self) -> bool:
        if not self.master:
            return False
        self.control_enabled = False
        self.control_state = "rtl"
        mapping = self.master.mode_mapping() or {}
        name = "RTL" if "RTL" in mapping else next((n for n in mapping if "RTL" in n), None)
        if name is None:
            return False
        self._expected_mode = name
        self._send(self.master.set_mode, mapping[name])
        self.mode = DroneMode.RTL
        self.telemetry.mode = self.mode
        return True

    def hold(self) -> bool:
        """Kontrolü bırakır ve aracı yerinde tutar (ArduPilot LOITER)."""
        self.control_enabled = False
        self.control_state = "hold"
        name = HOLD_MODES.get(self.autopilot, "LOITER")
        return self.set_flight_mode(name) if self.master else False

    def send_velocity(self, vx: float, vy: float, vz: float, yaw_rate: float = 0.0) -> bool:
        """PSO hız komutu. vx: doğu, vy: kuzey, vz: yukarı (m/s). MAVLink LOCAL_NED'e çevrilir.

        Yalnızca hub kontrolü verilmiş ve araç GUIDED modundayken gönderilir.
        """
        if not self.master or not self.control_enabled:
            return False
        if self.flight_mode and self.flight_mode != GUIDED_MODES.get(self.autopilot, "GUIDED"):
            return False
        type_mask = 0b010111000111     # yalnızca vx, vy, vz ve yaw_rate
        self._send(self.master.mav.set_position_target_local_ned_send,
                   0, self.target_system, self.master.target_component, mavutil.mavlink.MAV_FRAME_LOCAL_NED,
                   type_mask, 0, 0, 0, vy, vx, -vz, 0, 0, 0, 0, math.radians(yaw_rate))
        self.last_velocity_sent = time.time()
        return True

    def goto_coordinate(self, lat: float, lon: float, alt: float, speed: float = 8.0) -> bool:
        if not self.master or not self.control_enabled:
            return False
        type_mask = 0b110111111000     # yalnızca konum
        self._send(self.master.mav.set_position_target_global_int_send,
                   0, self.target_system, self.master.target_component,
                   mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT, type_mask,
                   int(lat * 1e7), int(lon * 1e7), float(alt), 0, 0, 0, 0, 0, 0, 0, 0)
        return True

    # ------------------------------------------------------------------ uçuş öncesi kontrol
    def preflight(self) -> List[Dict[str, Any]]:
        """Hub kontrolüne almadan önce geçmesi gereken kontroller."""
        age = time.time() - self.telemetry.last_heartbeat if self.telemetry.last_heartbeat else None
        fs = self.params.get("FS_GCS_ENABLE")
        ekf_ok = self.ekf_flags is not None and (self.ekf_flags & EKF_REQUIRED) == EKF_REQUIRED
        checks = [
            ("link", "Bağlantı (heartbeat)", age is not None and age <= 2.0,
             "yok" if age is None else f"{age:.1f} s önce"),
            ("autopilot", "Otopilot hub kontrolünü destekliyor", self.autopilot == "ardupilot",
             {"ardupilot": "ArduPilot (SITL ile doğrulandı)", "px4": "PX4: yalnızca telemetri, RTL ve iniş"}
             .get(self.autopilot, self.autopilot)),
            ("gps", "GPS 3D fix ve uydu", self.gps_fix >= 3 and self.gps_sats >= self.MIN_GPS_SATS,
             f"fix {self.gps_fix}, {self.gps_sats} uydu"),
            ("ekf", "EKF konum çözümü", ekf_ok, "hazır" if ekf_ok else "bekleniyor"),
            ("home", "Ev (RTL) konumu", self.home is not None, "kayıtlı" if self.home else "yok"),
            ("battery", f"Batarya en az %{self.MIN_BATTERY:.0f}", self.telemetry.battery_percentage >= self.MIN_BATTERY,
             f"%{self.telemetry.battery_percentage:.0f} ({self.battery_voltage:.1f} V)"),
            ("gcs_failsafe", "Hub bağlantısı koparsa otopilot RTL yapar", self.autopilot != "ardupilot" or (fs or 0) > 0,
             "FS_GCS_ENABLE okunamadı" if fs is None else f"FS_GCS_ENABLE = {fs:.0f}"),
        ]
        return [{"id": i, "label": label, "ok": bool(ok), "detail": detail} for i, label, ok, detail in checks]

    def grant_control(self) -> List[Dict[str, Any]]:
        """Operatör onayı: kontroller geçerse hub bu drone'a komut verebilir."""
        checks = self.preflight()
        if all(c["ok"] for c in checks):
            self.control_enabled = True
            self.control_state = "mission" if self.telemetry.is_in_air and self.flight_mode == "GUIDED" else "ready"
        return checks

    def release_control(self) -> bool:
        """Hub komut göndermeyi keser; araç havadaysa yerinde tutulur."""
        was_flying = self.telemetry.is_in_air
        self.control_enabled = False
        self.control_state = "observe"
        return self.hold() if was_flying else True

    def status(self) -> Dict[str, Any]:
        return {"autopilot": self.autopilot, "system_id": self.target_system, "flight_mode": self.flight_mode,
                "control_state": self.control_state, "control_enabled": self.control_enabled,
                "link_ok": self.link_ok(), "gps_fix": self.gps_fix, "gps_sats": self.gps_sats,
                "messages": [text for _, text in list(self.status_text)[-4:]]}

    # ------------------------------------------------------------------ veri
    def get_telemetry(self):
        return self.telemetry

    def get_camera_frame(self, pose=None) -> Optional[np.ndarray]:
        """pose: algılamada kullanılacak telemetri kopyası; tatbikat kamerası kareyi tam bu pozdan çizer."""
        if self.camera_source is not None:
            return self.camera_source(pose or self.telemetry, self.capabilities)
        if self._cap and self._cap.isOpened():
            ret, frame = self._cap.read()
            if ret:
                return frame
        return None
