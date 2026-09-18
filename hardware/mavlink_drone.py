"""
PyreSwarm - MAVLink Donanım Sürücüsü (MAVLink Hardware Driver)
Pixhawk / PX4 / ArduPilot otopilotlu profesyonel endüstriyel drone'lar ile iletişim sağlar.
"""

import time
import math
import threading
from typing import Optional
import numpy as np
import cv2

try:
    from pymavlink import mavutil
    MAVLINK_AVAILABLE = True
except ImportError:
    MAVLINK_AVAILABLE = False

from hardware.drone_base import BaseDrone, DroneMode, DroneType, DroneTelemetry


class MAVLinkDrone(BaseDrone):
    """
    Gerçek MAVLink otopilotuna (SITL veya Fiziksel Drone) bağlanan profesyonel sürücü.
    """

    def __init__(
        self,
        drone_id: str,
        connection_string: str = "udpin:0.0.0.0:14550",
        video_stream_url: Optional[str] = None
    ):
        super().__init__(drone_id=drone_id, drone_type=DroneType.MAVLINK)
        self.connection_string = connection_string
        self.video_stream_url = video_stream_url
        self.master = None
        self._running = False
        self._thread = None
        self._cap = None

        if self.video_stream_url:
            self._init_video_capture()

    def _init_video_capture(self):
        try:
            self._cap = cv2.VideoCapture(self.video_stream_url)
        except Exception as e:
            print(f"[{self.drone_id}] Video akışı açılamadı: {e}")

    def connect(self) -> bool:
        if not MAVLINK_AVAILABLE:
            print(f"[{self.drone_id}] HATA: pymavlink kurulu değil!")
            return False

        try:
            print(f"[{self.drone_id}] MAVLink bağlantısı kuruluyor: {self.connection_string}...")
            self.master = mavutil.mavlink_connection(self.connection_string)
            self.master.wait_heartbeat(timeout=5)
            print(f"[{self.drone_id}] MAVLink Heartbeat alındı! Hedef Sistem: {self.master.target_system}")

            self._running = True
            self._thread = threading.Thread(target=self._telemetry_loop, daemon=True)
            self._thread.start()

            self.mode = DroneMode.ARMED if self.telemetry.is_armed else DroneMode.IDLE
            self.telemetry.mode = self.mode
            return True
        except Exception as e:
            print(f"[{self.drone_id}] MAVLink bağlantı hatası: {e}")
            return False

    def disconnect(self):
        self._running = False
        if self._cap:
            self._cap.release()
        if self.master:
            self.master.close()
        self.mode = DroneMode.DISCONNECTED
        self.telemetry.mode = self.mode

    def _telemetry_loop(self):
        """MAVLink mesajlarını sürekli dinler ve telemetriyi günceller."""
        while self._running and self.master:
            try:
                msg = self.master.recv_match(
                    type=['HEARTBEAT', 'GLOBAL_POSITION_INT', 'SYS_STATUS', 'ATTITUDE'],
                    blocking=True,
                    timeout=1.0
                )
                if not msg:
                    continue

                msg_type = msg.get_type()

                if msg_type == 'HEARTBEAT':
                    is_armed = bool(msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
                    self.telemetry.is_armed = is_armed
                    self.telemetry.last_heartbeat = time.time()

                elif msg_type == 'GLOBAL_POSITION_INT':
                    # lat, lon (degE7), alt (mm), relative_alt (mm), vx, vy, vz (cm/s), hdg (cdeg)
                    self.telemetry.lat = msg.lat / 1e7
                    self.telemetry.lon = msg.lon / 1e7
                    self.telemetry.alt = max(0.0, msg.relative_alt / 1000.0)
                    self.telemetry.vx = msg.vx / 100.0
                    self.telemetry.vy = msg.vy / 100.0
                    self.telemetry.vz = msg.vz / 100.0
                    self.telemetry.speed = math.hypot(self.telemetry.vx, self.telemetry.vy)
                    self.telemetry.heading = msg.hdg / 100.0
                    self.telemetry.is_in_air = self.telemetry.alt > 1.0

                elif msg_type == 'SYS_STATUS':
                    self.telemetry.battery_percentage = max(0.0, min(100.0, msg.battery_remaining))

            except Exception as e:
                time.sleep(0.05)

    def arm(self) -> bool:
        if not self.master:
            return False
        self.master.arducopter_arm()
        return True

    def disarm(self) -> bool:
        if not self.master:
            return False
        self.master.arducopter_disarm()
        return True

    def takeoff(self, target_alt: float = 30.0) -> bool:
        if not self.master:
            return False
        # MAV_CMD_NAV_TAKEOFF
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            0,
            0, 0, 0, 0, 0, 0,
            target_alt
        )
        self.mode = DroneMode.TAKEOFF
        self.telemetry.mode = self.mode
        return True

    def land(self) -> bool:
        if not self.master:
            return False
        self.master.set_mode_rtl()
        self.mode = DroneMode.LANDING
        self.telemetry.mode = self.mode
        return True

    def return_to_launch(self) -> bool:
        if not self.master:
            return False
        self.master.set_mode_rtl()
        self.mode = DroneMode.RTL
        self.telemetry.mode = self.mode
        return True

    def send_velocity(self, vx: float, vy: float, vz: float, yaw_rate: float = 0.0) -> bool:
        """
        SET_POSITION_TARGET_LOCAL_NED mesajı ile hız vektörü gönderir.
        vx: Kuzey (m/s), vy: Doğu (m/s), vz: Aşağı (m/s - negatif yukarı)
        """
        if not self.master:
            return False

        type_mask = int(0b0000111111000111)  # Sadece vx, vy, vz ve yaw_rate aktif

        self.master.mav.set_position_target_local_ned_send(
            0,                                     # time_boot_ms
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_FRAME_LOCAL_NED,
            type_mask,
            0, 0, 0,                               # x, y, z (kullanılmıyor)
            vy, vx, -vz,                           # MAVLink NED formatı: Kuzey, Doğu, Aşağı
            0, 0, 0,                               # ax, ay, az
            0, math.radians(yaw_rate)              # yaw, yaw_rate
        )
        return True

    def goto_coordinate(self, lat: float, lon: float, alt: float, speed: float = 8.0) -> bool:
        if not self.master:
            return False
        self.master.mav.mission_item_send(
            self.master.target_system,
            self.master.target_component,
            0,
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
            mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
            2, 0, 0, 0, 0, 0,
            lat, lon, alt
        )
        return True

    def get_telemetry(self) -> DroneTelemetry:
        return self.telemetry

    def get_camera_frame(self) -> Optional[np.ndarray]:
        if self._cap and self._cap.isOpened():
            ret, frame = self._cap.read()
            if ret:
                return frame
        return None
