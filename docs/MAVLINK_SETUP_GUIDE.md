# PyreSwarm - MAVLink Gerçek Saha Entegrasyon Kılavuzu

Bu doküman, Pixhawk, Cube, PX4 veya ArduPilot otopilotlu drone'ların PyreSwarm'a nasıl bağlanacağını açıklar. Arayüzden adım adım kullanım, uçuş öncesi kontroller ve acil durumlar için: [SAHA_KILAVUZU_TR.md](SAHA_KILAVUZU_TR.md).

> **Kısaca:** Bağlanan otopilot önce yalnızca izlenir. ArduPilot Copter, uçuş öncesi kontroller geçip operatör **Hub kontrolüne al** dediğinde sürüye katılır. PX4 bu sürümde izlenir, RTL ve iniş komutu alır; sürü kontrolüne alınmaz.

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
- Arayüzde: **+ Ekle → MAVLink otopilot**, bağlantı `COM3,57600`.

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
Sahaya çıkmadan önce gerçek ArduPilot uçuş koduyla çoklu drone denemesi için depodaki Docker kurulumu kullanılır (ArduCopter 4.5.7):
```powershell
SITL_BASLAT.bat
```
Araç *i*, `tcp:127.0.0.1:5760 + 10·i` adresinde ve sistem kimliği *i+1* ile çalışır (`5760`, `5770`, `5780`). Arayüzde **+ Ekle → MAVLink otopilot** ile ekleyin; tatbikat için **Tatbikat sentetik kamerası** kutusunu işaretleyin. API ile:
```bash
curl -X POST http://127.0.0.1:8000/api/swarm/add_drone \
     -H "Content-Type: application/json" \
     -d '{"drone_type": "mavlink", "drone_id": "SITL-1", "connection_string": "tcp:127.0.0.1:5760", "synthetic_camera": true}'
```
Kendi `sim_vehicle.py` kurulumunuz varsa `--out=udp:127.0.0.1:14550` ile yönlendirip `udpin:0.0.0.0:14550` adresini kullanabilirsiniz.

---

## 3. Otopilot Emniyet ve Güvenlik Parametreleri (Fail-Safe)

Gerçek sahada sürü uçuşu yaparken Mission Planner veya QGroundControl üzerinden şu parametreleri ayarlayınız:

1. **GUIDED mod ve bağlantı kaybı:**
   - ArduPilot: Hub, kontrol verildiğinde aracı kendisi `GUIDED` moda alır ve 4 Hz `SET_POSITION_TARGET_LOCAL_NED` hız komutları gönderir. Pilot başka bir moda geçerse hub aracı bırakır.
   - `FS_GCS_ENABLE = 1`, `FS_GCS_TIMEOUT = 5`: hub bağlantısı koparsa araç eve döner. `FS_GCS_ENABLE = 0` iken hub kontrolü kabul etmez.
   - `SYSID_THISMAV`: sürüdeki her araçta farklı olmalıdır.
   - PX4: bu sürümde Offboard ile sürü kontrolü yoktur; hub PX4 aracını izler ve RTL / iniş komutu verir.

2. **Geofence & RTL Emniyeti:**
   - `FENCE_ACTION = 1` (RTL - Sınır aşıldığında kalkış noktasına dön).
   - `FENCE_ALT_MAX = 120` (Maksimum 120m irtifa kısıtı).
   - `BATT_FS_LOW_ACT = 1` (Düşük bataryada otomatik RTL).

3. **Çarpışma Önleme:**
   - Hub, drone'lar 90 m'den yaklaştığında itme kuvveti uygular ve en az 30 m ayrılmayı hedefler (ArduPilot SITL'de arama sırasında en yakın mesafe 72,9 m ölçüldü). Bu yazılım katmanıdır; otopilotun kendi engel ve geofence güvenliğinin yerine geçmez. Kalkış noktalarını birbirinden en az 20–25 m uzak seçin.
