# 2026-09-26 — Sahaya hazır hub: drone'unu getir, sürüye kat

- **ArduPilot sürü kontrolü (MAVLink):** bağlanan otopilot önce yalnızca gözlenir; uçuş öncesi kontroller (bağlantı, GPS 3D fix + 6 uydu, EKF, ev konumu, batarya, `FS_GCS_ENABLE`, üsse uzaklık) geçince operatör **Hub kontrolüne al** der. GUIDED + kollama + kalkış, 4 Hz hız komutları, her komutta ACK, mod doğrulaması, 1 Hz GCS heartbeat.
- **Güvenlik:** pilot kumandadan modu değiştirirse hub aracı anında bırakır; hub bağlantısı koparsa komut kesilir ve otopilot kendi failsafe'iyle eve döner; duraklat/RTL gerçek otopilotlara ulaşır. PX4: izleme + RTL/iniş.
- **ArduPilot SITL ile 3 araçlı kabul denemesi** (`tools/sitl/`, `SITL_BASLAT.bat`), sonuçlar `artifacts/sitl_trial/result.json`.
- **Hibrit arama (yeni varsayılan):** sensör erişimine göre aralıklı şeritler; yangın bilinince sektörünü taramış drone'lar rüzgâr altı kıvılcım konisine döner. "Son görülme" kapsama haritası, rüzgâr girişi.
- **İnceleme ayrılması:** iki inceleyici olayın karşı yanlarında ve farklı irtifada durur.
- **Tatbikat kamerası:** yangın karede gerçek konumunda ve boyutunda, burun yönüne göre dönmüş çizilir; modelin görmediği `smoke.png` çıkarıldı. Tatbikat tablosu tutuşmadan tespite süreyi gösterir.
- **Arayüz:** otopilot durumu, uçuş öncesi kontrol listesi, kontrol düğmeleri, kapsama katmanı, rüzgâr formu, tatbikat tablosu. Varsayılan filo görev başlayana dek yerde bekler. Sunucu proje dışından başlatılınca kameranın kör kalması düzeltildi.
- **Karşılaştırma:** iki senaryo (rastgele yangın, rüzgâr altı artçı yangın), ayar tohumları 101-120, son test tohumları 241-280; `scripts/make_search_report.py` tablo ve grafikleri üretir.
- [Saha kılavuzu](docs/SAHA_KILAVUZU_TR.md). 118 test.

# 2026-09-19 — Ortak operasyon merkezi

- PSO hareket güncellemesi, kapasite ağırlıklı devriye, sınırlı kanıt incelemesi ve poligon dolanması.
- Ayrı SAR görevi, kaynaklı olay/operatör teyidi ve gizli tatbikat hedefleri.
- Gönüllü gerçek telemetri / pilot rehberliği protokolü ve örnek istemci.
- NED/ENU, LAND, kayıt hataları, zaman aşımı, kalkış ve batarya rezervi düzeltmeleri.
- Responsive görev merkezi; yerel Leaflet bağımlılığı.
- 89 test; yeniden üretilebilir 600 saniyelik hub senaryosu.
- Güncel saha hazırlık sınırları; fiziksel otonom uçuş henüz doğrulanmadı.

# Değişiklik Günlüğü (Changelog)

Tüm önemli değişiklikler bu dosyada belgelenecektir.
Biçim [Keep a Changelog](https://keepachangelog.com/) standardına dayanır.

## [0.1.0] - 2026-09-18
### Eklendi
- WGS84 ve Yerel Metrik ENU koordinat dönüşüm katmanı (`src/common/coordinates.py`).
- Güvenlik ve Uçuş Düzlemi (`SafetyFlightPlane`), Geofence kısıtları ve APF çarpışma önleme.
- Uzamsal-Zamansal Kanıt Füzyonu (`SpatialTemporalEvidenceFusion`) ve Yangın Olayı Yönetimi (`FireIncidentManager`).
- Çok Amaçlı Hedef Ulaşımı (`GoalAttainmentFitness`), Çeşitlilik Yöneticisi ve Tabu Maskeleme ile 3D-PSO Sürü Optimize Edici.
- Olay güdümlü `MessageBus`, `CommunicationLossHandler` ve dinamik sürü katılımı (`SwarmMembershipManager`).
- Deterministik tohumlu simülasyon motoru (`SwarmSimulationEngine`) ve karşılaştırmalı test paketi (`BaselineRunner`).
- 54 test içeren tam otomatik test paketi (%100 Başarı).
- MAVLink ve PX4 entegrasyon arayüzü (`PARTIALLY_VALIDATED`).
- Kapsamlı teknik mimari, ADR ve PDF rapor oluşturma altyapısı.
