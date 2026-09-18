"""
PyreSwarm - Coğrafi Kısıt ve Bölge Kapatma Birim Testleri
"""

import pytest
from core.geofence_manager import GeofenceManager, ZoneType


def test_geofence_add_and_containment():
    mgr = GeofenceManager()
    
    # 1km x 1km kare bölge
    coords = [
        (37.0500, 28.3200),
        (37.0600, 28.3200),
        (37.0600, 28.3300),
        (37.0500, 28.3300)
    ]
    
    zone = mgr.add_zone(
        name="Test Golu",
        zone_type=ZoneType.WATER_BODY,
        coordinates=coords
    )
    
    assert zone.id in mgr.zones
    assert len(mgr.get_all_zones()) == 1

    # Merkezin içindeyse True dönmeli
    inside, z = mgr.is_point_inside(37.0550, 28.3250)
    assert inside is True
    assert z.id == zone.id

    # Dışındaysa False dönmeli
    outside, _ = mgr.is_point_inside(37.0400, 28.3100)
    assert outside is False


def test_geofence_repulsion_vector():
    mgr = GeofenceManager()
    coords = [
        (37.0500, 28.3200),
        (37.0600, 28.3200),
        (37.0600, 28.3300),
        (37.0500, 28.3300)
    ]
    mgr.add_zone(
        name="No Fly Zone",
        zone_type=ZoneType.NO_FLY_ZONE,
        coordinates=coords,
        safety_margin_meters=50.0
    )

    # Alanın hemen güney dışındaki bir nokta için kuzeye (içeri) değil, güneye doğru itki üretmeli
    dlat, dlon = mgr.calculate_repulsion_vector(37.0499, 28.3250)
    assert dlat < 0  # Güneye doğru negatif dlat


def test_geofence_fitness_penalty():
    mgr = GeofenceManager()
    coords = [
        (37.0500, 28.3200),
        (37.0600, 28.3200),
        (37.0600, 28.3300),
        (37.0500, 28.3300)
    ]
    mgr.add_zone(
        name="Sondurulen Yangin",
        zone_type=ZoneType.FIRE_EXTINGUISHED,
        coordinates=coords
    )

    # Alan içindeki bir nokta için yüksek ceza puanı verilmeli
    penalty_inside = mgr.get_fitness_penalty(37.0550, 28.3250)
    assert penalty_inside >= 500.0

    # Çok uzaktaki nokta için ceza 0 olmalı
    penalty_outside = mgr.get_fitness_penalty(37.0100, 28.2500)
    assert penalty_outside == 0.0
