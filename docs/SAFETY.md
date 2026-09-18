# PyreSwarm - Operasyonel Uçuş Emniyeti (Safety Guidelines)

## 1. Altın Emniyet İlkeleri
1. **Güvenlik Düzlemi Üstünlüğü:** Hiçbir yapay zeka çıktısı, PSO sezgiseli veya operatör manuel hedefi `SafetyFlightPlane` kısıtlarını çiğneyemez.
2. **Uçuşa Yasak Bölge (NFZ) Projeksiyonu:** Bir waypoint NFZ içine denk gelirse derhal en yakın güvenli sınır noktasına çekilir; uçuş hattı yasak poligonu kesiyorsa drone derhal durdurulur.
3. **APF Çarpışma Önleme:** Sürü içindeki herhangi iki hava aracı arasındaki mesafe $30\text{ metre}$ altına inemez. İtki vektörleri otonom olarak ayrılmayı sağlar.
4. **Batarya İflas Koruması:** Üsse dönüş enerjisi + iniş enerjisi + $\%20$ güvenlik payı sağlandığı anda drone derhal RTL moduna geçer ve arama görevinden muaf tutulur.
5. **İletişim Kaybı Fail-Safe:** 15 saniyeden uzun süre kalp atışı alınamayan drone otomatik olarak otopilot dahili emniyet moduna (Failsafe RTL / Land) geçer.
