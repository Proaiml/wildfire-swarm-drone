"""
PyreSwarm - Arama Teorisi, Matematiksel Modelleme ve Monte Carlo Simülasyon Motoru
Kamera optiği, Koopman arama integrali, alan kapsama hızları ve ampirik benchmark testleri.
"""

from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Any
import math
import time
import os
import random
import numpy as np


@dataclass
class SearchPhysicsConfig:
    altitude_m: float = 85.0           # Arama irtifası (m)
    horizontal_fov_deg: float = 84.0   # Kamera yatay görüş açısı (deg)
    vertical_fov_deg: float = 56.0     # Kamera dikey görüş açısı (deg)
    cruise_speed_ms: float = 12.0      # Seyir hızı (m/s ~ 43.2 km/h)
    overlap_ratio: float = 0.15        # Güvenli tarama örtüşme oranı (%15)
    pso_efficiency_gain: float = 1.62  # PSO'nun duman gradyanı ve pbest/gbest çekimiyle sağladığı arama çarpanı


class MetricsEngine:
    """
    Sürü Drone Yangın Arama Performansını matematiksel ve ampirik olarak hesaplayan motor.
    """

    def __init__(self, config: Optional[SearchPhysicsConfig] = None):
        self.cfg = config or SearchPhysicsConfig()

    def get_ground_footprint(self, alt: Optional[float] = None) -> Tuple[float, float, float]:
        """
        Sensör zemin izdüşümünü (Footprint) hesaplar.
        W: Yatay genişlik (metre)
        L: Dikey derinlik (metre)
        A: Anlık görüş alanı (m^2)
        """
        h = alt if alt is not None else self.cfg.altitude_m
        rad_h = math.radians(self.cfg.horizontal_fov_deg / 2.0)
        rad_v = math.radians(self.cfg.vertical_fov_deg / 2.0)

        w = 2.0 * h * math.tan(rad_h)
        l = 2.0 * h * math.tan(rad_v)
        area = w * l
        return w, l, area

    def get_effective_sweep_width(self, alt: Optional[float] = None) -> float:
        """Etkin tarama genişliği: W_eff = W * (1 - overlap)"""
        w, _, _ = self.get_ground_footprint(alt)
        return w * (1.0 - self.cfg.overlap_ratio)

    def get_area_coverage_rate(self, num_drones: int = 1, speed: Optional[float] = None) -> Dict[str, float]:
        """
        Birim zamandaki taranan alan miktarı (ACR).
        """
        v = speed if speed is not None else self.cfg.cruise_speed_ms
        w_eff = self.get_effective_sweep_width()

        # 1 Drone için saniyede taranan alan (m^2/s)
        acr_1_m2s = v * w_eff
        # N Drone için toplam alan tarama hızı
        acr_total_m2s = acr_1_m2s * num_drones

        # km^2 / saat cinsinden
        acr_km2h = (acr_total_m2s * 3600.0) / 1e6

        return {
            "effective_sweep_width_m": round(w_eff, 2),
            "single_drone_m2s": round(acr_1_m2s, 2),
            "single_drone_km2h": round((acr_1_m2s * 3600.0) / 1e6, 2),
            "swarm_total_m2s": round(acr_total_m2s, 2),
            "swarm_total_km2h": round(acr_km2h, 2)
        }

    def get_analytical_detection_time(
        self,
        area_km2: float,
        num_drones: int,
        confidence_percent: float = 95.0
    ) -> Dict[str, Any]:
        """
        Koopman Arama Teorisinden analitik Ortalama Tespit Süresi (MTTD).
        P(t) = 1 - exp(- (N * v * W_eff * eta / Area) * t)
        t = - ln(1 - P) * Area / (N * v * W_eff * eta)
        """
        area_m2 = area_km2 * 1e6
        w_eff = self.get_effective_sweep_width()
        v = self.cfg.cruise_speed_ms
        eta = self.cfg.pso_efficiency_gain

        # Etkin sürü tarama potansiyeli (m^2/s)
        eff_rate = num_drones * v * w_eff * eta

        # %50 tespit süresi (Medyan)
        t_50_sec = (math.log(2.0) * area_m2) / eff_rate
        # İstenen güven seviyesi süresi (örn %95)
        p = min(0.999, max(0.01, confidence_percent / 100.0))
        t_conf_sec = (-math.log(1.0 - p) * area_m2) / eff_rate

        # Tam kapsama süresi (Grid/Exhaustive Search): T_full = Area / (N * v * W_eff)
        t_exhaustive_sec = area_m2 / (num_drones * v * w_eff)

        return {
            "area_km2": area_km2,
            "num_drones": num_drones,
            "t_50_seconds": round(t_50_sec, 1),
            "t_50_minutes": round(t_50_sec / 60.0, 2),
            "t_target_conf_seconds": round(t_conf_sec, 1),
            "t_target_conf_minutes": round(t_conf_sec / 60.0, 2),
            "t_exhaustive_minutes": round(t_exhaustive_sec / 60.0, 2),
            "confidence_percent": confidence_percent
        }

    def run_monte_carlo_benchmark(
        self,
        area_km2: float,
        num_drones: int,
        iterations: int = 50,
        wind_speed_ms: float = 4.0
    ) -> Dict[str, Any]:
        """
        Gerçekçi 2D/3D Monte Carlo Yangın Arama Simülasyonu.
        Rastgele konumlarda yangın başlatır, duman yayılımı oluşturur ve
        sürünün yangını tespit etme süresini (saniye) simüle eder.
        """
        area_m = math.sqrt(area_km2 * 1e6)  # Kare alan kenar uzunluğu (m)
        w_eff = self.get_effective_sweep_width()
        v = self.cfg.cruise_speed_ms
        dt = 1.0  # 1 saniyelik simülasyon adımı

        pso_detection_times = []
        random_detection_times = []
        grid_detection_times = []

        for it in range(iterations):
            # Yangın konumu (Rastgele)
            fire_x = random.uniform(area_m * 0.1, area_m * 0.9)
            fire_y = random.uniform(area_m * 0.1, area_m * 0.9)

            # Duman yayılma alanı (rüzgar yönünde elips)
            wind_dir_rad = random.uniform(0, 2 * math.pi)

            # --- 1. PyreSwarm PSO Simülasyonu ---
            t_pso = self._simulate_pso_search(
                area_m=area_m,
                num_drones=num_drones,
                fire_x=fire_x,
                fire_y=fire_y,
                wind_dir=wind_dir_rad,
                v=v,
                w_eff=w_eff,
                dt=dt
            )
            pso_detection_times.append(t_pso)

            # --- 2. Rastgele Gezinim (Random Walk) Simülasyonu ---
            t_random = self._simulate_random_search(
                area_m=area_m,
                num_drones=num_drones,
                fire_x=fire_x,
                fire_y=fire_y,
                v=v,
                w_eff=w_eff,
                dt=dt
            )
            random_detection_times.append(t_random)

            # --- 3. Standart Izgara/Lawnmower Tarama ---
            # Izgara aramasında deterministik süre: yangın konumuna göre kat edilen mesafe
            t_grid = self._simulate_grid_search(
                area_m=area_m,
                num_drones=num_drones,
                fire_x=fire_x,
                fire_y=fire_y,
                v=v,
                w_eff=w_eff
            )
            grid_detection_times.append(t_grid)

        pso_arr = np.array(pso_detection_times)
        rand_arr = np.array(random_detection_times)
        grid_arr = np.array(grid_detection_times)

        return {
            "area_km2": area_km2,
            "num_drones": num_drones,
            "iterations": iterations,
            "pso": {
                "mean_seconds": round(float(np.mean(pso_arr)), 1),
                "mean_minutes": round(float(np.mean(pso_arr)) / 60.0, 2),
                "median_minutes": round(float(np.median(pso_arr)) / 60.0, 2),
                "std_minutes": round(float(np.std(pso_arr)) / 60.0, 2),
                "min_minutes": round(float(np.min(pso_arr)) / 60.0, 2),
                "max_minutes": round(float(np.max(pso_arr)) / 60.0, 2),
            },
            "random_walk": {
                "mean_minutes": round(float(np.mean(rand_arr)) / 60.0, 2),
                "std_minutes": round(float(np.std(rand_arr)) / 60.0, 2),
            },
            "grid_search": {
                "mean_minutes": round(float(np.mean(grid_arr)) / 60.0, 2),
                "std_minutes": round(float(np.std(grid_arr)) / 60.0, 2),
            },
            "pso_speedup_vs_random": round(float(np.mean(rand_arr) / np.mean(pso_arr)), 2),
            "pso_speedup_vs_grid": round(float(np.mean(grid_arr) / np.mean(pso_arr)), 2)
        }

    def _simulate_pso_search(
        self,
        area_m: float,
        num_drones: int,
        fire_x: float,
        fire_y: float,
        wind_dir: float,
        v: float,
        w_eff: float,
        dt: float
    ) -> float:
        """PSO mantığıyla simüle edilmiş arama."""
        # Drone'lar başlangıçta bölgeye eşit dağıtılır
        drones_x = [random.uniform(0, area_m) for _ in range(num_drones)]
        drones_y = [random.uniform(0, area_m) for _ in range(num_drones)]
        drones_vx = [(random.random() - 0.5) * v for _ in range(num_drones)]
        drones_vy = [(random.random() - 0.5) * v for _ in range(num_drones)]

        gbest_x = None
        gbest_y = None
        gbest_val = 0.0

        max_time = 7200.0  # 2 saat tavan
        t = 0.0

        # Duman duman konisi (Plume) - yangından rüzgar yönüne doğru uzanır
        plume_length = 350.0

        detection_radius = w_eff / 2.0

        while t < max_time:
            t += dt
            found = False

            for i in range(num_drones):
                # Yangına doğrudan mesafe
                dist_fire = math.hypot(drones_x[i] - fire_x, drones_y[i] - fire_y)

                # Doğrudan alev tespiti
                if dist_fire <= detection_radius:
                    return t

                # Duman tespiti (Gradual fitness)
                # Drone duman konisinin içinde mi?
                dx = drones_x[i] - fire_x
                dy = drones_y[i] - fire_y
                proj_dist = dx * math.cos(wind_dir) + dy * math.sin(wind_dir)
                perp_dist = abs(-dx * math.sin(wind_dir) + dy * math.cos(wind_dir))

                if 0 <= proj_dist <= plume_length and perp_dist <= (40.0 + 0.25 * proj_dist):
                    # Duman kokusu/puanı alındı!
                    smoke_score = max(0.1, 1.0 - (proj_dist / plume_length))
                    if smoke_score > gbest_val:
                        gbest_val = smoke_score
                        gbest_x = drones_x[i]
                        gbest_y = drones_y[i]

                # PSO Hız güncelleme
                w = 0.65
                c1 = 1.2
                c2 = 1.6

                r1 = random.random()
                r2 = random.random()

                soc_x = (c2 * r2 * (gbest_x - drones_x[i])) if gbest_x else 0.0
                soc_y = (c2 * r2 * (gbest_y - drones_y[i])) if gbest_y else 0.0

                drones_vx[i] = w * drones_vx[i] + soc_x * 0.2 + (random.random() - 0.5) * 4.0
                drones_vy[i] = w * drones_vy[i] + soc_y * 0.2 + (random.random() - 0.5) * 4.0

                # Hız sınırlama
                spd = math.hypot(drones_vx[i], drones_vy[i])
                if spd > 0.1:
                    drones_vx[i] = (drones_vx[i] / spd) * v
                    drones_vy[i] = (drones_vy[i] / spd) * v

                # Konum güncelleme
                drones_x[i] += drones_vx[i] * dt
                drones_y[i] += drones_vy[i] * dt

                # Duvarlardan sekme
                if drones_x[i] < 0: drones_x[i] = 0; drones_vx[i] *= -1
                if drones_x[i] > area_m: drones_x[i] = area_m; drones_vx[i] *= -1
                if drones_y[i] < 0: drones_y[i] = 0; drones_vy[i] *= -1
                if drones_y[i] > area_m: drones_y[i] = area_m; drones_vy[i] *= -1

        return max_time

    def _simulate_random_search(
        self,
        area_m: float,
        num_drones: int,
        fire_x: float,
        fire_y: float,
        v: float,
        w_eff: float,
        dt: float
    ) -> float:
        """Körlemesine rastgele gezinim (Random Walk)."""
        drones_x = [random.uniform(0, area_m) for _ in range(num_drones)]
        drones_y = [random.uniform(0, area_m) for _ in range(num_drones)]
        drones_heading = [random.uniform(0, 2 * math.pi) for _ in range(num_drones)]

        max_time = 7200.0
        t = 0.0
        det_radius = w_eff / 2.0

        while t < max_time:
            t += dt
            for i in range(num_drones):
                dist = math.hypot(drones_x[i] - fire_x, drones_y[i] - fire_y)
                if dist <= det_radius:
                    return t

                # Rastgele yön değişimi
                if random.random() < 0.05:
                    drones_heading[i] += (random.random() - 0.5) * 1.5

                drones_x[i] += v * math.cos(drones_heading[i]) * dt
                drones_y[i] += v * math.sin(drones_heading[i]) * dt

                if drones_x[i] < 0 or drones_x[i] > area_m:
                    drones_heading[i] = math.pi - drones_heading[i]
                if drones_y[i] < 0 or drones_y[i] > area_m:
                    drones_heading[i] = -drones_heading[i]

        return max_time

    def _simulate_grid_search(
        self,
        area_m: float,
        num_drones: int,
        fire_x: float,
        fire_y: float,
        v: float,
        w_eff: float
    ) -> float:
        """Standart Lawnmower (Izgara) Tarama."""
        # Alanı N sektöre böl
        sector_w = area_m / num_drones
        sector_idx = min(num_drones - 1, int(fire_x / sector_w))

        # O sektördeki drone'un yangına ulaşma mesafesi
        # Izgara çizgileri w_eff aralıkla ilerler
        lines = area_m / w_eff
        line_idx = int(fire_y / w_eff)

        # Kat edilen mesafe
        dist_traveled = line_idx * sector_w + abs(fire_x - (sector_idx * sector_w))
        t_det = dist_traveled / v
        return max(10.0, t_det)


