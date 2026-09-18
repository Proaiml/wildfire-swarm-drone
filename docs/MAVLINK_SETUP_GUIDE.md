# PyreSwarm - MAVLink Gerçek Saha Entegrasyon Kılavuzu

Bu doküman, Pixhawk, Cube, PX4 veya ArduPilot otopilotlu profesyonel endüstriyel drone'ların **PyreSwarm Sürü Yönetim Sistemi**'ne fiziksel sahada nasıl bağlanacağını açıklar.

---

## 1. Donanım ve Haberleşme Mimarisi

```
  +-----------------------+                    +------------------------------------+
  |   Fiziksel Drone      |                    |     PyreSwarm GCS Sunucusu         |
  |  (Pixhawk / PX4)      |                    | (Yer Kontrol İstasyonu / Laptop)   |
  |                       |                    |                                    |
  |  Companion Computer   |  WiFi / 4G LTE /   | MAVLink Sürücüsü                   |
  | (Jetson / RPi / SiK)  |<==================>| (udpin:0.0.0.0:14550)             |
  |                       |  Telemetri Radyosu |                                    |
  | Termal/RGB Kamera     |                    | YOLOv8 Yangın Tespit Motoru        |
  +-----------------------+                    +------------------------------------+
```

---

## 2. Bağlantı Yöntemleri

### A. Yerel Telemetri Radyosu (SiK Radio 433 MHz / 915 MHz)
Laptopunuza USB ile takılan standart telemetri alıcısı için:
- Windows'ta COM portu tespit edin (Örn: `COM3`, Baud: `57600`).
- Sürücü başlatma parametresi:
  ```python
  from hardware.mavlink_drone import MAVLinkDrone
  drone = MAVLinkDrone(drone_id="PIXHAWK-01", connection_string="COM3,57600")
  drone.connect()
  ```

### B. WiFi veya 4G/LTE Companion Computer (Raspberry Pi / Jetson)
Drone üzerindeki tek kart bilgisayarda `mavproxy` veya `mavp2p` çalıştırılarak telemetri yer istasyonunun IP adresine UDP paketi olarak yönlendirilir:
```bash
# Drone üzerindeki RPi / Jetson terminalinde:
mavproxy.py --master=/dev/ttyTHS1,921600 --out=udp:YER_ISTASYONU_IP:14550
```
Yer istasyonunda PyreSwarm otomatik olarak `udpin:0.0.0.0:14550` portunu dinler:
```python
drone = MAVLinkDrone(drone_id="MAV-ALPHA", connection_string="udpin:0.0.0.0:14550")
drone.connect()
```

### C. ArduPilot SITL Simülasyonu ile Test
Sahaya çıkmadan önce yazılım döngüsünde (SITL) çoklu drone testi yapmak için:
```bash
# Drone 1 (Port 14550)
sim_vehicle.py -v ArduCopter -I 0 --out=udp:127.0.0.1:14550

# Drone 2 (Port 14560)
sim_vehicle.py -v ArduCopter -I 1 --out=udp:127.0.0.1:14560
```
Web arayüzünden veya API'den tek tıkla kaydedilebilir:
```bash
curl -X POST http://localhost:8000/api/swarm/register_mavlink \
     -H "Content-Type: application/json" \
     -d '{"drone_id": "SITL-DRONE-01", "connection_string": "udpin:0.0.0.0:14550"}'
```

---

## 3. Otopilot Emniyet ve Güvenlik Parametreleri (Fail-Safe)

Gerçek sahada sürü uçuşu yaparken Mission Planner veya QGroundControl üzerinden şu parametreleri ayarlayınız:

1. **GUIDED / OFFBOARD Mod Yetkisi:**
   - ArduPilot: Uçuş modu `GUIDED` olarak ayarlanmalıdır. PyreSwarm'ın gönderdiği `SET_POSITION_TARGET_LOCAL_NED` hız komutları bu modda işlenir.
   - PX4: `Offboard` modu aktif edilmelidir.

2. **Geofence & RTL Emniyeti:**
   - `FENCE_ACTION = 1` (RTL - Sınır aşıldığında kalkış noktasına dön).
   - `FENCE_ALT_MAX = 120` (Maksimum 120m irtifa kısıtı).
   - `BATT_FS_LOW_ACT = 1` (Düşük bataryada otomatik RTL).

3. **Çarpışma Önleme:**
   - PyreSwarm yazılımındaki **Artificial Potential Fields (APF)** algoritması drone'lar arasında minimum 30 metre mesafeyi otomatik korur.
