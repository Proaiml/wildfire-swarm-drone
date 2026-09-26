# PyreSwarm — Yazılım güvenliği

## Bugünkü durum

| Konu | Uygulama |
|---|---|
| Ağ erişimi | Sunucu yalnızca `127.0.0.1` üzerinde dinler (`run.py`); `Host` başlığı `localhost` / `127.0.0.1` dışında reddedilir |
| Çapraz kaynak | CORS yalnızca `http://localhost:8000` ve `http://127.0.0.1:8000`; başka kaynaktan gelen değiştirici istekler 403 |
| Girdi doğrulama | Tüm istekler şemaya göre doğrulanır; tanımsız alan, NaN/sonsuz sayı, aralık dışı koordinat ve irtifa reddedilir |
| Gönüllü telemetrisi | 3 saniyeden eski, yinelenen ya da gelecekten gelen ölçüm reddedilir; hub konum uydurmaz |
| Otopilot komutları | Hareket komutu yalnızca operatör **Hub kontrolüne al** dediğinde ve uçuş öncesi kontroller geçtiğinde gönderilir |
| Gizli bilgiler | Depoda API anahtarı ya da parola yoktur |

## Kimlik doğrulama yok

Hub'da kullanıcı girişi, rol ve TLS yoktur; güvenlik, sunucunun yalnızca bu bilgisayardan erişilebilir olmasına dayanır. Hub'ı başka bilgisayarlara açmak için önce şunlar gerekir:

- kullanıcı girişi ve roller (izleyici / operatör),
- TLS (HTTPS / WSS),
- denetim kaydı (kim hangi drone'u kontrole aldı, hangi olayı teyit etti),
- gönüllü köprüleri için cihaz başına anahtar.

Sunucuyu `0.0.0.0` üzerinde başlatmak ya da bir tünelle internete açmak bu gereksinimleri karşılamaz.

`src/` altındaki `SwarmMembershipManager` gibi eski katmanlar web hub'ının kullandığı yol değildir.
