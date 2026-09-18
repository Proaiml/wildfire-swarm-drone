# ADR-001: MAVSDK & Donanım Bağımsız Drone Katmanı Soyutlaması

## Durum
KABUL EDİLDİ (ACCEPTED) - Versiyon 0.1.0

## Bağlam
Fiziksel yangın söndürme ve arama operasyonlarında tek bir drone üreticisine (DJI, PX4, ArduPilot vb.) veya yalnızca simülasyona bağımlı olmak platformun endüstriyel esnekliğini kısıtlar. Farklı drone'ların ortak bir sürüde birlikte çalışabilmesi ve algoritmaların doğrudan motor kontrolcüsüne değil, yüksek seviyeli komutlara bağlanması gerekmektedir.

## Karar
`DroneAdapter` soyut temel sınıfı (ABC) oluşturulmuştur.
1. `SimulationDroneAdapter`: Yerel fizik, rüzgar ve kamera izdüşümü ile test ve benchmark'lar için deterministik adaptör.
2. `MAVSDKDroneAdapter`: PX4 ve ArduPilot otopilotları için MAVLink standardını uygulayan adaptör. Gerçek donanım doğrulaması henüz saha şartlarında tamamlanmadığı için `PARTIALLY_VALIDATED` olarak etiketlenmiştir.

## Sonuçlar
- **Olumlu:** Algoritmalar, güvenlik katmanı ve web merkezi otopilot tipinden tamamen soyutlanmıştır.
- **Sınırlama:** Gerçek MAVLink donanımında saha rüzgarı ve GPS gürültüsü laboratuvar testleri ile kalibre edilmelidir.
