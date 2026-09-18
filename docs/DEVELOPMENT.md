# PyreSwarm - Geliştirici Kılavuzu (Development)

## 1. Proje Mimarisi ve Paket Hiyerarşisi
```text
src/
├── common/        # Koordinat ve jeodezik metrik dönüşümleri (ENU, WGS84)
├── perception/    # YOLOv8 dedektör, Mock dedektör ve uzamsal-zamansal füzyon
├── drones/        # DroneState, DroneAdapter, SimulationAdapter, MAVSDK
├── safety/        # SafetyFlightPlane, Geofence, APF Collision, Battery Failsafe
├── swarm/         # Goal Attainment Fitness, SwarmDiversityManager, 3D-PSO Optimizer
├── incidents/     # FireIncident yaşam döngüsü ve tekilleştirme
├── mapping/       # SearchMap hücre ızgarası, FOV ayak izi ve kapsama analizi
└── communication/ # MessageBus, CommunicationLossHandler, SwarmMembershipManager
```

## 2. Geliştirme Kuralları
1. **Type Hints:** Tüm yeni fonksiyonlar ve veri modelleri eksiksiz type-hint taşımalıdır.
2. **Sıfır Sessiz Hata:** Kritik emniyet ve matematik bloklarında çıplak `except: pass` kesinlikle yasaktır.
3. **Regresyon Koruması:** Yeni kod eklenmeden veya refactor edilmeden önce ilgili testler yazılmalıdır (`pytest tests/`).
