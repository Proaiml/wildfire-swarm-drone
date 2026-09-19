# Ortak operasyon merkezi — kullanım ve entegrasyon

## Çalışma biçimi

`BASLAT.bat` uygulamayı yalnızca localhost üzerinde açar. Web arayüzünde yangın keşfi ve arama-kurtarma görevleri bulunur. Simülasyon filosu ile gönüllü pilot rehberliği aynı sektörel planlayıcıyı kullanır. Fiziksel MAVLink drone'ları gözlem amaçlıdır; bu sürüm fiziksel aracı arm etmez, kaldırmaz veya sürü uçuşuna otomatik katmaz.

Başlangıçtaki dört simülasyon drone'u havada bekleme senaryosudur. Yeni eklenen simülasyon drone'u yerde başlar; görev başlayınca kademeli kalkar. Düşük batarya, RTL ve iniş durumları görev başlat/duraklat işlemleriyle iptal edilmez.

## Harita ve görev

- **Arama alanı:** iki karşı köşeye tıklayın. Yerel düzlem modeli nedeniyle bir kenar en fazla 0.2 derecedir. Tüm kullanılabilir drone'lar için sektörler yeniden hesaplanır.
- **Yasak bölge / Göl-alan kapat:** en az üç köşe seçin, Alanı tamamla düğmesine basın. Kendini kesen poligon reddedilir. Her kapalı alan bu sürümde hem tarama hem uçuş dışıdır; 25 m tampon vardır. SAR sırasında su araması gerekiyorsa gölü kapatmayın.
- **İhbar:** bilinen hedef konumuna tıklayın. Bu bir operatör bildirimi olarak kaydedilir; güven skoru tek başına teyit değildir.
- **Tatbikat hedefi:** mevcut göreve göre gizli yangın veya kişi hedefi yerleştirir. Olay listesine hemen eklenmez.
- **Üs:** simülasyonu durdurur, simülasyon drone'larını yeni konuma taşır ve arama alanını sıfırlar. Gönüllü/fiziksel telemetri değiştirilmez. Kalıcı kayıt kutusu seçilmedikçe mevcut konfigürasyon dosyası değiştirilmez.
- **Sektörler:** her drone için kapasite oranında bölünmüş alanı gösterir. Bu, planlanan görev dağılımıdır; taranmış alan veya garantili algılama yüzdesi değildir.
- **Uçuş izi:** son 300 hareket örneği. Yalnızca hareket olduğunda uzar; büyük yeniden konuşlandırmalarda sıfırlanır.

Harita kütüphanesi yereldir. OSM/Esri altlıkları internet ister. Altlık erişilemiyorsa telemetri, sınırlar ve sektörler düz koordinat ızgarasında çalışmaya devam eder. Harita sağlayıcıları ziyaret edilen harita karelerini görür; çevrimdışı saha kullanımında yerel karo sunucusu gerekir.

## Olaylar

`candidate` → `confirmed` / `dismissed`; onaylanan olay `resolved` yapılabilir. Teyit operatör kararıdır. Simülasyon kaynakları açıkça işaretlenir. Olayı tamamlamak ve coğrafi alanı kapatmak ayrı işlemlerdir. Rapor JSON'u kaynak, görev türü, durum ve konum içerir.

Görev türü değişiminde eski olaylar ve optimizasyon belleği temizlenir. Önce raporu indirin. Çalışma zamanı drone kayıtları, olaylar ve çizilmiş alanlar bellektedir; sunucu yeniden başlatıldığında geri yüklenmez. Kalıcı olan yalnızca açıkça kaydedilen üs ayarıdır.

## Gönüllü katılım protokolü

