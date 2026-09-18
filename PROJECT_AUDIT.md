# PyreSwarm — Proje Teknik Durum ve Mimari Denetim Raporu (Project Audit)
**Tarih:** 2026-09-18  
**Versiyon:** 2.5.0-audit  
**Durum:** KAPSAMLI DENETİM TAMAMLANDI (PASSED)

---

## 1. Yönetici Özeti ve Mevcut Kod Tabanı Envanteri

PyreSwarm, orman yangınlarının erken tespiti için YOLOv8 yapay zeka nesne algılama modeli (`best.pt`) ile 3 Boyutlu Parçacık Sürü Optimizasyonunu (3D-PSO) birleştiren otonom bir sürü drone yönetim platformudur.

### 1.1. Dizin ve Dosya Yapısı
```text
c:\Users\İlhan\Desktop\ödev2/
├── best.pt                             # YOLOv8n eğitimli yangın/duman ağırlıkları (6.2 MB)
├── smoke detect.py                     # Orijinal tekil test betiği (YOLO demo)
├── run.py                              # Uygulama başlatıcı ve tarayıcı otomatik tetikleyici
├── BASLAT.bat                          # Tek tıkla Windows GCS başlatıcı betik
├── TESTLERI_CALISTIR.bat               # Tek tıkla pytest test koşucusu
├── requirements.txt                    # Python kütüphane bağımlılıkları
├── config/
│   └── mission_config.json             # Kalıcı operasyon üssü ve bölge ön tanımları
├── core/
│   ├── fire_detector.py                # YOLOv8 inferansı, HUD çizimi, zemin GPS kestirimi
│   ├── geofence_manager.py             # Shapely tabanlı poligon kısıtları ve APF kaçınması
│   ├── metrics_engine.py               # Koopman arama teorisi, ACR ve Monte Carlo benchmark'ı
│   ├── pso_engine.py                   # 3D PSO arama motoru, APF ayrılma, rüzgar ve AOI
│   └── swarm_manager.py                # Merkezi orkestrasyon, liderlik, olay ihracı
├── hardware/
│   ├── drone_base.py                   # BaseDrone soyut sınıfı ve DroneTelemetry dataclass
│   ├── mavlink_drone.py                # PyMAVLink tabanlı Pixhawk/PX4/ArduPilot sürücüsü
│   ├── simulated_drone.py              # 6-DOF kinematik, batarya modeli, sentetik video
│   └── volunteer_bridge.py             # Sivil/gönüllü drone REST entegrasyon köprüsü
├── web/
│   ├── app.py                          # FastAPI REST API, MJPEG stream ve WebSocket telemetrisi
│   ├── templates/index.html            # GCS arayüzü, Leaflet harita, HUD ve kontrol modalları
│   └── static/
│       ├── css/style.css               # Aero karanlık tema, radar nabzı, HUD stilleri
│       └── js/dashboard.js             # Leaflet & Google Maps Hibrit, WebSocket, GCS mantığı
├── docs/
│   ├── generate_pdf_reports.py         # ReportLab tabanlı profesyonel PDF üretici
│   ├── MAVLINK_SETUP_GUIDE.md          # Pixhawk/SITL kurulum dokümantasyonu
│   └── USER_GUIDE_TR.md                # Türkçe kullanım kılavuzu
└── tests/
    ├── test_api.py                     # Web API uç nokta testleri
    ├── test_detector.py                # YOLO inferans ve GPS ray-casting testleri
    ├── test_field_operations.py        # Kalıcı üs, hot-plug drone, fail-safe testleri
    ├── test_geofence.py                # Geofence poligon ve itici vektör testleri
    ├── test_metrics_engine.py          # ACR, Koopman süresi ve Monte Carlo testleri
    ├── test_pdf_generation.py          # PDF üretim geçerlilik testleri
    ├── test_pso.py                     # PSO parçacık, gbest ve çarpışma önleme testleri
    ├── test_scale_and_performance.py   # Sürü ölçeklenebilirlik testleri
    └── test_swarm_integration.py       # Tam entegrasyon ve yangın yakınsama testleri
```

---

## 2. Derinlemesine Modül Analizi

