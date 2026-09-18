# PyreSwarm — Gereksinimler ve İzlenebilirlik Matrisi (Requirements Traceability Matrix)
**Platform:** Autonomous Wildfire Detection & Swarm Exploration Platform  
**Sürüm:** 2.5.0-master  
**Tarih:** 2026-09-18  

---

## 1. Giriş ve Kapsam

Bu doküman, PyreSwarm sisteminin tüm fonksiyonel, güvenlik, optimizasyon, simülasyon, donanım entegrasyonu ve arayüz gereksinimlerini benzersiz kimliklerle (`REQ-xxx`) tanımlar ve her gereksinimin kod implementasyonu, test karşılığı ve doğrulama durumunu takip eder.

### Veri ve Metrik Sınıflandırma Etiketleri (Rule 1):
- `[MEASURED]`: Gerçek donanım, benchmark veya profiler ile doğrudan ölçülmüş veriler.
- `[SIMULATED]`: Deterministik veya stokastik simülasyon çıktısı olan veriler.
- `[MANUFACTURER_SPEC]`: Donanım veya sensör üreticisinin resmi teknik katalog verisi.
- `[CONFIGURED_ASSUMPTION]`: Kullanıcı veya mühendislik parametresi olarak atanan varsayımlar.
- `[THEORETICAL_BOUND]`: Analitik matematiksel modellerden türetilen teorik alt/üst sınırlar.

---

## 2. Gereksinimler ve İzlenebilirlik Matrisi (RTM)

