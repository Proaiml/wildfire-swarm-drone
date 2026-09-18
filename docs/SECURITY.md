# PyreSwarm - Güvenlik Mimarisi ve Kimlik Doğrulama (Security)

## 1. Ağ ve İletişim Güvenliği
1. **Dinamik Sürü Katılım Doğrulaması:** Rastgele ağ cihazlarının sürüye yetkisiz katılımını engellemek için `SwarmMembershipManager` HMAC/JWT token tabanlı yetkilendirme uygular (`PYRESWARM_AUTH_TOKEN_2026`).
2. **Replay Saldırısı Koruması:** Tüm telemetri paketleri mikrosaniye zaman damgası (`timestamp`) ve artan durum versiyonu (`state_version`) taşır. Bayat (>2.0 sn) paketler elenir.
3. **API Güvenliği:** REST uç noktaları CORS kısıtlamalarına tabidir. WebSockets üzerinden iletilen komutlar doğrulanır.
4. **Hassas Bilgi İzolasyonu:** API anahtarları, sertifikalar ve otopilot şifreleri kod içinde tutulmaz; `.env` dosyası üzerinden okunur.
