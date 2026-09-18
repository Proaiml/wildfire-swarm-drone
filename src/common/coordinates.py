"""
PyreSwarm - Koordinat Dönüşüm ve Coğrafi Metrik Katmanı (Coordinate Frame Layer)
WGS84 Jeodezik (Enlem/Boylam/İrtifa) ile Yerel Metrik ENU (East-North-Up) teğet düzlem dönüşümleri.
Açısal bozulmaları ortadan kaldırarak fiziksel hız, ayrılma ve optimizasyon hesaplamalarını metrik uzayda yürütür.
"""

import math
from typing import Tuple, List, Optional


# WGS84 Elipsoid Sabitleri [MANUFACTURER_SPEC]
WGS84_A = 6378137.0          # Yarı-büyük eksen (Ekvatoral yarıçap, metre)
WGS84_F = 1.0 / 298.257223563 # Basıklık (Flattening)
WGS84_B = WGS84_A * (1.0 - WGS84_F) # Yarı-küçük eksen (Kutupsal yarıçap, metre)
WGS84_E_SQ = 2.0 * WGS84_F - WGS84_F ** 2 # Birinci eksantriklik karesi


def geodetic_to_enu(
    lat: float,
    lon: float,
    alt: float,
    ref_lat: float,
    ref_lon: float,
    ref_alt: float = 0.0
) -> Tuple[float, float, float]:
    """
    WGS84 Jeodezik koordinatları (lat, lon, alt) belirtilen referans noktasına göre
    Yerel Metrik ENU (Doğu, Kuzey, Yukarı - metre) koordinatlarına dönüştürür.
    [THEORETICAL_BOUND]
    """
    phi = math.radians(lat)
    lam = math.radians(lon)
    phi_0 = math.radians(ref_lat)
    lam_0 = math.radians(ref_lon)

    # Eğrilik yarıçapı
    sin_phi_0 = math.sin(phi_0)
    cos_phi_0 = math.cos(phi_0)
    n_0 = WGS84_A / math.sqrt(1.0 - WGS84_E_SQ * sin_phi_0 ** 2)

    # Yerel düz teğet aproksimasyonu (Yerel operasyon alanları < 100 km için hata < 0.05%)
    d_phi = phi - phi_0
    d_lam = lam - lam_0

    # Metrik bileşenler
    east = d_lam * n_0 * cos_phi_0
    m_0 = (WGS84_A * (1.0 - WGS84_E_SQ)) / ((1.0 - WGS84_E_SQ * sin_phi_0 ** 2) ** 1.5)
    north = d_phi * m_0
    up = alt - ref_alt

    return round(east, 3), round(north, 3), round(up, 3)


def enu_to_geodetic(
    east: float,
    north: float,
    up: float,
    ref_lat: float,
    ref_lon: float,
    ref_alt: float = 0.0
) -> Tuple[float, float, float]:
    """
    Yerel Metrik ENU (Doğu, Kuzey, Yukarı - metre) koordinatlarını
    WGS84 Jeodezik koordinatlarına (enlem, boylam, irtifa) geri dönüştürür.
    [THEORETICAL_BOUND]
    """
    phi_0 = math.radians(ref_lat)
    sin_phi_0 = math.sin(phi_0)
    cos_phi_0 = math.cos(phi_0)
    n_0 = WGS84_A / math.sqrt(1.0 - WGS84_E_SQ * sin_phi_0 ** 2)
    m_0 = (WGS84_A * (1.0 - WGS84_E_SQ)) / ((1.0 - WGS84_E_SQ * sin_phi_0 ** 2) ** 1.5)

    d_phi = north / m_0
    d_lam = east / (n_0 * cos_phi_0) if abs(cos_phi_0) > 1e-7 else 0.0

    lat = ref_lat + math.degrees(d_phi)
    lon = ref_lon + math.degrees(d_lam)
    alt = ref_alt + up

    return round(lat, 7), round(lon, 7), round(alt, 2)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    İki WGS84 koordinatı arasındaki büyük daire (küresel zemin) mesafesini metre cinsinden hesaplar.
    [THEORETICAL_BOUND]
    """
    r = 6371000.0  # Ortalama Dünya yarıçapı (metre)
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lam = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lam / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def enu_distance_2d(e1: float, n1: float, e2: float, n2: float) -> float:
    """Yerel ENU metrik uzayında iki nokta arası 2D Öklid mesafesi (metre)."""
    return math.hypot(e2 - e1, n2 - n1)


def enu_distance_3d(e1: float, n1: float, u1: float, e2: float, n2: float, u2: float) -> float:
    """Yerel ENU metrik uzayında iki nokta arası 3D Öklid mesafesi (metre)."""
    return math.sqrt((e2 - e1) ** 2 + (n2 - n1) ** 2 + (u2 - u1) ** 2)


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Nokta 1'den Nokta 2'ye doğru seyir açısını (azimut / bearing - derece [0, 360)) hesaplar."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lam = math.radians(lon2 - lon1)

    y = math.sin(delta_lam) * math.cos(phi2)
    x = (math.cos(phi1) * math.sin(phi2) -
         math.sin(phi1) * math.cos(phi2) * math.cos(delta_lam))

    brng = math.degrees(math.atan2(y, x))
    return (brng + 360.0) % 360.0
