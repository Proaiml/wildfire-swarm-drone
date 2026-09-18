"""
PyreSwarm - YOLOv8 Yangın Algılayıcı Birim Testleri
"""

import os
import cv2
import pytest
from core.fire_detector import FireDetector


def test_detector_initialization():
    detector = FireDetector(model_path="best.pt")
    assert detector.model is not None
    assert 0 in detector.model.names
    assert 1 in detector.model.names


def test_detector_inference_on_sample_images():
    detector = FireDetector(model_path="best.pt")
    
    # Projedeki mana.jpg veya fire.jpg
    test_img_path = "mana.jpg" if os.path.exists("mana.jpg") else "fire.jpg"
    assert os.path.exists(test_img_path), f"Test resmi bulunamadı: {test_img_path}"

    image = cv2.imread(test_img_path)
    assert image is not None

    detections, score, annotated = detector.detect(
        frame=image,
        drone_lat=37.0500,
        drone_lon=28.3200,
        drone_alt=50.0
    )

    # Model en az bir duman veya yangın tespiti yapmalı
    assert len(detections) > 0
    assert score > 0.0
    assert annotated.shape == image.shape

    # İlk tespitin özellikleri
    first_det = detections[0]
    assert first_det.confidence > 0.1
    assert first_det.class_name in ["smoke", "fire"]
    assert first_det.estimated_gps is not None
    assert len(first_det.estimated_gps) == 2


def test_ray_casting_ground_gps():
    detector = FireDetector(model_path="best.pt")
    lat, lon = detector._estimate_ground_gps(
        px=320, py=240, img_w=640, img_h=480,
        lat=37.0500, lon=28.3200, alt=60.0,
        yaw_deg=0.0, pitch_deg=-90.0, hfov_deg=80.0
    )
    # Merkez piksel dikey kamerada tam drone GPS'ini vermelidir
    assert abs(lat - 37.0500) < 1e-4
    assert abs(lon - 28.3200) < 1e-4
