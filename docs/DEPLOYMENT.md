# PyreSwarm — Kurulum

## Gereksinimler

- Windows 10/11 (doğrulanan ortam) ya da Linux
- Python 3.11
- 8 GB RAM; yangın modelinin hızlı çalışması için NVIDIA GPU önerilir (yoksa CPU'da daha yavaş çalışır)
- Harita altlığı için internet (yoksa sınırlar ve drone'lar düz ızgarada gösterilir)
- Yalnızca ArduPilot SITL denemesi için: Docker Desktop

## Kurulum ve başlatma

```powershell
git clone https://github.com/Proaiml/wildfire-swarm-drone.git
cd wildfire-swarm-drone
py -3.11 -m pip install -r requirements.txt
py -3.11 run.py
```

Windows'ta `BASLAT.bat` aynı işi yapar. Arayüz: http://127.0.0.1:8000. Sunucu yalnızca bu bilgisayardan erişilebilir (bkz. [SECURITY.md](SECURITY.md)).

`best.pt` (yangın modeli) depo kökünde olmalıdır.

## Gerçek otopilot olmadan deneme: ArduPilot SITL

```powershell
SITL_BASLAT.bat          # ilk seferde imajı derler (10-20 dk), sonra 3 ArduCopter başlatır
```

Hub'da **+ Ekle → MAVLink otopilot** ile `tcp:127.0.0.1:5760`, `5770`, `5780` adreslerini ekleyin. Otomatik kabul denemesi:

```powershell
py -3.11 tools/sitl/sitl_swarm_trial.py
```

Durdurmak için: `docker rm -f pyreswarm-sitl`.

## Sahada

Drone bağlama, otopilot ayarları, uçuş öncesi kontroller ve acil durumlar: [SAHA_KILAVUZU_TR.md](SAHA_KILAVUZU_TR.md).
