# Saha kılavuzu: drone'u getir, sürüye kat, yangını bul

Bu kılavuz, sahadaki bir operatörün PyreSwarm'ı baştan sona kullanması içindir. Her adımda ekranda ne göreceğinizi ve neyin sizin sorumluluğunuzda olduğunu yazar.

> **Güvenlik ilkesi.** Hub bir drone'a ancak siz *Hub kontrolüne al* dediğinizde ve uçuş öncesi kontrollerin hepsi geçtiğinde komut verir. Pilot kumandadan modu değiştirdiği anda hub geri çekilir. Hub'ın bağlantısı koparsa drone'un kendi otopilotu eve döner (RTL). Bu davranışlar gerçek ArduPilot uçuş koduyla (SITL) test edildi; ilk gerçek uçuşlarınızı yine de açık, boş bir alanda, tek araçla ve kumandası elinde bir pilotla yapın. Uçuş izni, yükseklik ve bölge kuralları (SHGM) sizin sorumluluğunuzdadır.

## 1. Başlatma

1. `BASLAT.bat` dosyasına çift tıklayın (ya da `py -3.11 run.py`). Tarayıcıda `http://localhost:8000` açılır.
2. Üst çubukta **● Telemetri bağlı** yazısını görün. Sağ panelde "Yangın modeli yüklü" yazmalıdır.
3. Varsayılan simülasyon filosu (4 drone) üste, yerde bekler. Batarya görev başlamadan harcanmaz.

## 2. Alanı hazırlama

| Düğme | Ne yapar |
|---|---|
| **▧ Arama alanı** | Haritada iki köşeye tıklayın. Sürü yalnızca bu dikdörtgende arar. |
| **⊘ Yasak bölge** / **≈ Göl / alan kapat** | En az üç köşe; *Alanı tamamla*. Drone'lar bu alanın içinden geçmez, etrafından dolaşır. |
| **Üs** | Kalkış/dönüş noktası. Kalıcı kaydedilebilir. |
| **Rüzgâr** | Hız (m/s) ve rüzgârın **estiği** yön (°, 0 = kuzeyden). Ekran kıvılcımların nereye taşınacağını yazar; artçı yangın önceliği oraya kayar. Varsayılan `config/mission_config.json` içindedir. |

## 3. Kendi drone'unuzu ekleme

**+ Ekle** düğmesine basın ve katılım türünü seçin.

### A. ArduPilot / PX4 otopilotlu drone (sürü kontrolü)

| Bağlantı | Adres örneği | Ne zaman |
|---|---|---|
| Telemetri radyosu (SiK) USB | `COM3,57600` (Windows) · `/dev/ttyUSB0,57600` (Linux) | Tek araç, klasik radyo |
| Ağ / Wi-Fi / eş bilgisayar (mavlink-router) | `udpin:0.0.0.0:14550` | Aracın telemetrisi bu bilgisayara UDP gönderiyorsa |
| QGroundControl / Mission Planner yönlendirmesi | `udpin:0.0.0.0:14551` | Pilotun yer istasyonu açıkken aynı telemetriyi paylaşmak için |
| ArduPilot SITL (deneme) | `tcp:127.0.0.1:5760`, `5770`, `5780` | Gerçek araç yokken (`SITL_BASLAT.bat`) |

Aynı bağlantıdan birden çok araç geliyorsa **Sistem kimliği** alanına aracın `SYSID_THISMAV` değerini yazın. Sürüdeki her aracın sistem kimliği farklı olmalıdır.

Bağlandıktan sonra drone kartı **GÖZLEM** rozetiyle görünür. Bu aşamada hub **hiçbir hareket komutu göndermez**. Kartta uçuş öncesi kontroller listelenir:

| Kontrol | Geçme koşulu |
|---|---|
| Bağlantı | Son heartbeat en fazla 2 s önce |
| Otopilot | ArduPilot Copter (PX4: şimdilik yalnızca izleme, RTL ve iniş) |
| GPS | 3D fix ve en az 6 uydu |
| EKF | Konum çözümü hazır |
| Ev (RTL) konumu | Otopilotta kayıtlı |
| Batarya | En az %40 |
| Bağlantı kaybında RTL | `FS_GCS_ENABLE` 0 değil |
| Üsse uzaklık | En fazla 5 km |

Hepsi ✓ olunca **Hub kontrolüne al**. Görev aktifse drone GUIDED moduna alınır, motorları kollanır, arama irtifasına kalkar ve sürüye katılır.

