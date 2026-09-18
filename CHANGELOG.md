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
