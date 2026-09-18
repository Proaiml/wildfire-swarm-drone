"""
PyreSwarm - Ana Başlatıcı (Main Launcher)
Web Görev Kontrol Merkezini ve Sürü Drone Koordinatörünü tek komutla başlatır.
"""

import os
import sys
import uvicorn

def main():
    print("""
    ========================================================================
     🔥 PYRESWARM: OTONOM SÜRÜ DRONE YANGIN TESPİT & KOORDİNASYON SİSTEMİ 🔥
    ========================================================================
     [+] Çekirdek: 3D-PSO (Particle Swarm Optimization) & Artificial Potential Fields
     [+] Yapay Zeka: YOLOv8 (best.pt - Yangın & Duman Tespiti)
     [+] Donanım Desteği: Pixhawk/PX4/ArduPilot MAVLink, DJI & Simülatör
     [+] Özel Yetenek: Dinamik Gönüllü/Vatandaş Drone Katılımı & Bölge Kapatma
    ========================================================================
     [>>] Görev Kontrol İstasyonu (GCS) Web Arayüzü Başlatılıyor:
          URL: http://localhost:8000
    ========================================================================
    """)

    # Web sunucusunu başlat
    uvicorn.run(
        "web.app:app",
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )

if __name__ == "__main__":
    main()
