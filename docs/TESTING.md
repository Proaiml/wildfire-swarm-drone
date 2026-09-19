> Tarihsel belge: güncel web kontrol akışı ve doğrulama sınırları için [REAL_WORLD_READINESS](REAL_WORLD_READINESS.md) ve hub kılavuzunu okuyun. Aşağıdaki önceki saha/başarım iddiaları güncel doğrulama sayılmaz.

# PyreSwarm - Test Stratejisi ve Doğrulama Rehberi (Testing)

## 1. Test Piramidi ve Kapsam

PyreSwarm test suite'i `pytest` ile yönetilir ve 54 testten oluşur (%100 Başarı):

* **Birim Testleri (Unit Tests):**
  - `test_coordinates.py`: WGS84 $\leftrightarrow$ ENU teğet dönüşümleri, haversine mesafeleri.
  - `test_fusion_and_incidents.py`: Kanıt birikimi, zamansal sönümleme ve incident durum makinesi.
  - `test_safety_plane.py`: NFZ kısıtları, irtifa ve hız clamping, APF çarpışma önleme.
  - `test_battery_and_rth.py`: LiPo deşarj eğrisi ve otonom RTL eşik kontrolleri.
  - `test_communication_and_membership.py`: MessageBus pub-sub, wildcard topic'ler ve dynamic join.
* **Entegrasyon Testleri (Integration Tests):**
  - `test_swarm_integration.py`: Sürü başlatma, YOLO tespiti ve PSO gbest senkronizasyonu.
  - `test_geofence.py`: Dinamik kapatılan bölgeler ve poligon filtreleme.
* **Uçtan Uca Kabul Testi (End-to-End Acceptance Test):**
  - `test_e2e_acceptance.py`: Requirement 81 tam senaryosu (Arama -> Tespit -> Yangın Doğrulama -> Sürü Bölünmesi -> Dinamik Katılım -> İletişim Kaybı -> Düşük Batarya RTL -> Görev Tamamlama).
* **Değişmez ve Fuzzing Testleri (Invariants & Fuzz Tests):**
  - `test_invariants.py`: Güvenlik ve kimlik değişmezlerinin matematiksel doğrulanması.
  - `test_fuzz_and_edge_cases.py`: NaN, sonsuzluk, negatif batarya ve bozuk JSON girdileri.

## 2. Testleri Çalıştırma
```bash
python -m pytest tests/ -v
```
Windows ortamında tek tıkla: `TESTLERI_CALISTIR.bat`.
