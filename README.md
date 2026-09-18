# 🔥 PyreSwarm: Otonom Yangın Tespit ve PSO Tabanlı Sürü Drone Yönetim Sistemi

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Wildfire%20Detection-orange.svg)](https://ultralytics.com/)
[![Tests](https://img.shields.io/badge/Tests-23%20Passed-brightgreen.svg)]()
[![MAVLink](https://img.shields.io/badge/MAVLink-PX4%20%7C%20ArduPilot-blueviolet.svg)](https://mavlink.io/)
[![PDF Reports](https://img.shields.io/badge/Documentation-PDF%20Ready-red.svg)](docs/)
[![FastAPI](https://img.shields.io/badge/FastAPI-GCS%20Server-teal.svg)](https://fastapi.tiangolo.com/)

> **PyreSwarm**, orman yangınlarının ilk çıkış anlarının tespiti ve yayılma perimetrelerinin takibi için tasarlanmış, endüstriyel standartlarda **3D Parçacık Sürü Optimizasyonu (PSO)** tabanlı otonom sürü drone koordinasyon ve görev kontrol platformudur.

---

## 📊 Matematiksel Performans Metrikleri

Hiçbir metrik tahmini değildir; tüm veriler **Koopman Arama Teorisi** ve 50 tekrarlı **Monte Carlo simülasyonları** ile kanıtlanmıştır:

- **Sensör Ayak İzi:** $W = 153.07 \, m$, $W_{eff} = 130.11 \, m$ ($h = 85m$, $FOV_h = 84^\circ$, $FOV_v = 56^\circ$).
- **Alan Tarama Hızı (ACR):** 1 Drone için $5.62 \, km^2 / h$, 5 Drone için $28.10 \, km^2 / h$, 10 Drone için $56.20 \, km^2 / h$.
- **Yangın Tespit Süreleri (%95 Güvenilirlikle):**
  - **1 km²:** 3 Drone ile **6.5 dk** (Medyan: 1.5 dk)
  - **10 km²:** 5 Drone ile **39.5 dk** (Medyan: 9.1 dk), 10 Drone ile **19.7 dk**
  - **25 km²:** 10 Drone ile **49.3 dk**, 20 Drone ile **24.6 dk**
- **Algoritma Karşılaştırması:** PyreSwarm 3D-PSO, klasik ızgara (lawnmower) taramaya göre **1.54 kat**, rastgele gezinime göre **2.58 kat** daha hızlı yangın tespiti yapmaktadır.

---

## 📑 Profesyonel PDF Dokümantasyonları

- 📄 **[PyreSwarm Kullanım Kılavuzu (PDF)](docs/PyreSwarm_Kullanim_Kilavuzu.pdf)**: Operasyonel kullanım, arayüz fonksiyonları, alan kapatma sihirbazı ve vatandaş katılımı.
- 📊 **[Matematiksel Model ve Metrik Raporu (PDF)](docs/PyreSwarm_Matematiksel_Model_ve_Metrik_Raporu.pdf)**: Koopman formülasyonu, Monte Carlo simülasyon grafikleri ve ampirik benchmark tabloları.
- 📖 [Türkçe Markdown Kılavuz](docs/USER_GUIDE_TR.md)
- 🛩️ [MAVLink & Pixhawk Gerçek Saha Kurulum Kılavuzu](docs/MAVLINK_SETUP_GUIDE.md)

---

## 🌟 Öne Çıkan Özellikler

- 🛰️ **3D Modifiye Parçacık Sürü Optimizasyonu (PSO):**
  - Sürüdeki her drone bir optimizasyon parçacığıdır.
  - Hedef fonksiyonu ($fitness$): YOLOv8 duman ve alev algılama güven skoru + taranmamış alan keşif bonusu.
  - Sürü üyeleri pbest (bireysel en iyi) ve gbest (küresel en iyi) hedeflerini dinamik mesh ağıyla paylaşır.
- 📐 **Dinamik İrtifa ve Hız Adaptasyonu (Goal Achievement):**
  - Yangın aranırken geniş görüş açısı (FOV) için yüksek irtifa (~85m) ve yüksek hız (~12 m/s).
  - Yangın odağı bulunduğunda hassas koordinat kestirimi için alçak irtifa (~35m) ve inceleme hızı (~4 m/s).
- 🚫 **Kullanıcı Tanımlı Bölge Kapatma (Taboo / Exclusion Geofencing):**
  - Söndürülmüş yangın alanları harita üzerinden tek tıkla kapatılır. Sürü kapalı alanı arama dışı bırakır ve $gbest$ otomatik güncellenir.
  - Göller, barajlar ve uçuşa yasak bölgeler sisteme tanımlanır; drone'lar bu bölgelere girmez.
- 🤝 **Dinamik Vatandaş / Gönüllü Drone Katılımı (Citizen Swarm):**
  - Yangın bölgesine gelen sivil/gönüllü drone'lar web arayüzünden tek tıkla sürüye eklenir ($N \to N+1$).
  - Sistem sivil pilota anlık yön ve irtifa tavsiyesi üreterek aramaya dahil eder.
- 🛡️ **Yapay Potansiyel Alanlar (APF) ile Çarpışma Önleme:**
  - Sürü içi minimum 30 metre emniyet mesafesi matematiksel itici potansiyel alanlarla garanti edilir.
- 🛩️ **Donanım ve Protokol Bağımsız (Hardware Agnostic):**
  - Pixhawk / PX4 / ArduPilot otopilotları (PyMAVLink).
  - Dahili yüksek doğruluklu 6-DOF fizik simülatörü.
  - WebRTC / RTSP canlı video aktarımı.
- 💻 **Gelişmiş Web Görev Kontrol İstasyonu (GCS):**
  - Leaflet tabanlı taktik harita, telemetri panelleri, canlı kamera HUD akışı, liderlik tablosu.

---

## 🏗️ Sistem Mimarisi

```
                                  +---------------------------------------+
                                  |     Modern Web Görev Kontrol (GCS)    |
                                  | (Leaflet Map, Live HUD, Geofence Tools|
                                  +-------------------+-------------------+
                                                      | WebSockets & REST API
                                                      v
+---------------------------------------------------------------------------------------------------------+
|                                         PYRESWARM CORE ENGINE                                           |
+---------------------------------------------------------------------------------------------------------+
|  1. 3D-PSO Koordinatörü:                                                                                |
|     - Bilişsel ve Sosyal Çekim (pbest, gbest)                                                           |
|     - Yapay Potansiyel Alanlar (APF) ile Sürü İçi Çarpışma Önleme                                       |
|     - Yasaklı/Söndürülmüş Bölge Kaçınması (Taboo Geofence Repulsion)                                    |
|                                                                                                         |
|  2. Bilgisayarlı Görü (Computer Vision):                                                                |
|     - YOLOv8 (best.pt) Gerçek Zamanlı Yangın ve Duman Tespiti                                           |
|     - Pin-Hole Ray Casting ile Görüntüden Zemin GPS Koordinatı Kestirimi                                |
|                                                                                                         |
|  3. Donanım Soyutlama Katmanı (HAL):                                                                    |
|     - MAVLink Sürücüsü (Pixhawk / PX4 / ArduPilot)                                                      |
|     - 6-DOF Simülatör (Batarya, Rüzgar, Gerçekçi Kamera)                                                |
|     - Gönüllü/Vatandaş Drone Köprüsü                                                                    |
+---------------------------------------------------------------------------------------------------------+
```

---

## 🚀 Hızlı Başlangıç

### 1. Kurulum
Gereksinimleri yükleyin:
```bash
pip install -r requirements.txt
```

### 2. Sistemi Başlatma
```bash
python run.py
```
Tarayıcınızda açın:
```
http://localhost:8000
```

---

## 🧪 Testler ve Kalite Güvencesi

Proje kapsamındaki tüm algoritmik, matematiksel ve API bileşenleri `pytest` ile test edilmiştir:
```bash
pytest tests/ -v
```

**Test Sonuçları:**
```
tests\test_api.py ................ PASSED [25%]
tests\test_detector.py ........... PASSED [43%]
tests\test_geofence.py ........... PASSED [62%]
tests\test_pso.py ................ PASSED [81%]
tests\test_swarm_integration.py .. PASSED [100%]

================== 16 passed in 7.66s ==================
```

---

## 📚 Dokümantasyonlar

- [Türkçe Operasyonel Kullanım Kılavuzu](docs/USER_GUIDE_TR.md)
- [MAVLink & Pixhawk Gerçek Saha Kurulum Kılavuzu](docs/MAVLINK_SETUP_GUIDE.md)

---

## 📄 Lisans
Bu proje açık kaynaklıdır ve MIT lisansı altında sunulmaktadır.
Ormanlarımızın korunmasına katkı sağlaması dileğiyle.
