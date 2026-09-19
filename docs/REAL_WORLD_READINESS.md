# Gerçek dünya uyumluluğu — 19 Eylül 2026

## Bulgular ve yapılan düzeltmeler

Web `core/` + `hardware/` yolunu kullanıyordu. `src/` içindeki yeni güvenlik, haberleşme ve benchmark katmanlarının varlığı web kontrolünde çalıştıklarını kanıtlamıyordu. Mevcut 57 testin geçmesi bu ayrışmayı yakalamıyordu.

| Bulgu | Değişiklik / kalan sınır |
|---|---|
| Başlangıç yangınları keşfedilmiş kümeye ekleniyordu | Tatbikat gerçeği ve gözlem ayrıldı; senaryo API'si doğrudan olay üretmez. |
| Keşif rastgele hız + başlangıç konumuna bilişsel çekimle sıkışıyordu | Kapasite ağırlıklı kalıcı tarama şeritleri; pozitif kanıtta sınırlı PSO incelemesi. |
| Tüm sürü tek en iyi skora çekiliyordu | En fazla iki inceleyici, 30 s inceleme penceresi, kalan filo devriyesi. |
| Hedef irtifa hesaplanıyor ama uygulanmıyordu | Kapasite sınırında dikey hedef takibi, ivme sınırı, kademeli kalkış. |
| Kamera inferansı kontrol döngüsünü geciktiriyordu | Ayrı algılama işçisi; kamera yokken de kontrol ve telemetri devam eder. |
| Geofence yalnızca itkiydi | Tam yol parçası ve duruş ufku kontrolü, tamponlu görünürlük grafiği dolanması, simülasyon adımında sınır kontrolü. |
| Gönüllü konumu komutla sahte olarak ilerliyordu | Yalnızca dışarıdan telemetri konumu günceller; zaman aşımında rehberlik kaldırılır. |
| MAVLink bağlantısı başarısızken kayıt başarılı sayılıyordu | Başarısız bağlantı filoya eklenmez; yinelenen kimlik reddedilir. |
| MAVLink NED/ENU telemetri eksenleri karışıktı; iniş RTL gönderiyordu | Eksen/işaret, LAND ve yaw-rate maskesi düzeltildi; fiziksel kontrol henüz açık değil. |
| Tek yüksek confidence otomatik yangın doğruluyordu | Kaynaklı aday kayıtları ve operatör teyit/durum akışı. |
| Hareket için yangın görülmesi gerekiyordu | Telemetri her kontrolde güncellenir; gözlem yolundan bağımsız rota üretimi. |
| Gönüllü/araç yetenekleri aynı kabul ediliyordu | Hız, irtifa ve HFOV kapasite modeli; farklı sektör boyutları. |
| SAR seçeneği yoktu | Ayrı görev modu, ayrı senaryo verisi, kişi ihbarı ve sentetik sensör. |
| Arayüzde kontroller ekran dışına taşıyordu | Responsive harita/filo/olay düzeni, kararlı harita katmanları, bağlantı durumu ve açık simülasyon etiketleri. |

## Sahaya çıkış için karşılanmamış koşullar

1. **Araç/firmware matrisi ve test tezgahı:** PX4 ve ArduPilot ayrı mod/ACK mantığı gerektirir. DJI için üretici SDK köprüsü gerekir. Her model doğrudan bağlanabilir denemez.
2. **Uçuş kontrolü:** Yerel autopilot komut akışı/watchdog, pilot override, link-loss, EKF/GPS reddi, çarpışma ve RTL engel rotası donanımda kanıtlanmalı. PX4 Offboard sürekli en az 2 Hz yaşam sinyali ister; Python'da nominal bir döngü hızı bu garantiyi vermez. [PX4 resmi belge](https://docs.px4.io/main/en/flight_modes/offboard).
3. **Koordinatlar:** MAVLink `GLOBAL_POSITION_INT` hızları Kuzey/Doğu/Aşağı, `relative_alt` home-relative'dir. Arazi yüksekliği ve kamera kalibrasyonu olmadan konum tahmini kesin hedef koordinatı değildir. [MAVLink ortak mesajlar](https://mavlink.io/en/messages/common).
4. **Algılama:** Etiketli saha veri kümesi, mesafe/GSD, duman/ışık/arazi dilimleri, yanlış alarm oranı, gerçek hedef lokalizasyon hatası ve SAR kişi modeli gerekli.
5. **Görev başarımı:** PSO kazancı eşit sensör, bütçe ve görev koşullarında karşılaştırılmalı. Ham model confidence'ını maksimum yapmak; daha fazla gerçek yangın bulmak, daha iyi kapsama veya en iyi uçuş profili öğrenmek ile aynı değildir.
6. **Operasyon merkezi:** Kimlik doğrulama ve rol bazlı yetki, gönüllü kabulü, veri gizliliği, olay/karar audit kaydı, kalıcı görev verisi, çevrimdışı harita ve ağ kesintisi testleri eksik. Bu sürüm localhost geliştirme merkezidir.
7. **Güvenlik modeli:** Simülasyonda ihlal engellemek için ani yatay duruş uygulanabilir. Gerçek drone anında duramaz. APF ayrılma ve görünürlük grafiği 3D arazi/engel veya tüm olası trafik durumları için güvenlik ispatı değildir. RTL ve pasif fiziksel araçlarla çoklu çarpışma önleme ayrıca geliştirilmelidir.

Bu koşullar çözülmeden sistem gerçek yangın/arama-kurtarma operasyonunda bağımsız uçuş yetkilisi olarak sunulmamalıdır. Kod düzeltmeleri, örnek model çıkarımı ve tarayıcı testleri bu eksikleri ortadan kaldırmaz.

## Kod yolları

Aktif web kontrolü: `web/app.py → core/swarm_manager.py → core/pso_engine.py → hardware/*`.

Eski deney/benchmark yolu: `simulation/`, `benchmarks/`, `src/`. Bu yolun raporları yeni web davranışının kanıtı değildir. Yeniden karşılaştırma yapılmadan eski PDF metrikleri yeni sürüme aktarılmamalıdır.