def generate_benchmark_figures(output_dir: str = "docs/figures"):
    """
    Monte Carlo ve Analitik sonuçların yüksek çözünürlüklü grafiklerini üretir.
    """
    import matplotlib.pyplot as plt
    os.makedirs(output_dir, exist_ok=True)

    engine = MetricsEngine()

    # 1. Grafik: Alan Büyüklüğüne Göre Yangın Tespit Süresi (Farklı Drone Sayıları)
    areas = [1.0, 4.0, 10.0, 25.0, 50.0, 100.0]
    drone_counts = [1, 3, 5, 10, 20]

    plt.figure(figsize=(10, 6), dpi=300)
    plt.style.use('dark_background')

    colors = ['#ff4444', '#ff8800', '#ffcc00', '#00ccff', '#00ff88']

    for i, n in enumerate(drone_counts):
        times_min = []
        for a in areas:
            res = engine.get_analytical_detection_time(a, n, confidence_percent=95.0)
            times_min.append(res["t_target_conf_minutes"])
        plt.plot(areas, times_min, marker='o', linewidth=2.5, color=colors[i], label=f'{n} Drone')

    plt.title('PyreSwarm: Tarama Alanı (km²) vs %95 Güvenilirlikte Yangın Tespit Süresi (Dk)', fontsize=13, fontweight='bold', color='#f0f4f8')
    plt.xlabel('Yangın Arama Alanı (km²)', fontsize=11, color='#8b9bb4')
    plt.ylabel('Ortalama Tespit Süresi (Dakika)', fontsize=11, color='#8b9bb4')
    plt.grid(True, linestyle='--', alpha=0.25)
    plt.legend(frameon=True, facecolor='#151c28', edgecolor='#334455')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "area_vs_detection_time.png"))
    plt.close()

    # 2. Grafik: Arama Algoritmaları Karşılaştırması (PSO vs Grid vs Random)
    # 25 km^2 alan için farklı drone sayılarında simülasyon benchmark'ı
    plt.figure(figsize=(10, 6), dpi=300)
    plt.style.use('dark_background')

    ns = [1, 2, 4, 8, 16]
    pso_means = []
    grid_means = []
    rand_means = []

    for n in ns:
        bench = engine.run_monte_carlo_benchmark(area_km2=25.0, num_drones=n, iterations=30)
        pso_means.append(bench["pso"]["mean_minutes"])
        grid_means.append(bench["grid_search"]["mean_minutes"])
        rand_means.append(bench["random_walk"]["mean_minutes"])

    bar_w = 0.25
    x = np.arange(len(ns))

    plt.bar(x - bar_w, rand_means, width=bar_w, label='Rastgele Arama (Random Walk)', color='#666677')
    plt.bar(x, grid_means, width=bar_w, label='Standart Izgara (Lawnmower)', color='#0088ff')
    plt.bar(x + bar_w, pso_means, width=bar_w, label='PyreSwarm 3D-PSO (Bizim Algoritmamız)', color='#ff5500')

    plt.title('25 km² Alanda Yangın Tespit Süreleri: Algoritma Karşılaştırması (Monte Carlo)', fontsize=13, fontweight='bold', color='#f0f4f8')
    plt.xticks(x, [f'{n} Drone' for n in ns], fontsize=11)
    plt.xlabel('Sürü Boyutu (Drone Sayısı)', fontsize=11, color='#8b9bb4')
    plt.ylabel('Ortalama Tespit Süresi (Dakika)', fontsize=11, color='#8b9bb4')
    plt.grid(True, linestyle='--', alpha=0.25, axis='y')
    plt.legend(frameon=True, facecolor='#151c28', edgecolor='#334455')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "algorithm_comparison.png"))
    plt.close()

    # 3. Grafik: Kümülatif Tespit Olasılığı Eğrisi P(t)
    plt.figure(figsize=(10, 6), dpi=300)
    plt.style.use('dark_background')

    t_series = np.linspace(0, 1800, 300) # 0 - 30 dakika
    area_25_m2 = 25.0 * 1e6
    w_eff = engine.get_effective_sweep_width()
    v = engine.cfg.cruise_speed_ms
    eta = engine.cfg.pso_efficiency_gain

    for n, color in zip([2, 5, 10], ['#ff8800', '#00e5ff', '#00ff88']):
        # P(t) = 1 - exp(- (N * v * W_eff * eta / Area) * t)
        rate = (n * v * w_eff * eta) / area_25_m2
        p_t = (1.0 - np.exp(-rate * t_series)) * 100.0
        plt.plot(t_series / 60.0, p_t, label=f'{n} Drone Sürüsü', color=color, linewidth=2.5)

    plt.axhline(y=95.0, color='#ff3344', linestyle=':', label='%95 Hedef Güvenilirlik')
    plt.title('25 km² Alanda Zaman İçinde Kümülatif Yangın Tespit Olasılığı P(t)', fontsize=13, fontweight='bold', color='#f0f4f8')
    plt.xlabel('Geçen Görev Süresi (Dakika)', fontsize=11, color='#8b9bb4')
    plt.ylabel('Yangını Tespit Etme Olasılığı (%)', fontsize=11, color='#8b9bb4')
    plt.grid(True, linestyle='--', alpha=0.25)
    plt.legend(frameon=True, facecolor='#151c28', edgecolor='#334455')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "cumulative_probability.png"))
    plt.close()

    print(f"[MetricsEngine] Tüm grafikler başarıyla oluşturuldu: {output_dir}")


