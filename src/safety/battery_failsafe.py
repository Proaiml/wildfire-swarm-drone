"""
PyreSwarm - Batarya ve Enerji Güvenlik Katmanı (Battery & Energy Failsafe)
Fiziksel 4S LiPo batarya deşarj eğrisi, seyir/asılı kalma (hover) güç modeli ve
otonom Geri Dönüş (Return to Launch - RTL) rezerv kontrolü.
[MANUFACTURER_SPEC / SIMULATED]
"""

import math
from typing import Tuple, Dict, Any
from src.drones.state import DroneState, DroneMode, DroneHealth


class BatteryEnergyModel:
    """
    Drone batarya tüketimini ve güvenli dönüş menzilini hesaplayan güvenlik denetleyicisi.
    """

    def __init__(
        self,
        nominal_capacity_mah: float = 5000.0,
        voltage_nominal: float = 14.8,       # 4S LiPo nominal voltaj
        voltage_full: float = 16.8,          # Tam şarj (4.2V/hücre)
        voltage_empty: float = 13.6,         # Boş eşiği (3.4V/hücre)
        power_hover_w: float = 220.0,        # Asılı kalma gücü (Watt)
        power_cruise_w: float = 180.0,       # Seyir gücü (Watt)
        cruise_speed_ms: float = 12.0,       # Seyir hızı (m/s)
        safety_margin_percent: float = 20.0, # Asgari rezerv yüzdesi
        landing_time_sec: float = 30.0,      # İniş süresi tahmini (saniye)
        meters_per_degree: float = 111139.0
    ):
        self.capacity_mah = nominal_capacity_mah
        self.v_nominal = voltage_nominal
        self.v_full = voltage_full
        self.v_empty = voltage_empty
        self.p_hover = power_hover_w
        self.p_cruise = power_cruise_w
        self.cruise_speed = cruise_speed_ms
        self.reserve_pct = safety_margin_percent
        self.landing_time = landing_time_sec
        self.meters_per_degree = meters_per_degree

        # Toplam teorik enerji kapasitesi (Joule = Watt * Saniye)
        # E = (mAh / 1000) * V * 3600
        self.total_energy_joules = (self.capacity_mah / 1000.0) * self.v_nominal * 3600.0
        # Metre başına harcanan enerji (J/m) = P_cruise / v
        self.joules_per_meter = self.p_cruise / self.cruise_speed

    def update_drone_battery_simulation(
        self,
        drone: DroneState,
        dt_seconds: float,
        is_moving: bool = True
    ) -> float:
        """
        Simülasyon adımında tüketilen enerjiyi batarya yüzdesinden düşer.
        Döndürür: Güncel batarya yüzdesi [0.0, 100.0]
        """
        if not drone.is_in_air:
            return drone.battery_percentage

        power = self.p_cruise if is_moving else self.p_hover
        energy_spent_joules = power * dt_seconds

        percent_drop = (energy_spent_joules / self.total_energy_joules) * 100.0
        drone.battery_percentage = max(0.0, drone.battery_percentage - percent_drop)

        # Voltaj hesaplaması (Lineerlaştırılmış deşarj eğrisi)
        ratio = drone.battery_percentage / 100.0
        drone.battery_voltage = round(self.v_empty + (self.v_full - self.v_empty) * ratio, 2)

        # Bayrak güncellemeleri
        drone.is_low_battery = drone.battery_percentage <= self.reserve_pct
        drone.is_critical_battery = drone.battery_percentage <= 12.0

        if drone.is_critical_battery:
            drone.health = DroneHealth.CRITICAL_BATTERY

        return drone.battery_percentage

    def calculate_energy_to_point(
        self,
        from_lat: float,
        from_lon: float,
        to_lat: float,
        to_lon: float
    ) -> float:
        """İki nokta arası seyahat için gerekli tahmini enerjiyi (Joule) hesaplar."""
        dx = (to_lon - from_lon) * self.meters_per_degree * math.cos(math.radians(from_lat))
        dy = (to_lat - from_lat) * self.meters_per_degree
        dist_m = math.hypot(dx, dy)
        return dist_m * self.joules_per_meter

    def evaluate_rth_requirement(self, drone: DroneState) -> Tuple[bool, float, Dict[str, Any]]:
        """
        Drone'un üsse dönebilmesi için gereken asgari enerjiyi hesaplar.
        Eğer kalan enerji <= (Dönüş Enerjisi + İniş Enerjisi + Rezerv) ise derhal RTL zorunludur!
        Döndürür: (must_return_now, remaining_flight_time_sec, debug_dict)
        """
        # 1. Kalan toplam enerji (Joule)
        remaining_energy_j = (drone.battery_percentage / 100.0) * self.total_energy_joules

        # 2. Eve dönüş enerjisi
        energy_to_home_j = self.calculate_energy_to_point(
            drone.lat, drone.lon, drone.home_lat, drone.home_lon
        )

        # 3. İniş ve asılı kalma payı (30 sn)
        landing_energy_j = self.landing_time * self.p_hover

        # 4. Güvenlik rezervi (Örn: %15)
        reserve_energy_j = (self.reserve_pct / 100.0) * self.total_energy_joules

        # Toplam zorunlu asgari enerji barajı
        required_minimum_j = energy_to_home_j + landing_energy_j + reserve_energy_j

        must_return = remaining_energy_j <= required_minimum_j

        remaining_time_sec = remaining_energy_j / max(1.0, self.p_cruise)

        info = {
            "remaining_energy_joules": round(remaining_energy_j, 1),
            "energy_to_home_joules": round(energy_to_home_j, 1),
            "reserve_energy_joules": round(reserve_energy_j, 1),
            "battery_percent": round(drone.battery_percentage, 1),
            "must_return_home": must_return
        }

        return must_return, round(remaining_time_sec, 1), info
