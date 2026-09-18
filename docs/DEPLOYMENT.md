# PyreSwarm - Dağıtım ve Saha Kurulum Kılavuzu (Deployment)

## 1. Sistem Gereksinimleri
* **İşletim Sistemi:** Windows 10/11 veya Ubuntu Linux 22.04 LTS
* **Python Sürümü:** Python 3.10 veya 3.11
* **Donanım:**
  - Asgari: 8 GB RAM, 4 Çekirdek CPU
  - Önerilen (Saha Yer Kontrol İstasyonu): 16 GB RAM, NVIDIA GTX 1650 veya üzeri GPU (CUDA destekli)

## 2. Hızlı Kurulum ve Başlatma (Windows)
```cmd
git clone https://github.com/ilhan/pyreswarm.git
cd pyreswarm
pip install -r requirements.txt
BASLAT.bat
```
Tarayıcınızda otomatik olarak `http://localhost:8000` açılacaktır.

## 3. Docker ile Dağıtım (Opsiyonel)
```bash
docker build -t pyreswarm:latest .
docker run -d -p 8000:8000 pyreswarm:latest
```
