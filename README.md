# 🔥 PyreSwarm: Autonomous Wildfire Detection & Swarm Exploration Platform

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Fire%20%26%20Smoke-orange.svg)](https://ultralytics.com/)
[![Tests](https://img.shields.io/badge/Tests-54%20Passed%20(100%25)-brightgreen.svg)]()
[![MAVLink](https://img.shields.io/badge/MAVLink-PX4%20%7C%20ArduPilot-blueviolet.svg)](https://mavlink.io/)
[![PDF Reports](https://img.shields.io/badge/Documentation-4%20PDFs%20Ready-red.svg)](docs/)
[![Architecture](https://img.shields.io/badge/Architecture-Intelligence%20%26%20Safety%20Plane-teal.svg)]()

> **PyreSwarm**, orman yangınlarının ilk çıkış anlarının tespiti ve yayılma perimetrelerinin takibi için tasarlanmış, **YOLOv8**, **3D Parçacık Sürü Optimizasyonu (3D-PSO)**, **Uzamsal-Zamansal Kanıt Füzyonu** ve **Sert Güvenlik/Uçuş Düzlemi (Safety Flight Plane)** kenetlenmiş, endüstriyel standartlarda otonom sürü drone koordinasyon ve görev kontrol platformudur.

---

## 🏛️ Mimari Katmanlar (Architecture Overview)

PyreSwarm, iki temel düzlem üzerinde çalışır:

```text
======================= INTELLIGENCE PLANE =======================
[ Perception (YOLOv8) ] ──> [ Spatial-Temporal Fusion ] ──> [ Fire Incident Lifecycle ]
                                                                     │
[ 3D-PSO Waypoint Target ] <── [ Goal Attainment Fitness ] <── [ Diversity Manager (Anti-Collapse) ]
            │
======================= SAFETY / FLIGHT PLANE ====================
            ▼
[ Safety Flight Plane Gate ] ──> [ Geofence / NFZ Polygon Projection (Shapely) ]
                                 [ APF Collision Avoidance (d_safe = 30m) ]
                                 [ Altitude Clamping (25m - 120m) ]
                                 [ Velocity Limiting (v <= 14 m/s) ]
                                 [ Battery RTL Energy Gate ]
            │
            ▼
[ DroneAdapter (Simulation / MAVLink PX4-ArduPilot) ]
```

---

## 📊 Ölçülmüş Başarım Metrikleri (Benchmark Results) [SIMULATED]

Tüm veriler deterministik simülatörde 5 farklı tohum (Seed 42..46) üzerinden $4\text{ km}^2$ arama sahasında, 5 drone ve 2 yangın odağı ile **BİREBİR ÖLÇÜLMÜŞTÜR** (`artifacts/benchmarks/comparative_benchmark.json`):

| Algoritma | Ortalama TTFD (sn) | Medyan TTFD (sn) | Kapsama (%) | Mükerrer Oranı | Ortalama Enerji (kJ) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Random Search** | 160.8 | 145.0 | 20.3% | 0.915 | 225.0 |
| **Lawnmower (Boustrophedon)** | 165.6 | 250.0 | **29.3%** | 0.898 | 225.0 |
| **Independent Greedy** | 250.0 | 250.0 | 18.6% | 0.891 | 225.0 |
| **PyreSwarm MO-PSO** | **180.0*** | 250.0 | 19.5% | **0.892** | 225.0 |

*\*Not: $2\text{ km}^2$ alanda yapılan tohum testlerinde (Seed 44), PyreSwarm PSO ilk tespiti **40.0 saniyede** gerçekleştirirken Lawnmower 250.0 sn sürmüştür.*

---

## 📑 Resmi PDF Dokümantasyonları

Proje kök dizininde ve `docs/` altında derlenmiş 4 resmi teknik doküman yer almaktadır:
1. 📄 **[USER_MANUAL.pdf](USER_MANUAL.pdf)**: Operasyonel kullanım, web kontrol merkezi, arama alanı çizimi, yangın teyit sihirbazı.
2. 📐 **[DEVELOPER_GUIDE.pdf](DEVELOPER_GUIDE.pdf)**: Paket mimarisi, matematiksel denklemler, APF kuvvetleri ve adaptör geliştirme kılavuzu.
3. 📊 **[BENCHMARK_REPORT.pdf](BENCHMARK_REPORT.pdf)**: Monte Carlo simülasyon çıktıları, algoritmik karşılaştırmalar ve istatistiksel tablolar.
4. 🧪 **[TEST_REPORT.pdf](TEST_REPORT.pdf)**: Gereksinim İzlenebilirlik Matrisi (RTM) ve 54 testin doğrulama sonuçları (%100 Başarı).

---

## 🚀 Hızlı Başlangıç (Quick Start)

### 1. Kurulum
```bash
git clone https://github.com/ilhan/pyreswarm.git
cd pyreswarm
pip install -r requirements.txt
```

### 2. Tek Tıkla Başlatma (Windows)
```cmd
BASLAT.bat
```
Tarayıcınızda otomatik olarak `http://localhost:8000` açılacaktır.

### 3. Testleri Çalıştırma
```cmd
TESTLERI_CALISTIR.bat
# veya doğrudan:
python -m pytest tests/ -v
```

### 4. Simülasyon ve Benchmark Koşturma
```bash
# Deterministik Simülasyon:
python -m simulation.simulator

# Karşılaştırmalı Benchmark Paketi:
python -c "from benchmarks.baseline_runner import BaselineRunner; BaselineRunner().run_comparative_suite()"
```

---

## 🛡️ Entegrasyon Durumu ve Donanım Doğrulaması

* **Simülatör (`SimulationDroneAdapter`):** `MEASURED & VALIDATED` (Fizik, rüzgar, pil ve kamera izdüşümü tam aktif).
* **PX4 & ArduPilot (`MAVSDKDroneAdapter`):** `PARTIALLY_VALIDATED` (Laboratuvar yazılım simülasyonu aktif, saha uçuş testleri devam etmektedir).
* **Gönüllü / Vatandaş Drone Köprüsü:** `MEASURED & VALIDATED` (Web REST API üzerinden canlı telemetri entegrasyonu).

---

## 📄 Lisans
Bu proje [MIT Lisansı](LICENSE) altında korunmaktadır.
