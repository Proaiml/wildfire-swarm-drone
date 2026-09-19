> Tarihsel belge: güncel web kontrol akışı ve doğrulama sınırları için [REAL_WORLD_READINESS](REAL_WORLD_READINESS.md) ve hub kılavuzunu okuyun. Aşağıdaki önceki saha/başarım iddiaları güncel doğrulama sayılmaz.

# PyreSwarm - MAVLink ve PX4 / ArduPilot Entegrasyonu (MAVLink Integration)

## 1. Protokol Mimarisi
MAVLink iletişimi `pymavlink` ve `mavsdk` kütüphaneleri üzerinden sağlanır. Sürü yer kontrol istasyonu (GCS) ile her drone otopilotu arasında UDP veya Seri port üzerinden telemetri ve komut köprüsü kurulur.

* **UDP Port Standardı:** `udp://:14540`, `udp://:14541`, ...
* **Baud Rate:** `57600` veya `115200` (Telemetri radyoları için)

## 2. Kullanılan Temel MAVLink Mesajları
* `HEARTBEAT` (#0): Bağlantı sağlığı, uçuş modu (GUIDED / AUTO / OFFBOARD).
* `GLOBAL_POSITION_INT` (#33): Enlem, boylam, irtifa (WGS84) ve zemin hızı.
* `ATTITUDE` (#30): Roll, pitch, yaw yönelimleri.
* `SYS_STATUS` (#1): Batarya yüzdesi, voltaj ve sensör sağlık bayrakları.
* `SET_POSITION_TARGET_GLOBAL_INT` (#86): Güvenlik düzlemi onaylı hedef koordinat komutu.

## 3. Donanım Güvenlik Kuralları
1. **Otonom Geofence Eşlemesi:** PyreSwarm web panelinde çizilen yasak alanlar, MAVLink üzerinden otopilotun dahili geofence parametrelerine yedek güvenlik katmanı olarak işlenir.
2. **Bağlantı Kaybı:** Radyo veya Wi-Fi kesintisinde otopilot otomatik olarak dahili RTL moduna geçer.
