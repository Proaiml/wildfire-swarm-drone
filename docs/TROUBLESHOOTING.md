# PyreSwarm — Sorun giderme

| Belirti | Olası neden | Ne yapmalı |
|---|---|---|
| Üst çubukta **Telemetri güncel değil** | Sunucu durdu ya da WebSocket koptu | Sunucu penceresinde hata var mı bakın; sayfayı yenileyin |
| Harita gri, drone'lar ızgarada | İnternet yok, harita altlığı yüklenemedi | Çalışmaya devam eder; çevrimdışı sahada yerel karo sunucusu gerekir |
| "Yangın modeli yüklenemedi" | `best.pt` depo kökünde yok ya da bozuk | Dosyayı geri koyun; kamera tespiti o zamana kadar kapalıdır |
| Simülasyon kamerası hiç yangın görmüyor | Tatbikat hedefi yok ya da drone hedefin üstünden geçmedi | **◇ Tatbikat hedefi** ekleyin; *Operatör gerçeklik katmanı* ile hedefleri kendi ekranınızda görün |
| MAVLink eklerken "10 s içinde heartbeat gelmedi" | Yanlış adres/port, telemetri yönlendirilmemiş, port başka programda | Adresi kontrol edin (`COM3,57600`, `udpin:0.0.0.0:14550`, `tcp:...`). Aynı UDP portunu QGroundControl de dinliyorsa QGC'de ayrı bir yönlendirme açın |
| Aynı bağlantıda iki araç karışıyor | Sistem kimliği belirtilmemiş | **Sistem kimliği** alanına aracın `SYSID_THISMAV` değerini yazın; her aracın kimliği farklı olmalı |
| **Hub kontrolüne al** reddediliyor | Uçuş öncesi kontrollerden biri geçmedi | Kartta kırmızı olan kontrole bakın: GPS fix/uydu, EKF, ev konumu, batarya %40, `FS_GCS_ENABLE`, üsse uzaklık |
| Kart **PİLOT DEVRALDI** gösteriyor | Pilot kumandadan modu değiştirdi | Beklenen davranış. Tekrar katmak için kontroller geçince yeniden *Hub kontrolüne al* |
| Kart **BAĞLANTI KOPTU** gösteriyor | 3 saniyeden uzun heartbeat gelmedi | Otopilot kendi failsafe'ini uygular; pilot dönüşü izler. Bağlantı gelince kontrolü yeniden alın |
| Otopilot kalkmıyor | Görev başlamadı, araç kollanamadı (arming check) ya da GUIDED moda geçemedi | Kartta otopilot durum mesajına bakın; aracın kendi ön-kollama kontrollerini yer istasyonunda doğrulayın |
| `SITL_BASLAT.bat` "Docker çalışmıyor" | Docker Desktop kapalı | Docker Desktop'ı açıp tekrar deneyin |
| Tatbikatta aynı yangına iki olay | İki tespit 90 m'den uzak konumlandı | Olaylardan birini *Reddet*; konum hatası kamera irtifası ve görüş açısıyla artar |
