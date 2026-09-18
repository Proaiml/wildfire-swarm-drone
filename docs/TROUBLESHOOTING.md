# PyreSwarm - Sorun Giderme Kılavuzu (Troubleshooting)

## 1. Yaygın Sorunlar ve Çözümleri

### S1: Web haritasında drone konumları güncellenmiyor
* **Neden:** WebSocket bağlantısı kopmuş veya backend sunucusu durdurulmuş olabilir.
* **Çözüm:** Tarayıcıyı F5 ile yenileyin; konsolda `ws://localhost:8000/ws/telemetry` bağlantısını denetleyin. Backend loglarında hata olup olmadığını kontrol edin.

### S2: Drone yangın görmesine rağmen alarm vermiyor
* **Neden:** `SpatialTemporalEvidenceFusion` en az 3 ardışık kararlı kare ve \%40 güven eşiği aramaktadır. Tekil geçici kareler elenir.
* **Çözüm:** Drone'un yangın üzerinde en az 1-2 saniye kalmasını sağlayın; kamera irtifasını düşürün.

### S3: GPU bulunamadı hatası (CUDA Fallback)
* **Neden:** PyTorch CUDA sürücüsü algılanamamıştır.
* **Çözüm:** Sistem otomatik olarak CPU fallback moduna geçer. Performansı artırmak için NVIDIA CUDA sürücülerini güncelleyin.

### S4: MAVLink bağlantısı kurulamıyor (`PARTIALLY_VALIDATED`)
* **Neden:** UDP portu (14540) başka bir süreç (QGroundControl / MissionPlanner) tarafından kilitlenmiş olabilir veya kablo bağlantısı kopmuştur.
* **Çözüm:** Bağlantı URL'sini `config/` altından kontrol edin ve port çakışmalarını giderin.
