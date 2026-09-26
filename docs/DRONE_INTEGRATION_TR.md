# Gerçek drone katılımı: bağlantı, görüntü, PSO ve kabul sınırları

Araştırma tarihi: 20 Eylül 2026, güncelleme 26 Eylül 2026. **ArduPilot Copter araçları operatör onayı ve uçuş öncesi kontrollerle hub'ın sürü kontrolüne alınabilir; bu akış ArduPilot SITL ile (gerçek uçuş kodu, simüle araç) üç araçla sınandı. Gerçek araçla saha kabulü henüz yapılmadı.** Adım adım kullanım: [saha kılavuzu](SAHA_KILAVUZU_TR.md). Marka/model/firmware/SDK eşleşmesi ve fiziksel kabul testleri olmadan “her drone tak-çalıştır” denemez. Aşağıdaki “üreticinin sağladığı yol” ile “bu depoda uygulanmış bağdaştırıcı” farklı sütunlardır.

## Hangi drone, hangi bağlantı?

| Araç ailesi | Üreticinin desteklediği yol | Bu depoda çalışan yol | Henüz uygulanmayan/doğrulanmayan |
|---|---|---|---|
| PX4 çalışan Pixhawk/uyumlu otopilot | MAVLink; MAVSDK veya ROS 2 Offboard | `hardware/mavlink_drone.py` ile telemetri gözlemi, RTL ve iniş komutu; bağımsız köprüyle gönüllü rehberliği | PX4 Offboard sürü kontrolü, SITL/HIL ve fiziksel sürü uçuşu |
| ArduPilot Copter çalışan araç | MAVLink; Guided komutları | Gözlem → uçuş öncesi kontroller → operatör onayı → GUIDED kalkış ve 4 Hz hız komutlarıyla sürü; ACK, pilot devralması, bağlantı kaybında RTL (SITL ile sınandı) | Gerçek araçla saha kabulü |
| DJI MSDK V5 destekli model + destekli kumanda | Android Mobile SDK V5; model/firmware desteği resmî sürüm tablosundan seçilir | Üretici uygulaması yazılırsa ortak HTTP gönüllü arayüzüne bağlanabilir | Bu depoda DJI Android uygulaması/bağdaştırıcısı yok; MAVLink diye eklemek çalışmaz |
| DJI Pilot 2 / Dock Cloud API destekli donanım | DJI Cloud API | Henüz doğrudan bağdaştırıcı yok | Cloud API altyapısı, cihaz bağlama, MQTT/medya/kimlik işlemleri |
| Parrot ANAFI, Thermal, USA, Ai, UKR, Chuck | Linux üzerinde Olympe; Sphinx üretici simülasyonu | Olympe köprüsü yazılırsa ortak HTTP arayüzü | Bu depoda Olympe adaptörü ve cihaz kabul testi yok |
| SDK'sı veya dış telemetrisi bulunmayan tüketici drone'u | Üreticinin izin verdiği dış arayüz varsa değerlendirilir | Operatör manuel ihbar girebilir | Otomatik sürü katılımı vaat edilmez; telefon GPS'i drone GPS'i değildir |