| REQ ID | Kategori | Başlık ve Tanım | Öncelik | Modül / Dosya | Test ID | Durum |
|---|---|---|---|---|---|---|
| **REQ-PERC-001** | Perception | **YOLOv8 Yangın ve Duman Algılama:** `best.pt` ağırlıkları ile frame başına `fire` ve `smoke` nesneleri için bounding box ve güven skoru üretilmelidir. | CRITICAL | `src/perception/detector.py` | `TEST-PERC-01` | IMPLEMENTED |
| **REQ-PERC-002** | Perception | **Pinhole Ray-Casting Zemin GPS Kestirimi:** Tespit edilen alev/duman pikselleri drone irtifası, yalpa ve gimbal açısı kullanılarak zemin enlem/boylamına projekte edilmelidir. | HIGH | `src/perception/ray_caster.py` | `TEST-PERC-02` | IMPLEMENTED |
| **REQ-PERC-003** | Perception | **Spatio-Temporal Evidence Fusion:** Tekil frame gürültüsünü önlemek için ardışık gözlemler zaman penceresinde filtrelenmeli ve birleştirilmelidir. | HIGH | `src/perception/fusion.py` | `TEST-PERC-03` | IN_PROGRESS |
| **REQ-PERC-004** | Perception | **Detector Adapter Mimarisi:** Algılama motoru Ultralytics, ONNX, TensorRT ve Mock adapter'ları arkasında soyutlanmalıdır. | MEDIUM | `src/perception/adapters.py` | `TEST-PERC-04` | IN_PROGRESS |
| **REQ-DRON-001** | Drone Abstraction | **DroneAdapter Standart Arayüzü:** `connect`, `disconnect`, `arm`, `disarm`, `takeoff`, `land`, `return_to_home`, `set_velocity`, `set_altitude`, `get_state` metodları standartlaştırılmalıdır. | CRITICAL | `src/drones/adapter.py` | `TEST-DRON-01` | IMPLEMENTED |
| **REQ-DRON-002** | Drone Abstraction | **DroneState Kapsamlı Durum Modeli:** Lat, lon, alt, yerel ENU $[x, y, z]$, hız $[v_x, v_y, v_z]$, heading, batarya, GPS fix, pbest, görev modu ve sağlık durumunu içeren tip güvenli model. | CRITICAL | `src/drones/state.py` | `TEST-DRON-02` | IMPLEMENTED |
| **REQ-DRON-003** | Drone Abstraction | **MAVLink / PX4 / ArduPilot Desteği:** PyMAVLink tabanlı donanım entegrasyonu (`PARTIALLY_VALIDATED` olarak etiketli). | HIGH | `src/drones/mavlink_adapter.py` | `TEST-DRON-03` | PARTIALLY_VALIDATED |
| **REQ-DRON-004** | Drone Abstraction | **6-DOF Simüle Drone:** Kinematik, batarya tükenimi, atalet gecikmesi ve sentetik zemin kamerası içeren test simülatörü. | HIGH | `src/drones/simulated_adapter.py` | `TEST-DRON-04` | IMPLEMENTED |
| **REQ-SAFE-001** | Safety Plane | **Strict Separation (Zeka ve Emniyet Ayrımı):** AI/PSO katmanı motorlara doğrudan erişemez; yüksek seviyeli hedef üretir, Safety Plane kısıtları uygulayarak otopilota projekte eder. | CRITICAL | `src/safety/safety_plane.py` | `TEST-SAFE-01` | IN_PROGRESS |
| **REQ-SAFE-002** | Safety Plane | **Geofence & No-Fly Zone (NFZ) Muhafazası:** Drone hiçbir koşulda kullanıcı tanımlı yasaklı poligonların veya arama sınırı dışının içine waypoint alamaz. | CRITICAL | `src/safety/geofence.py` | `TEST-SAFE-02` | IMPLEMENTED |
| **REQ-SAFE-003** | Safety Plane | **Sürü İçi Çarpışma Önleme (APF Separation):** Drone'lar arasında $d_{safe} \ge 30\text{ m}$ güvenli ayrılma kuralı itici potansiyel alanlarla uygulanmalıdır. | CRITICAL | `src/safety/collision.py` | `TEST-SAFE-03` | IMPLEMENTED |
| **REQ-SAFE-004** | Safety Plane | **Batarya Return-to-Home (RTH) Sınırı:** $E_{remaining} > E_{target} + E_{home} + E_{margin}$ kuralı ihlal edildiğinde drone yeni arama görevi alamaz, otonom RTL tetiklenir ($\le \%15$). | CRITICAL | `src/safety/battery_failsafe.py` | `TEST-SAFE-04` | IMPLEMENTED |
| **REQ-SWRM-001** | Swarm PSO | **3D Parçacık Sürü Arama:** İrtifa ve hız uyarlamalı 3D PSO ile yangın gradyanı takibi ve arama optimizasyonu. | HIGH | `src/swarm/pso_optimizer.py` | `TEST-SWRM-01` | IMPLEMENTED |
| **REQ-SWRM-002** | Swarm PSO | **Çok Amaçlı Goal Attainment / MOPSO:** $J = w_f F + w_s S + w_c C - w_r R - w_e E - w_o O - w_d D$ formülasyonu ile çoklu hedeflerin normalize optimizasyonu. | HIGH | `src/swarm/goal_attainment.py` | `TEST-SWRM-02` | IN_PROGRESS |
| **REQ-SWRM-003** | Swarm PSO | **Multi-Attractor & Swarm Diversity (Çoklu Yangın Koruması):** Tekil gbest yerine çoklu çekim noktaları oluşturulmalı; tüm sürünün tek bir yangına çökmesi (collapse) engellenmelidir. | HIGH | `src/swarm/diversity.py` | `TEST-SWRM-03` | IN_PROGRESS |
| **REQ-SWRM-004** | Swarm PSO | **Exploration vs Exploitation Dengeleme:** Yangın bulunduğunda doğrulama için sınırlı sayıda drone ayrılmalı, diğerleri keşfe devam etmelidir. | HIGH | `src/swarm/policy.py` | `TEST-SWRM-04` | IN_PROGRESS |
| **REQ-MAP-001** | Search Map | **Hücresel Kapsama Haritası (Grid/Cell Map):** Arama alanı hücrelere bölünmeli, her hücre için taranma olasılığı, son ziyaret zamanı ve keşif değeri tutulmalıdır. | HIGH | `src/mapping/search_map.py` | `TEST-MAP-01` | IN_PROGRESS |
| **REQ-MAP-002** | Search Map | **Dinamik Taboo Bölge Kapatma:** Teyit edilen veya söndürülen yangın alanları arama dışı taboo olarak kapatılmalı ve sürü orayı tekrar taramamalıdır. | HIGH | `src/mapping/taboo_manager.py` | `TEST-MAP-02` | IMPLEMENTED |
| **REQ-MAP-003** | Search Map | **Local Metric ENU Koordinat Çerçevesi:** Üs merkezli teğet düzlemde metrik $[x, y, z]$ dönüşümü yapılarak açısal bozulma engellenmelidir. | HIGH | `src/mapping/coordinates.py` | `TEST-MAP-03` | IN_PROGRESS |
| **REQ-COMM-001** | Communication | **Distributed Event Bus Abstraction:** `MessageBus` arayüzü ile `InMemoryBus` ve `WebSocketBus` üzerinden telemetri, tespit ve görev mesajları dağıtılmalıdır. | HIGH | `src/communication/bus.py` | `TEST-COMM-01` | IN_PROGRESS |
| **REQ-COMM-002** | Communication | **Bağlantı Kopması (Comm Loss) Yönetimi:** `CONNECTED`, `DEGRADED`, `STALE`, `DISCONNECTED` durumları izlenmeli; bağlantı kesilen drone için son konum ve görev saklanmalıdır. | HIGH | `src/communication/loss_handler.py` | `TEST-COMM-02` | IN_PROGRESS |
| **REQ-COMM-003** | Communication | **Dinamik Sürü Katılımı (Hot-Plugging & Capability Discovery):** Çalışan sürüye yeni bir sivil/gönüllü veya donanım drone'u anında katılabilmeli, sensör ve hız özellikleri keşfedilmelidir. | HIGH | `src/communication/membership.py` | `TEST-COMM-03` | IMPLEMENTED |
| **REQ-INCD-001** | Incidents | **FireIncident Yaşam Döngüsü:** Tespitler kümelenmeli ve `candidate` $\rightarrow$ `suspected` $\rightarrow$ `confirmed` $\rightarrow$ `monitoring` $\rightarrow$ `resolved` durumları yönetilmelidir. | HIGH | `src/incidents/incident_manager.py`| `TEST-INCD-01` | IN_PROGRESS |
| **REQ-GCS-001** | Web GCS | **Web Görev Kontrol Merkezi:** Leaflet, Google Maps Hibrit/Uydu katmanları, canlı HUD video akışı, telemetri göstergeleri ve kalıcı üs yönetimi. | HIGH | `web/templates/index.html` | `TEST-GCS-01` | IMPLEMENTED |
| **REQ-GCS-002** | Web GCS | **Manuel Operatör Müdahalesi (Override):** Görev duraklatma, devam ettirme, tekil ve toplu RTL, acil durum durdurma ve OGM telsiz/WhatsApp sevk paketi üretimi. | HIGH | `web/static/js/dashboard.js` | `TEST-GCS-02` | IMPLEMENTED |
| **REQ-SIM-001** | Simulation | **Deterministik ve Tekrarlanabilir Simülatör:** `--seed` parametresi ile aynı tohumda birebir aynı senaryoyu üreten yerel simülasyon ortamı. | HIGH | `simulation/simulator.py` | `TEST-SIM-01` | IN_PROGRESS |
| **REQ-SIM-002** | Simulation | **Hata Enjeksiyonu (Fault Injection):** GPS kaybı, kamera arızası, düşük batarya ve haberleşme kopması senaryolarının simüle edilebilmesi. | MEDIUM | `simulation/fault_injector.py` | `TEST-SIM-02` | IN_PROGRESS |
| **REQ-SIM-003** | Simulation | **Baseline Kıyaslama Motoru:** Aynı harita ve yangın konumlarında Random Search, Boustrophedon (Lawnmower), Greedy ve Swarm PSO kıyaslaması. | HIGH | `benchmarks/baseline_runner.py` | `TEST-SIM-03` | IN_PROGRESS |
| **REQ-METR-001** | Metrics & Math | **Sensör Footprint ve ACR Hesaplama:** Kamera FOV ve irtifaya bağlı analitik alan tarama hızı ($5.62\text{ km}^2/\text{saat}$ tek drone, $22.48\text{ km}^2/\text{saat}$ 4 drone). | HIGH | `core/metrics_engine.py` | `TEST-METR-01` | IMPLEMENTED |
| **REQ-METR-002** | Metrics & Math | **Koopman MTTD ve Monte Carlo Dağılımı:** Alan büyüklüğü ve drone sayısına göre $T_{50}$ ve $T_{95}$ tespit sürelerinin hesaplanması ve 50 koşulu Monte Carlo analizi. | HIGH | `core/metrics_engine.py` | `TEST-METR-02` | IMPLEMENTED |
| **REQ-DOC-001** | Documentation | **Yazdırılabilir Kapsamlı PDF Dokümantasyonu:** Kullanım Kılavuzu, Geliştirici Kılavuzu, Benchmark Raporu ve Test Raporu ReportLab ile derlenmelidir. | HIGH | `docs/generate_pdf_reports.py` | `TEST-DOC-01` | IMPLEMENTED |

---

## 3. Doğrulama Seviyeleri (Definition of Done)
Bir gereksinimin `DONE` / `VALIDATED` sayılması için:
1. Kaynak kod implementasyonunun eksiksiz mevcut olması,
2. İlgili birim (unit) testinin yazılmış ve geçmiş olması,
3. Entegrasyon davranışının doğrulanmış olması,
4. Dokümantasyonda ve matematiksel modellerde yer alması,
5. Hata yönetimi ve sınır koşullarının test edilmiş olması şarttır.