1. Arayüzde **Ekle → Gönüllü pilot / marka bağımsız** seçin. Kapasite bilgilerini üretici ve görev kısıtlarına göre girin.
2. Dönen `VOLUNTEER_...` kimliği ile harici cihaz köprüsü gerçek drone telemetrisini gönderir. Telefon GPS'i drone konumu yerine kullanılmamalıdır.
3. Köprü `/api/volunteer/{id}/guidance` yanıtını pilotuna gösterir. Bu yanıt uçuş komutu değildir.

Örnek kayıt (JSON, POST `/api/swarm/register_volunteer`):

```json
{"pilot_name":"Ekip 2","lat":37.0,"lon":28.0,"alt":40,
 "capabilities":{"max_speed_ms":6,"max_altitude_m":100,"search_altitude_m":50,"camera_hfov_deg":75}}
```

Gerçek telemetriyi en az 1 Hz gönderin (POST `/api/volunteer/{id}/telemetry`):

```json
{"lat":37.001,"lon":28.002,"alt":48.0,"battery":72.0,"captured_at":1789822000.0}
```

`captured_at` gerçek ölçüm anının UTC Unix saniyesidir; örnekteki sayıyı kullanmayın. Üç saniyeden eski, yinelenen veya bir saniyeden fazla gelecek zamanlı ölçüm reddedilir; cihaz saatleri senkron olmalıdır. Üç saniyeden eski telemetride rota yanıtı `guidance: null` olur; drone yeni görev paylaşımından çıkarılır. Batarya %20 ve altında rehberlik planından çıkarılır. Her başarılı yeni telemetri güncellemesi sadece dışarıdan gelen konumu yazar; hub konum uydurmaz.

GET `/api/volunteer/{id}/guidance`:

```json
{"advisory_only":true,"telemetry_fresh":true,
 "guidance":{"target_heading_deg":90,"target_speed_ms":5,"target_altitude_m":50},
 "waypoint":[37.001,28.003]}
```

`examples/volunteer_bridge_client.py` gerçek telemetri üreten bir SDK bağdaştırıcısının kullanabileceği istemcidir. Aynı bilgisayar için hazırdır. Uzak gönüllülerin gerçek operasyona katılması için kimlik doğrulama, pilot/araç yetkilendirmesi, TLS, operatör onayı ve güvenilir ağ geçidi ayrıca gereklidir. Mevcut localhost sunucusunu internete açmak bu gereklilikleri karşılamaz.

## MAVLink

`udpin:127.0.0.1:14550` gibi bağlantılar için kimlik benzersiz olmalıdır. Bağlantı hatası filoya başarılı kayıt olarak yansımaz. NED telemetri, uygulamanın Doğu-Kuzey-Yukarı eksenine çevrilir. `relative_alt` kalkış noktasına göre irtifadır; değişken arazide AGL değildir.

SITL/HIL ve fiziksel uçuş testleri yapılmadan web üzerinden fiziksel kontrol açılmamıştır. PX4 Offboard, ArduPilot Guided, komut ACK, GPS/EKF sağlık, otopilot failsafe, bağlantı kopması, araç çakışması ve pilotun kontrolü geri alması ayrı kabul testleridir.

## Sınırlar

Sektör ağırlığı nominal görüş genişliği × hızdır; rüzgar, ağaç örtüsü, duman, kamera çözünürlüğü, termal kontrast ve hedef büyüklüğüyle kalibre edilmemiştir. Basitleştirilmiş batarya modeli ölçülmüş üretici uçuş zarfı değildir. Engel dolanma yalnızca çizilmiş 2D poligonlar içindir. Drone'u içine alan yeni bir yasak bölge veya geçişi tamamen kapatan alan, güvenli bekleme gerektirebilir; otomatik arazi/3D engel kaçışı yoktur.

SAR'da `best.pt` kullanılmaz. Sentetik kişi sensörü görev planlamasını sınar; gerçek insan algılama, canlı termal/RGB model, yanlış pozitif/negatif değerlendirmesi ve saha kanıtı gerektirir. Simülasyonda 30 m ayrılma kontrolü fiziksel uçuş sertifikası değildir.
