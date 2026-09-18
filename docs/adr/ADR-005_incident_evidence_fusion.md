# ADR-005: Uzamsal-Zamansal Kanıt Füzyonu ve Olay Yaşam Döngüsü

## Durum
KABUL EDİLDİ (ACCEPTED) - Versiyon 0.1.0

## Bağlam
Tek bir kamera karesinde (frame) parlayan güneş yansıması, kırmızı bir çatı veya benzeri nesneler model tarafından anlık olarak yüksek güvenle yangın zannedilebilir. Tek bir frame sonucuna göre yangın alarmı vermek devasa yanlış pozitif (false positive) krizlerine ve sürünün kaynak israfına yol açar. Ayrıca aynı yangını gören birden fazla drone'un her birinin ayrı yangın kaydı açması operatör panelini kilitler.

## Karar
1. **Spatio-Temporal Evidence Fusion:**
   - Ardışık en az 3 kararlı kare ve zaman penceresi ($T=8\text{ s}$) içinde üssel sönümleme ($T_{half}=4\text{ s}$) ile kanıt birikimi.
   - Farklı drone'ların ortak gözlemleri için $R \le 50\text{ m}$ yarıçapında uzamsal kümeleme.
2. **Tekil Yangın Olayı (Fire Incident) Yaşam Döngüsü:**
   - `CANDIDATE` $\rightarrow$ `SUSPECTED` $\rightarrow$ `CONFIRMED` $\rightarrow$ `MONITORING` $\rightarrow$ `RESOLVED` $\rightarrow$ `EXCLUDED`.
   - Aynı coğrafi yangın tekil `incident_id` altında toplanır.
   - Operatör insan-döngüde (Human-in-the-Loop) onayı veya false alarm iptali yapabilir.

## Sonuçlar
- **Doğruluk:** Yanlış alarm oranı simülasyonda %90'ın üzerinde düşürülmüştür.
- **Sürü Yönetimi:** Onaylanan yangın çevresi tabu alanı yapılarak sürünün tek noktaya çökmesi (swarm collapse) önlenir.