### 2.1. Algılama Katmanı (Perception & Inference) — `core/fire_detector.py`
- **Model Dosyası:** `best.pt` (YOLOv8n mimarisi).
- **Parametre Sayısı:** 3,011,238 (3.01 Milyon) ağırlık parametresi [MEASURED].
- **Hesaplama Yükü:** 8.19 GFLOPs [MEASURED].
- **Sınıflar:** 2 sınıf (`0: 'smoke'`, `1: 'fire'`).
- **Girdi Formatı:** BGR $640 \times 480 \times 3$ NumPy dizisi veya Torch Tensor [CONFIGURED_ASSUMPTION].
- **Çıktı Formatı:** Bounding box $[x_1, y_1, x_2, y_2]$, sınıf indeksi, güven skoru ($0.0 - 1.0$).
- **Donanım Hızlandırma:** `torch.cuda.is_available()` ile CUDA otomatik seçimi; yoksa CPU fallback.
- **Isınma (Warmup):** Başlangıçta $320 \times 320$ boyutunda sentetik tensör ile inferans ısınması yapılmaktadır.
- **Pinhole Zemin Ray-Casting GPS Kestirimi:**
  Kamera yatay görüş açısı ($HFOV = 84^\circ$) ve dikey görüş açısı ($VFOV = 56^\circ$) kullanılarak, tespit kutucuğunun merkez pikseli $(p_x, p_y)$ drone'un irtifası ($h$), yalpa (yaw) ve gimbal eğim (pitch) açıları ile zemin düzlemine projekte edilerek gerçek enlem/boylam kestirilmektedir:
  $$\Delta x_{cam} = h \cdot \tan\left(\left(\frac{p_x - W/2}{W/2}\right) \cdot \frac{HFOV}{2}\right)$$
  $$\Delta y_{cam} = h \cdot \tan\left(\left(\frac{H/2 - p_y}{H/2}\right) \cdot \frac{VFOV}{2}\right)$$
  Bu yerel kamera deplasmanı drone heading açısıyla döndürülerek WGS84 derecesine dönüştürülmektedir.

### 2.2. Optimizasyon Motoru — `core/pso_engine.py`
- **Parçacık Uzayı:** 3 Boyutlu durum uzayı $[\text{lat}, \text{lon}, \text{alt}, v_x, v_y, v_z]$.
- **Klasik PSO Hız Güncelleme Denklemi:**
  $$v_i(t+1) = \omega v_i(t) + c_1 r_1 (p_i - x_i(t)) + c_2 r_2 (g - x_i(t)) + v_{repulsion} + v_{wind}$$
- **Kullanılan Parametreler:**
  - $\omega = 0.65$ (Atalet katsayısı) [CONFIGURED_ASSUMPTION]
  - $c_1 = 1.35$ (Bireysel bilişsel katsayı) [CONFIGURED_ASSUMPTION]
  - $c_2 = 1.65$ (Sosyal küresel katsayı) [CONFIGURED_ASSUMPTION]
  - $v_{max} = 14.0\text{ m/s}$, $v_{min} = 2.0\text{ m/s}$ [MANUFACTURER_SPEC / CONFIGURED_ASSUMPTION]
  - $h_{search} = 85.0\text{ m}$, $h_{inspect} = 35.0\text{ m}$ [CONFIGURED_ASSUMPTION]
- **Sürü İçi Çarpışma Önleme (APF Separation):**
  Drone'lar arası mesafe $d_{ij} < 30.0\text{ m}$ olduğunda zıt yönde itici hız vektörü uygulanmaktadır.
- **Mevcut Sınırlılıklar:**
  1. *Tekil gbest Yaklaşımı:* Tüm sürü tek bir yangın odağına doğru yakınsama eğilimindedir. Çoklu yangın senaryolarında sürünün tek bir noktaya çökmesini (swarm collapse) önlemek için multi-attractor veya niş (sub-swarm) mimarisine ihtiyaç vardır.
  2. *Derece/Metre Dönüşümü:* Derece üzerinden yerel skaler ile metrik işlem yapılmaktadır. Tam yerel ENU (East-North-Up) teğet düzlem koordinat dönüşümüne geçilmesi hassasiyeti artıracaktır.
  3. *Fitness Fonksiyonu:* Mevcut durumda ağırlıklı olarak yangın güven skoru maksimize edilmektedir; çok amaçlı Goal Attainment (keşif, enerji, örtüşme cezası) katmanına evrilmelidir.

### 2.3. Coğrafi Kısıtlar ve Taboo Arama — `core/geofence_manager.py`
- **Kütüphane:** Shapely geometry (`Point`, `Polygon`, `nearest_points`).
- **Bölge Türleri:**
  - `fire_extinguished`: Söndürülmüş veya teyit edilmiş yangın (Taboo search gereği tekrar taranmaz).
  - `water_body`: Göl, nehir veya baraj (Yangın çıkmayacak arama dışı su alanı).
  - `no_fly_zone`: Uçuşa kesinlikle yasak alan (Hava koridoru, askeri üs, vs.).
  - `high_risk_search`: Pozitif çekim oluşturan öncelikli orman alanı.
- **İtici Vektör Alanı (Repulsion Field):** Sınır yaklaştıkça yapay potansiyel alan (APF) ile ters orantılı itki kuvveti üretilir.

