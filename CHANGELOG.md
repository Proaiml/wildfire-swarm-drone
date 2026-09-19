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