**Önerilen otopilot ayarları (ArduPilot):** `FS_GCS_ENABLE=1` (hub koparsa RTL), `FS_GCS_TIMEOUT=5`, `RTL_ALT` arazideki en yüksek engelin üstünde, `FENCE_ENABLE=1` ve `FENCE_ALT_MAX`, `FENCE_RADIUS` görev alanına göre (hub'dan bağımsız ikinci güvenlik katmanı), `SYSID_THISMAV` her araçta farklı.

### B. Başka marka / SDK'sız drone (pilot rehberliği)

**Gönüllü pilot / marka bağımsız** seçin. Hub pilota yön, hız ve irtifa önerir; drone'u pilot uçurur. Telemetri ve kamera karesi köprü uygulamasıyla gönderilir (`examples/volunteer_bridge_client.py`, `docs/DRONE_INTEGRATION_TR.md`). DJI için üreticinin Mobile SDK'sıyla yazılmış bir köprü gerekir.

### C. Kamera

Otopilotlu drone'un RTSP akışını **Kamera akışı** alanına yazın (ör. `rtsp://192.168.144.25:8554/main`). Kamera aşağı (nadir) bakmalıdır; eğik gimbal ile konum tahmini geçerli değildir. Kamera yoksa drone yine sürüyle uçar, ancak yangını o drone göremez.

## 4. Görev

1. **▶ Başlat**. Simülasyon drone'ları ve hub kontrolündeki otopilotlar kalkar.
2. Kart rollerini izleyin:

| Rol | Anlamı |
|---|---|
| Şerit tarama | Drone sektörünü kamera erişimine göre aralıklı şeritlerle tarıyor; yangın bilinmedikçe şeritleri tekrarlar (ilk yangını en hızlı bu bulur) |
| Kanıt inceleme | Şüpheli olaya en yakın iki drone alçalıp bakıyor (30 s). İkisi olayın karşı yanlarında (~44 m arayla) ve farklı irtifada (35 m / 45 m) durur |
| Kıvılcım bölgesi devriyesi | Sektörünü bir kez taramış drone, bilinen yangının rüzgâr altındaki artçı yangın konisinde en az 60 s'dir görülmemiş yere gider |
| Yeniden ziyaret | Yalnızca `adaptive` stratejide: en uzun süredir görülmeyen yere gider |

3. **Son görülme** katmanı: harita üstündeki turuncu ton, bir yerin ne kadar süredir görülmediğini gösterir (koyu = uzun süredir görülmedi). Kapsama yüzdesi alt çubukta yazar.
4. **Olay merkezi**: şüpheli olaylar burada. *Teyit et*, *Reddet*, *Tamamlandı*, *Alanı kapat*. Hub hiçbir olayı kendi kendine teyit etmez.
5. **⏸ Duraklat**: drone'lar yerinde bekler. **Tüm filo RTL**: hub kontrolündeki bütün drone'lar eve döner.

## 5. Acil durumlar

| Durum | Ne olur | Siz ne yaparsınız |
|---|---|---|
| Pilot kumandadan modu değiştirdi | Hub o drone'u **anında** bırakır, kartta "PİLOT DEVRALDI" | Pilot uçuşu yönetir. Tekrar katmak için *Hub kontrolüne al* |
| Hub bilgisayarı / bağlantı koptu | Otopilot GCS failsafe ile RTL yapar (hub'a ihtiyaç yok) | Pilot dönüşü izler |
| Düşük batarya | Simülasyon: dönüş mesafesine göre erken RTL. Otopilot: kendi batarya failsafe'i | Otopilotta `BATT_FS_*` ayarlı olmalı |
| Yasak bölge çizildi | Rotalar bölgenin etrafından yeniden planlanır | — |
| Drone tek başına | *RTL* ya da *İn* düğmeleri her otopilot için her zaman çalışır | — |

## 6. Tatbikat: sistem yangını ne kadar hızlı buluyor?

1. **Tatbikat** panelini açın, gecikmeyi seçin (0 = hemen, 120 = görevin ikinci dakikasında tutuşur).
2. **◇ Tatbikat hedefi** ve haritaya tıklayın. Hedef gizlidir; hub'ın planlayıcısı onu hiçbir zaman görmez, yalnızca kamera görürse olay oluşur.
3. Panelde tablo her hedef için tutuşma, tespit anı ve **tespit süresini** gösterir. *Operatör gerçeklik katmanı* ile gizli hedefleri yalnızca kendi ekranınızda görebilirsiniz.

Gerçek otopilotlarla tatbikat için `SITL_BASLAT.bat` çalıştırın, drone'ları eklerken **Tatbikat sentetik kamerası** kutusunu işaretleyin.