### 2.4. Arama Teorisi ve Matematiksel Metrikler — `core/metrics_engine.py`
- **Sensör İzdüşümü (Ground Footprint):**
  $h = 85\text{ m}$, $HFOV = 84^\circ$, $VFOV = 56^\circ$ için:
  - Genişlik: $W = 2 \cdot 85 \cdot \tan(42^\circ) = 153.07\text{ m}$ [THEORETICAL_BOUND]
  - Uzunluk: $L = 2 \cdot 85 \cdot \tan(28^\circ) = 90.39\text{ m}$ [THEORETICAL_BOUND]
  - Anlık Zemin Alanı: $A = 13,836\text{ m}^2$ ($0.0138\text{ km}^2$) [THEORETICAL_BOUND]
  - Etkin Tarama Genişliği ($\%15$ örtüşme ile): $W_{eff} = 130.11\text{ m}$ [THEORETICAL_BOUND]
- **Alan Tarama Hızı (Area Coverage Rate - ACR):**
  $v = 12.0\text{ m/s}$ için:
  - Tekil Drone: $ACR_1 = 12 \cdot 130.11 \cdot 3600 / 10^6 = 5.62\text{ km}^2/\text{saat}$ [THEORETICAL_BOUND]
  - 4 Drone Filosu: $ACR_4 = 22.48\text{ km}^2/\text{saat}$ [THEORETICAL_BOUND]
- **Koopman Arama Teorisinden MTTD (Mean Time to Detect):**
  $$P(t) = 1 - \exp\left(-\frac{N \cdot v \cdot W_{eff} \cdot \eta_{pso}}{\text{Alan}} \cdot t\right)$$
  Burada $\eta_{pso} = 1.62$, duman sürüklenme gradyanının ve sosyal haberleşmenin sağladığı arama çarpanıdır [SIMULATED].
- **Monte Carlo Doğrulaması:** 50 bağımsız rastgele tohumlu simülasyon koşusu ile Random Search, Grid Lawnmower ve 3D-PSO karşılaştırılmaktadır [SIMULATED].

### 2.5. Donanım ve Simülatör Katmanı — `hardware/`
- `BaseDrone`: Ortak soyut sınıf (`connect`, `arm`, `takeoff`, `land`, `return_to_launch`, `send_velocity`).
- `SimulatedDrone`: 6-DOF kinematik, Euler integratörü, batarya deşarj eğrisi, sentetik/gerçek yangın görüntüsü harmanlama (`mana.jpg`, `fire.jpg`, `smoke.png`), $\%15$ batarya seviyesinde otonom RTL fail-safe'i [SIMULATED].
- `MAVLinkDrone`: PyMAVLink tabanlı, UDP (`udpin:0.0.0.0:14550`) veya Seri bağlantı ile Pixhawk / PX4 / ArduPilot otopilot kontrolü ve RTSP video akışı [PARTIALLY_VALIDATED].
- `VolunteerDrone`: Gönüllü/vatandaş drone'ları için REST/WebSocket telemetri ve rota tavsiye köprüsü.

### 2.6. Web GCS ve Sunucu Katmanı — `web/`
- **FastAPI Backend (`web/app.py`):**
  - REST Uç Noktaları: `/api/mission/base`, `/api/swarm/add_drone`, `/api/drone/{id}/rtl`, `/api/geofence/add`, `/api/mission/set_wind`, `/api/mission/set_aoi`, `/api/mission/export_report`.
  - Canlı MJPEG Akışı: `/api/video_feed/{drone_id}`.
  - WebSocket: `/ws/telemetry` (4 Hz gerçek zamanlı durum paketi).
- **Frontend Dashboard (`web/templates/index.html`, `dashboard.js`, `style.css`):**
  - Google Maps Hibrit / Uydu / Sokak ve OpenStreetMap katmanları.
  - Kalıcı Operasyon Üssü sürükleme, radar nabız göstergesi ve Türkiye yangın bölgesi ön tanımları.
  - Kapsamlı "+ DRONE EKLE" modalı (Simüle, MAVLink, Gönüllü).
  - Filo tablosu bireysel kontrolleri (RTL, İniş, Sil).
  - OGM/İtfaiye hazır WhatsApp telsiz ihbar modalı.

---

## 3. Test Kapsamı ve Doğrulama Durumu

