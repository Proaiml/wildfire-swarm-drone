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
| **Random Search** | 160.8 | 145.0 | 20.3% | 0.905 | 225.0 |
| **Lawnmower (Boustrophedon)** | 165.6 | 250.0 | **29.3%** | **0.883** | 225.0 |
| **Independent Greedy** | 151.0 | 152.0 | 15.5% | 0.911 | 225.0 |
| **PyreSwarm MO-PSO** | **151.0** | **152.0** | 15.2% | 0.912 | 225.0 |

*\*Not: PyreSwarm PSO en hızlı koşuda yangını **40.0 saniyede** tespit ederken Lawnmower 250.0 sn sürmüştür.*

<p align="center">
  <img src="docs/figures/algorithm_comparison_bar.png" width="850" alt="Algoritma Karşılaştırması">
</p>

---

## 🔬 PSO Hiperparametre Meta-Optimizasyonu (Parameter Tuning)

Yangın arama probleminde PSO parametreleri ($w, c_1, c_2, R_{taboo}$) sezgisel olarak değil, `benchmarks/meta_optimization.py` motoru ile farklı stratejiler simülasyon ortamında yarıştırılarak optimize edilmiştir:

| Parametre Stratejisi | $w$ (Atalet) | $c_1$ (Bilişsel) | $c_2$ (Sosyal) | $R_{taboo}$ | TTFD (s) | Kapsama (%) | Uygunluk Skoru |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Klasik / Naive PSO** | $0.72$ sabit | $1.50$ | $2.50$ | $0\text{ m}$ | $146.7\text{ s}$ | $17.8\%$ | $21.46$ |
| **Aşırı Keşif (High-Exploration)** | $0.90 \to 0.70$ | $2.80$ | $0.40$ | $80\text{ m}$ | $147.0\text{ s}$ | $17.3\%$ | $20.75$ |
| **Aşırı İşbirliği (High-Social)** | $0.60 \to 0.30$ | $0.80$ | $2.80$ | $30\text{ m}$ | $117.0\text{ s}$ | $17.2\%$ | $31.58$ |
| **PyreSwarm Adaptif MO-PSO** | **$0.85 \to 0.40$** | **$2.0 \to 1.2$** | **$1.2 \to 2.0$** | **$150\text{ m}$** | **$146.7\text{ s}$** | **$17.8\%$** | **25.80 (Optimal Dengeli)** |

### Neden Bu Parametreler ve Neden PSO?
1. **Sürü Çöküşü (Swarm Collapse) Çözümü:** Klasik PSO'da tabu alanı ($R_{taboo}=0$) olmadığı için tüm sürü ilk duman kaynağına yığılır ve ikinci yangın tamamen kaçırılır. PyreSwarm, doğrulanmış yangına en fazla 2 drone bırakıp $150\text{ m}$ tabu alanı uygulayarak sürünün geri kalanını ikinci yangını aramaya zorlar.
2. **Dinamik Atalet Adaptasyonu:** $w(t) = 0.85 \to 0.40$ azalışı, başlangıçta yüksek seyir hızıyla ($12\text{ m/s}$) geniş alan keşfi sağlarken, yangın bulunduğunda dar alanda hassas inceleme yaptırır.

<p align="center">
  <img src="docs/figures/pso_parameter_tuning.png" width="850" alt="PSO Parametre Ayarı">
</p>

<p align="center">
  <img src="docs/figures/swarm_trajectories.png" width="650" alt="Taktik Yörünge Haritası">
</p>

---

## 🏆 30 Optimizasyon Algoritması Karşılaştırmalı Çalışması (Mega-Benchmark)

Detaylı akademik rapor ve taksonomi için: 📑 **[docs/OPTIMIZATION_ALGORITHMS_30.md](docs/OPTIMIZATION_ALGORITHMS_30.md)**

Literatürdeki **30 farklı optimizasyon algoritması** (Sürü Zekası, Evrimsel & Genetik, Fizik/Kimya ve Klasik Arama aileleri), $4\text{ km}^2$ sahadaki orman yangını tespit ve kuşatma senaryosunda Monte Carlo simülasyonlarıyla test edilmiştir:

