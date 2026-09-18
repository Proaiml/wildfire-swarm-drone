# PyreSwarm - Simülasyon Rehberi ve Hata Enjeksiyonu (Simulation)

## 1. Simülasyon Çalıştırma
Deterministik simülasyon motoru komut satırından tohum parametresi (`--seed`) ile başlatılır:

```bash
python -m simulation.simulator --drones 5 --area-km2 4.0 --fires 2 --seed 42
```
Aynı seed parametresi verildiğinde tüm drone yörüngeleri, yangın konumları ve tespit süreleri birebir aynı sonucu üretir.

## 2. Hata Enjeksiyonu (Fault Injection) Senaryoları
Simülasyon motoru aşağıdaki saha krizlerini simüle edebilir:
1. `GPS_LOSS`: Drone GPS kilidini kaybeder; pozisyon tahmini durur ve yerinde acil inişe geçer.
2. `COMM_LOSS`: Telemetri linki kopar; `CommunicationLossHandler` sürü optimizasyonunu kilitlemeden drone'u `DISCONNECTED` yapar.
3. `CRITICAL_BATTERY`: Batarya seviyesi ani deşarj ile $\%10$'a düşürülür; otonom RTL tetiklenir.
4. `CAMERA_FAILURE`: Kamera karesi çekimi durur; drone arama görevinden çekilerek devriye moduna alınır.