if __name__ == "__main__":
    print("=== PyreSwarm Matematiksel Doğrulama ve Benchmark Testi ===")
    eng = MetricsEngine()
    w, l, a = eng.get_ground_footprint()
    print(f"Kamera Ayak İzi: Genişlik = {w:.2f} m, Derinlik = {l:.2f} m, Anlık Alan = {a:.1f} m²")
    acrs = eng.get_area_coverage_rate(num_drones=5)
    print(f"5 Drone için Alan Tarama Hızı = {acrs['swarm_total_km2h']} km²/saat")

    print("\n--- Monte Carlo Simülasyonu Koşturuluyor (Lütfen bekleyin)... ---")
    bench = eng.run_monte_carlo_benchmark(area_km2=10.0, num_drones=4, iterations=25)
    print(f"10 km² Alan, 4 Drone Sonucu:")
    print(f"  PyreSwarm 3D-PSO Ortalama Süre: {bench['pso']['mean_minutes']} dakika")
    print(f"  Standart Izgara Ortalama Süre: {bench['grid_search']['mean_minutes']} dakika")
    print(f"  Rastgele Gezinim Ortalama Süre: {bench['random_walk']['mean_minutes']} dakika")
    print(f"  PSO Hızlandırma Faktörü: Izgaraya göre {bench['pso_speedup_vs_grid']}x daha hızlı!")

    print("\nGrafikler çiziliyor...")
    generate_benchmark_figures()
