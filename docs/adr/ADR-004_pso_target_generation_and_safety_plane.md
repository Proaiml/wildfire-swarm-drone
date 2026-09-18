# ADR-004: PSO Hedef Üretimi ve Sert Güvenlik Düzlemi (Safety Plane) Ayrımı

## Durum
KABUL EDİLDİ (ACCEPTED) - Versiyon 0.1.0

## Bağlam
Klasik Parçacık Sürü Optimizasyonu (PSO) doğrudan fiziksel drone motorlarına bağlanamaz. Yapay zeka veya sezgisel algoritmanın uçuşa yasak bölgeleri (NFZ), irtifa sınırlarını, maksimum hızları veya batarya dönüş barajını ihlal etme riski vardır.

## Karar
Sistem kesin iki düzleme ayrılmıştır:
1. **Zeka Düzlemi (Intelligence Plane):** Multi-objective Goal Attainment, uzamsal kanıt füzyonu, arama haritası analizi ve 3D-PSO waypoint aday üretimi.
2. **Güvenlik/Uçuş Düzlemi (Safety Flight Plane):** Sert kısıt projeksiyonu.
   - Hiçbir yapay zeka çıktısı güvenlik düzlemini bypass edemez.
   - İrtifa kırpma ($25\text{ m} \le h \le 120\text{ m}$).
   - Hız sınırlama ($v \le 14\text{ m/s}$).
   - Shapely poligon kesişim kontrolü ile NFZ dışına güvenli projeksiyon.
   - APF ile $d_{safe} = 30\text{ m}$ ayrılma garantisi.
   - Batarya RTH rezerv kapısı ($E_{remain} \le E_{target} + E_{home} + E_{margin}$ durumunda zorunlu RTL).

## Sonuçlar
- **Güvenilirlik:** Hatalı veya aşırı agresif optimizasyon hedefleri fiziksel tehlike yaratmadan önce filtrelenir.
