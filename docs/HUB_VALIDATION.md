# Hub doğrulama raporu — 19 Eylül 2026

## Sonuç

Windows / Python 3.11 üzerinde **89 test geçti**. Başlangıçtaki 57 teste, aktif web/hub akışına yönelik 32 regresyon ve parametrik kontrol eklendi. JUnit kaydı: `artifacts/hub_validation/tests.xml`.

```powershell
py -3.11 -m pytest tests -q --disable-warnings --junitxml=artifacts/hub_validation/tests.xml
py -3.11 scripts/validate_hub.py
node --check web/static/js/dashboard.js
git diff --check
```

JavaScript sözdizimi ve diff boşluk kontrolleri başarılıdır. Tarayıcıda görev başlatma/duraklatma, telemetride hareket, SAR'a geçiş ve kapasite bilgisiyle drone ekleme kontrol edildi. Önceki taşan üst çubuğun yerine harita/filo/olay düzeni görsel olarak incelendi. Mobil ekran ve gerçek donanım kabul testi yapılmadı.

## PSO doğrulaması

`test_pso_social_term_causally_controls_evidence_attraction`: aynı koşullarda sosyal terim sıfırlanınca kanıta çekim yok; etkinleştirildiğinde hedef yönünde hareket var.

`test_pso_inertia_affects_patrol_motion`: atalet değişikliği devriye hızını değiştiriyor. PSO hem devriye hem inceleme adımında kullanılıyor; kanıt yokken pbest/gbest yangın çekimi kapalı ve kapsama terimi etkin. Bu, kısıtlı/hibrit PSO'dur; saf klasik PSO veya ölçülmüş algoritmik üstünlük iddiası değildir.

## 600 saniyelik deterministik senaryo

Dört simülasyon drone'u, iki gizli SAR hedefi, bir kapalı alan, tohum 2026. Aktif web yöneticisinin `tick` ve `perceive_once` yolları kullanıldı. Duvar saati yerine simülasyon süresine göre inceleme süresi dolumu sınandı.

| Ölçüm | Sonuç |
|---|---:|
| Bulunan aday hedef | 2 / 2 |
| İlk aday tespit zamanı | 176 s |
| Asgari yatay drone ayrılması | 43.899 m |
| En yüksek hız | 10.000 m/s |
| Kapalı alan içi konum örneği | 0 |
| Toplam uçulan mesafe | 22693.2 m |
| Otomatik operatör teyidi | 0 |

Ham iz ve sonuçlar: `artifacts/hub_validation/scenario.json`. Bu sentetik sensörlü tek deterministik senaryodur; gerçek kişi algılama başarımı veya bütün koşullarda çarpışmazlık kanıtı değildir.

## Diğer kapsanan regresyonlar

- Başlangıç/senaryo gerçeğinin keşfedilmiş olaylara sızmaması.
- Güven skoru yüksek olsa bile operatör teyidi gerekliliği; ikinci düşük skorlu olayın kaybolmaması.
- SAR/yangın görev ve algılama ayrımı; gerçek kişi modeli bulunmadığının belirtilmesi.
- Gönüllü konumunun uydurulmaması, ölçüm zaman aşımı ve tekrar gönderim reddi.
- Kapasite ağırlıklı sektör paylaşımı, hız ve irtifa sınırları.
- Kademeli kalkış, yere inince hareketin sonlanması, kamera dışı kontrol döngüsü.
- Başarısız/yinelenen drone kaydının reddi; fiziksel köprüye yanlışlıkla uçuş komutu verilmemesi.
- Devriyede ilerleme, dört drone ile beş dakika ayrılma, en fazla iki inceleyici.
- Poligon sınırı/yol kesişimi, dolanma rotası, kapalı alanda kalınca bekleme.
- RTL/inişin duraklatma tarafından bozulmaması; uzak üs için batarya rezervi.
- MAVLink hız ekseni/dikey işaret, LAND komutu ve yaw-rate maskesi.
- API konum/tür/alan doğrulaması ve çapraz kaynaklı kontrol isteğinin reddi.

## Kanıt sınırı

SITL/HIL, fiziksel uçuş, gerçek kamera kalibrasyonu, ağ arızasında otopilot tepkisi, çok markalı SDK entegrasyonu, termal insan modeli, saha precision/recall ve üretim güvenlik kabulü yapılmadı. Bunların yerine geçecek bir başarı iddiası yoktur. Eski PDF ve benchmark raporları bu sürümün doğrulama raporu olarak kullanılmamalıdır.
