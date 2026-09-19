import sys
import os
import threading
import webbrowser
import time
import uvicorn

# Windows konsol Unicode uyumluluğu
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

def open_browser():
    time.sleep(1.5)
    webbrowser.open("http://localhost:8000")

def main():
    print("""
    ========================================================================
     [***] PYRESWARM: OTONOM SURU DRONE YANGIN TESPIT VE KOORDINASYONU [***]
    ========================================================================
     [+] Cekirdek: Kapasite bazli tarama ve kanit odakli PSO
     [+] Yapay Zeka: YOLOv8 (best.pt - Yangin ve Duman Tespiti)
     [+] Calisma: Simulator, gonullu rehberligi, MAVLink telemetri
     [+] Fiziksel otonom ucus dogrulanmadi; bu surum fiziksel ucus yonetmez
    ========================================================================
     [>>] Gorev Kontrol Istasyonu (GCS) Web Arayuzu Baslatiliyor:
          URL: http://localhost:8000
    ========================================================================
    """)

    # Tarayıcıyı arka planda otomatik aç
    threading.Thread(target=open_browser, daemon=True).start()

    # Web sunucusunu başlat
    uvicorn.run(
        "web.app:app",
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )

if __name__ == "__main__":
    main()