Mevcut test paketi (`pytest tests/`) 30 adet otomatik test içermekte olup **%100 başarıyla** geçmektedir:
1. `tests/test_api.py` (5 test): Index, swarm state, mission controls, geofence, volunteer.
2. `tests/test_detector.py` (3 test): Model init, sample inference, pinhole ray-casting GPS.
3. `tests/test_field_operations.py` (6 test): Kalıcı üs, hot-plug drone, bireysel RTL/Land, batarya fail-safe, quick fire.
4. `tests/test_geofence.py` (3 test): Poligon çevreleme, APF itici vektör, ceza fonksiyonu.
5. `tests/test_metrics_engine.py` (4 test): Footprint, ACR, Koopman süresi, Monte Carlo benchmark.
6. `tests/test_pdf_generation.py` (1 test): ReportLab PDF raporlarının varlığı ve geçerliliği.
7. `tests/test_pso.py` (3 test): Parçacık kaydı, gbest paylaşımı, APF çarpışma önleme.
8. `tests/test_scale_and_performance.py` (2 test): Büyük sürü ölçeklenebilirliği (50 drone), sıfır drone durumu.
9. `tests/test_swarm_integration.py` (3 test): Sürü başlatma, yangın yakınsaması, taboo bölge gbest sıfırlama.

---

## 4. Tespit Edilen Eksiklikler, Riskler ve Teknik Borçlar (Gaps & Debt)

Aşağıdaki maddeler sistemin endüstriyel ve bilimsel seviyeye çıkarılması için geliştirilmesi gereken alanlardır:

| # | Alan | Mevcut Durum | Hedef / İhtiyaç |
|---|------|--------------|-----------------|
| 1 | **Intelligence vs Safety** | AI/PSO doğrudan hız üretip drone'a gönderiyor | **Strict Separation:** Intelligence Plane (hedef üretir) $\rightarrow$ Safety Flight Plane (NFZ, ayrılma, batarya kontrol eder, hedefe projeksiyon yapar) |
| 2 | **Koordinat Çerçevesi** | Derece tabanlı basit dönüşüm | **Local ENU (East-North-Up):** Üs merkezli teğet düzlem metrik koordinat çerçevesi |
| 3 | **Çok Amaçlı PSO** | Sadece fire confidence maksimizasyonu | **Goal Attainment / MOPSO:** Yangın güveni, duman, yeni alan keşfi (coverage), enerji, örtüşme cezası |
| 4 | **Swarm Diversity** | Tek `gbest` konumu | **Multi-Attractor / Sub-Swarms:** Birden fazla yangının aynı anda aranması ve sürünün tek noktaya çökmesinin engellenmesi |
| 5 | **Incident Lifecycle** | Basit liste kaydı | **Spatio-Temporal Evidence Fusion:** `candidate` $\rightarrow$ `suspected` $\rightarrow$ `confirmed` $\rightarrow$ `monitoring` $\rightarrow$ `resolved` |
| 6 | **Search Map** | Geofence poligonları | **Grid/Cell Coverage Heatmap:** Taranmış alan olasılığı, son gözlem zamanı, keşif puanı |
| 7 | **Haberleşme Mimarisi** | Paylaşımlı bellek sözlüğü | **MessageBus Abstraction:** `InMemoryBus`, `WebSocketBus`, topic yapısı (`telemetry`, `detection`, `mission`) |
| 8 | **İletişim Kopması** | Durum takibi yok | **Comm Loss Handling:** `CONNECTED`, `DEGRADED`, `STALE`, `DISCONNECTED` durumları ve otonom failsafe |
| 9 | **Deterministik Simülasyon**| Rastgele tohumlar | **Reproducible Simulation:** Sabit `--seed` ile tekrarlanabilir senaryolar ve hata enjeksiyonu (fault injection) |
| 10| **Baseline Kıyaslaması** | Sadece Monte Carlo fonksiyonu | **Kapsamlı Karşılaştırma:** Random Search vs Boustrophedon (Lawnmower) vs Greedy vs Swarm PSO (CSV/JSON/PDF çıktıları) |
| 11| **Veri Kategorizasyonu** | Kısmi dokümante | **Kesin Etiketleme:** `[MEASURED]`, `[SIMULATED]`, `[MANUFACTURER_SPEC]`, `[CONFIGURED_ASSUMPTION]`, `[THEORETICAL_BOUND]` |
| 12| **Veritabanı Kalıcılığı** | JSON config dosyası | **SQLite Persistence:** Görevler, drone telemetri logları, incident tarihçesi ve metriklerin veritabanında saklanması |

---

## 5. Korunacak Mevcut Özellikler (Regresyon Güvencesi)
- YOLOv8 inferans motoru ve `best.pt` ağırlıkları (`core/fire_detector.py`).
- Pinhole zemin GPS kestirim matematiği.
- Shapely tabanlı geofence poligon denetimi.
- Koopman arama teorisi ve analitik ACR formülasyonları.
- Kalıcı operasyon üssü ve bölge ön tanımları (`config/mission_config.json`).
- Leaflet ve Google Maps Hibrit arayüzü (`web/templates/index.html`).
- Tek tıkla başlatıcılar (`BASLAT.bat`, `TESTLERI_CALISTIR.bat`, `run.py`).
- Mevcut 30 testin tamamı kırılmadan korunacaktır.