PX4 Offboard sürekli yaşam sinyali/setpoint akışı ve mod önkoşulları ister; web sayfasının açık olması bu şartı sağlamaz. PX4 akış kesilince yapılandırılmış kayıp davranışına geçer. [PX4 Offboard](https://docs.px4.io/main/en/flight_modes/offboard)

MAVSDK Offboard, PX4 Offboard akışına yönelik bir arayüzdür. ArduPilot'a aynı mod isimlerini ve aynı kontrol varsayımlarını kopyalamayın. [MAVSDK Offboard](https://mavsdk.mavlink.io/main/en/cpp/guide/offboard.html), [ArduPilot Guided komutları](https://ardupilot.org/dev/docs/copter-commands-in-guided-mode.html)

DJI model listesi firmware ve SDK sürümüyle değişir. Tam model + kumanda + Android sürümünü bu resmî kaynaklarla eşleştirin; yalnızca marka adına göre uyumluluk vermeyin. [DJI MSDK V5 resmî örneği ve sürümleri](https://github.com/dji-sdk/Mobile-SDK-Android-V5), [DJI MSDK tanıtımı](https://developer.dji.com/doc/mobile-sdk-tutorial/en/basic-introduction/msdk-introduction.html), [DJI Cloud API](https://developer.dji.com/cloud-api/)

Parrot'un belgeleri desteklediği ANAFI ailesini, Linux gereksinimini ve Sphinx test yolunu listeler. Bunlar üretici yetenekleridir; PyreSwarm'da fiziksel olarak test edilmiş cihaz listesi değildir. [Parrot Olympe](https://developer.parrot.com/docs/olympe/index.html)

## Yerel kurulumu yeniden üretme

Windows/Python 3.11:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn web.app:app --host 127.0.0.1 --port 8000
```

Model `best.pt` depo kökünde olmalıdır. Yüklenemediğinde arayüz bunu bildirir; algılama başarısı uydurulmaz. `BASLAT.bat` mevcut kurulum için kısayoldur. Karşılaştırma için ayrıca `requirements-benchmark.txt` gerekir. Bu dosya MEALPY uygulama sürümünü sabitler; donanım/CUDA/sürücülerin aynı olduğunu garanti etmez.

## Sahaya gelen gönüllüyü ekleme

1. Operatör pilot/araç kimliğini, üretici modelini, batarya durumunu ve göreve uygunluğunu kontrol eder. Hub'ın mevcut formu bu kontrollerin yerine geçmez.
2. Üretici SDK'sını kullanan yerel köprü, **drone'un** GPS, kamera yönü, irtifa referansı ve bataryasını alır. Saatler UTC ile eşlenir. Kayıt düğmesine basmak tek başına telemetri üretmez.
3. **Ekle → Gönüllü pilot** formunda gerçek hız/irtifa/kamera HFOV sınırlarını girin. Dönen `VOLUNTEER_...` kimliğini köprüye verin; programlı kayıt için `examples/volunteer_bridge_client.py` içindeki `HubClient.register` kullanılabilir.
4. En az 1 Hz yeni telemetri gönderin. Sadece yenilenen ölçümler gönderilir; eski koordinata yeni zaman etiketi yapıştırılmaz. Üç saniyeyi aşan veri ve tekrar paket reddedilir.
5. Nadir kameranın JPEG'i ile **aynı çekim anındaki** drone pozu `/api/volunteer/{id}/observation` adresine gider. Sunucu kabulü `inference_pending` döndürür; bu bir yangın tespiti değildir. Model sonucu daha sonra olay merkezinde oluşur.
6. Pilot `/api/volunteer/{id}/guidance` yanıtından yön/hız/irtifa önerisini ve waypoint'i görür. `advisory_only: true` motor komutu olmadığını belirtir. Kayıp/eski telemetri, düşük batarya veya duraklatmada yeni rehberlik kullanılmaz.
7. Görev bittiğinde pilot kendi kumandasından dönüş/inişi yönetir; sonra kaydı filodan çıkarın. Mevcut web RTL düğmesi fiziksel araçta kanıtlanmış otomatik dönüş değildir.

`HubClient.send_observation(measurement, jpeg_bytes, heading)` yeni kare için kullanılabilir. Aynı `captured_at` önce `/telemetry`, sonra `/observation` olarak iki kez gönderilmez; gözlem isteği pozu zaten içerir. Aradaki yeni telemetri örnekleri `/telemetry` ile gönderilebilir.

```json
{
  "lat": 37.0, "lon": 28.0, "alt": 50.0,
  "battery": 82.0, "captured_at": 1790000000.0,
  "heading": 90.0, "nadir_camera": true,
  "jpeg_base64": "GERCEK_JPEG_BASE64"
}
```

Bu bir şema örneğidir; sabit zamanı/base64 metnini gerçek istek olarak kullanmayın. JPEG en fazla 3840×2160 ve base64 alanı 2.8 milyon karakterdir. Poz ve kare eşlenerek saklanır; sonraki telemetri eski karenin konumunu değiştirmez. Aynı kare yeniden algılama sayacı üretmek için tekrar kullanılmaz. Gönüllü RTSP URL'si görüntüleme amacıyla bulunabilir, fakat zaman eşlenmiş kanıt yolu bu gözlem endpoint'idir.

**İrtifa kritik:** kamera yer izdüşümü yerden yüksekliği gerektirir. MAVLink `relative_alt`, kalkış noktasına göre yüksekliktir; engebeli arazide AGL değildir. Dönüşüm için arazi/rangefinder gerekir. Mevcut görüntü konumlandırma nadir ve yaklaşık düz zemin varsayar; eğik gimbal veya bilinmeyen irtifa referansını bu sözleşmeye doğruymuş gibi göndermeyin. HFOV araç kapasitesinden algılayıcıya aktarılır. Kalibrasyonsuz GPS tahmini teyit edilmiş hedef değildir.

## Sosyal PSO gerçekte nasıl çalışıyor?

Bu uygulama **merkezî hub PSO**'sudur; drone'lar arasında doğrudan mesh/peer-to-peer protokol uygulanmış değildir. Telemetri ve gözlemler merkeze gelir, `pbest` ile `gbest` burada güncellenir, kısıtlı hız önerileri burada hesaplanır. Arayüz ortak gözlemi hangi drone'un ürettiğini gösterir.

Kişisel en iyi gözlem bilişsel terimi, paylaşılan iyi gözlem sosyal terimi besler. Gözlem yoksa gizli hedef koordinatı kullanılamaz; kapsama rotası aramayı sürdürür. Yakındaki en fazla iki drone incelemeye ayrılır, diğerleri başka başlangıç/artçı yangınları kaçırmamak için sektörlerini arar. Hız/ivme, kapasite, ayrılma ve alan kısıtları çekimden sonra uygulanır. Eski ortak gözlem temizlenir. Çözülen/reddedilen olay, 60 saniyelik tekrar bastırma sonrası yeni gözlemle yeni aday oluşturabilir; alan özellikle kapatılmışsa aranmaz.

**Henüz kanıtlanmayan:** farklı kamera/modeller arasında skor kalibrasyonu, en iyi drone'dan hız/irtifa parametrelerinin performans garantili transferi, dağıtık haberleşme, kopuk ağda ortak tutarlılık. Yüksek tek-kare güven puanı “en hızlı ve en güvenilir yangın bulucu” ile aynı ölçü değildir. Yayınlanan arama benchmark'ı bunları ölçtüğünü iddia etmez.

## MAVLink kurulumu

Otopilotun telemetri çıkışını hub bilgisayarındaki kullanılmayan UDP porta yönlendirin. UI'da **MAVLink otopilot** seçip örneğin `udpin:127.0.0.1:14550` bağlantısını verin. Bağlantı adresleri, uçuş öncesi kontroller ve önerilen otopilot ayarları için [saha kılavuzu](SAHA_KILAVUZU_TR.md). Bu adres ancak gerçekten o porta yönlendirilmiş yerel telemetri için doğrudur. Ağdaki araç için router/seri ayarı gerekir. Birden fazla araçta sistem kimliği ve akış yönlendirmesi ayrı doğrulanmalıdır; aynı karışık bağlantıya rastgele araç kaydı açmayın.

Önce yerde gerçek heartbeat, poz, NED→ENU hız yönleri, batarya, disconnect ve reconnect gözlenir. Sonraki aşama üretici SITL'idir. [ArduPilot SITL kurulumu](https://ardupilot.org/dev/docs/setting-up-sitl-on-linux.html), [SITL kullanım örnekleri](https://ardupilot.org/dev/docs/using-sitl-for-ardupilot-testing.html), [MAVLink arayüzü](https://ardupilot.org/dev/docs/mavlink-commands.html)

## Uçtan uca kabul matrisi

| Aşama | Geçme kanıtı | Bu sürümün durumu |
|---|---|---|
| Dahili simülasyon | Tekrarlanabilir rota/sensör/ayrılma kayıtları | Test ve ham deney kayıtları depoda |
| HTTP köprü | Yeni poz+kare kabulü, eski/tekrar veri reddi, tek kare tek işlem | Otomatik sözleşme testleri var |
| Gerçek model | Gerçek `best.pt` çağrıları, model hash'i, kaçırmaların kaydı | Fotoğraf tabanlı simülasyonda çalıştırıldı; hava görüntüsü doğrulaması değil |
| Üretici SDK | Gerçek cihazdan telemetri+kare zaman eşleme | Model başına yapılmalı; hazır DJI/Parrot adaptörü yok |
| SITL/HIL | GPS/EKF hazır olmadan kontrol reddi, komut ACK, pilot override, hub bağlantı kaybında RTL, çoklu araç | ArduPilot Copter 4.5.7 SITL, 3 araç: `tools/sitl/sitl_swarm_trial.py`, `artifacts/sitl_trial/result.json`. HIL yapılmadı |
| Kontrol sahası | Önce tek araç, sonra kontrollü çoklu araç; uçuş logları ve olay incelemesi | Yapılmadı |
| Operasyon dağıtımı | Kimlik/rol, TLS, denetim kaydı, kalıcı görev verisi, yedeklilik | Tamamlanmadı; localhost'u internete açmak çözüm değil |
| Yangın/SAR saha başarımı | Bağımsız gerçek veri, hedef bazlı recall, yanlış alarm/saat, algılama gecikmesi | Yangın için eksik; gerçek SAR modeli henüz yok |

Kontrol sahası ve saha başarımı aşamaları tamamlanmadan sistem, operatör ve pilot gözetimi olmadan çalışan bağımsız bir otonom sürü olarak kullanılmamalıdır. Önerilen sıra: SITL (`SITL_BASLAT.bat`) → tek gerçek araç, açık alan, kumandası elinde pilot → iki araç → görev.