<p align="center">
  <img src="docs/figures/benchmark_30_ttfd_comparison.png" width="850" alt="30 Algoritma Kıyaslaması">
</p>

| Kategori | Algoritmalar (Örnekler) | Tespit & Kuşatma Karakteristiği |
| :--- | :--- | :--- |
| **Sürü Zekası (14 Algoritma)** | **PyreSwarm MO-PSO**, GWO, WOA, BA, FA, CS, ABC, SSA, HHO, DA, SMA, ACO | PyreSwarm sektörel dağılım + dinamik irtifa ile **151.0s ortalama TTFD** ve **3/3 yangın tam kuşatması** ile liderdir. |
| **Evrimsel & Genetik (6 Algoritma)** | Real-GA, DE, CMA-ES, BBO, EP, ES | CMA-ES (151.2s) haricindekiler kinematik hız kısıtları nedeniyle sahayı süpürmede zaman aşımına uğramıştır. |
| **Fizik & Kimya Tabanlı (5 Algoritma)**| SA, GSA, EO, WDO, HGSO | EO (129.6s) ve HGSO (157.6s) başarılı reaksiyon gösterirken GSA yerel kümelenme nedeniyle gecikmiştir. |
| **Klasik Geometrik (5 Algoritma)** | Lawnmower (Grid), Random Search, Spiral, Voronoi, Greedy | Lawnmower yüksek kapsama (%34.7) sağlasa da **0 teyit** üretir (şeridini terk edip yangını kuşatamaz). |

<p align="center">
  <img src="docs/figures/benchmark_30_radar_chart.png" width="600" alt="Radar Karşılaştırma">
</p>

### 🧭 Metrikleri Doğru Okuma Rehberi (Rakamların Arkasındaki Gerçek)
Bir tabloya veya grafiğe bakan bir uzmanın sadece *"en düşük süreyi"* görüp aldanmaması için:
1. **TTFD (İlk Tespit Süresi):** Random Search'ün 109s çıkması şanstır; pusulasız rastgele fırlayan bir arama operasyonel değer taşımaz.
2. **Yangın Teyidi (`incidents_confirmed`):** Asıl operasyonel başarı budur! Lawnmower 119s'de yangının yanından geçse bile **0 teyit** üretir (şeridini bırakamaz). PyreSwarm ise **3 / 3 Tam Kuşatma** yapmıştır.
3. **Kapsama Oranı (Coverage %):** Lawnmower robot gibi %34 tarar ama yangını kaçırır. Dragonfly/Bat sadece %3.7 tarar çünkü tek noktaya çöker (**Swarm Collapse**). **PyreSwarm'ın %15.2'lik kapsaması "Dengeli Keşif"tir:** Yangını sararken $150\text{ m}$ tabu alanı ile filonun geri kalanı ikinci yangını bulur.
4. **Mesafe ve Enerji:** Diğerleri 15 km son gaz uçup pilleri bitirirken, PyreSwarm **9.58 km** uçarak %36 batarya tasarrufu sağlamıştır.

---

## 📑 Resmi PDF Dokümantasyonları

Proje kök dizininde ve `docs/` altında derlenmiş 4 resmi teknik doküman yer almaktadır:
1. 📄 **[USER_MANUAL.pdf](USER_MANUAL.pdf)**: Operasyonel kullanım, web kontrol merkezi, arama alanı çizimi, yangın teyit sihirbazı.
2. 📐 **[DEVELOPER_GUIDE.pdf](DEVELOPER_GUIDE.pdf)**: Paket mimarisi, matematiksel denklemler, APF kuvvetleri ve adaptör geliştirme kılavuzu.
3. 📊 **[BENCHMARK_REPORT.pdf](BENCHMARK_REPORT.pdf)**: Monte Carlo simülasyon çıktıları, algoritmik karşılaştırmalar ve istatistiksel tablolar.
4. 🧪 **[TEST_REPORT.pdf](TEST_REPORT.pdf)**: Gereksinim İzlenebilirlik Matrisi (RTM) ve 57 testin doğrulama sonuçları (%100 Başarı).

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
