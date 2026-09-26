# PyreSwarm — Uçuş güvenliği

Hub'ın güvenlik davranışları ve bunların nerede sınandığı. Sahada adım adım kullanım için: [SAHA_KILAVUZU_TR.md](SAHA_KILAVUZU_TR.md).

## Katmanlar

1. **Otopilot kendi güvenliğini korur.** Hub ne yaparsa yapsın ArduPilot'un failsafe'leri (GCS bağlantı kaybı, batarya, geofence) çalışmaya devam eder. Hub bunları kapatmaz, yerine geçmez.
2. **Hub, izin olmadan komut vermez.** Bağlanan otopilot yalnızca izlenir. Hareket komutu için uçuş öncesi kontrollerin hepsi geçmeli ve operatör **Hub kontrolüne al** demelidir.
3. **Pilot her zaman önce gelir.** Pilot kumandadan modu değiştirdiği anda hub o aracı bırakır.

## Davranışlar

| Durum | Hub ne yapar | Nerede sınandı |
|---|---|---|
| GPS fix / EKF / ev konumu yokken kontrol isteği | Reddeder, eksik kontrolü adıyla gösterir | Birim test + ArduPilot SITL |
| `FS_GCS_ENABLE = 0` | Kontrolü reddeder (hub koparsa aracın eve dönmesi gerekir) | Birim test |
| PX4 aracı | İzler; RTL ve iniş komutu verir, sürü kontrolüne almaz | Birim test |
| Pilot kumandadan mod değiştirir | Aracı hemen bırakır (SITL'de 0,1 s), komut göndermez | Birim test + SITL |
| Hub'ın kendi komut verdiği mod değişimi (ör. RTL) | Pilot devralması sanmaz | Birim test |
| 3 saniye heartbeat yok | Aracı "bağlantı koptu" sayar, komut göndermeyi keser | Birim test |
| Hub bağlantısı tamamen koptu | Otopilot kendi GCS failsafe'iyle eve döner (SITL'de 4,4 s sonra RTL) | SITL |
| Duraklat | Kontroldeki otopilotlara sıfır hız gönderir | Birim test |
| Tüm filo RTL | Kontroldeki ve etkin otopilotlar RTL'e geçer | Birim test + SITL |
| Yasak bölge / göl | Rotalar bölgenin etrafından planlanır; durma mesafesi içinde bölge varsa hız sıfırlanır | Birim test |
| Drone'lar arası mesafe | 90 m içinde itme kuvveti, hedef en az 30 m; iki inceleyici olayın karşı yanlarında ve farklı irtifada | Birim test + SITL (arama sırasında en az 72,9 m) |
| Düşük batarya (simülasyon) | Üsse dönüş mesafesine göre erken RTL | Birim test |
| Düşük batarya (otopilot) | Otopilotun kendi `BATT_FS_*` ayarı | Otopilot ayarı |

## Bilinen sınırlar

- Doğrulama gerçek ArduPilot uçuş koduyla (SITL) yapıldı. **Gerçek araçla saha kabulü yapılmadı.**
- Kalkışta araçlar kendi kalkış noktalarından dikey yükselir; kalkış noktalarını birbirinden yeterince uzak (en az 20–25 m) seçin.
- Engel kaçınma yalnızca haritada çizilen 2B alanlar içindir; ağaç, direk, arazi yüksekliği bilinmez. Arama irtifasını bölgedeki en yüksek engelin üstünde seçin.
- `relative_alt` kalkış noktasına göre irtifadır; engebeli arazide yerden yükseklik değildir.
