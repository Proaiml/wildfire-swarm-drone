"""
PyreSwarm - Karşılaştırmalı Temel Seviye ve Başarım Değerlendirme Motoru (Baseline Benchmarks)
Klasik arama stratejileri ile PyreSwarm 3D-PSO algoritmasını BİREBİR AYNI tohum (seed),
aynı harita ve aynı yangın koordinatlarında karşılaştırır:
1. Rastgele Arama (Random Search)
2. Çim Biçme / Paralel Hat (Lawnmower / Boustrophedon)
3. Bağımsız Açgözlü Arama (Independent Greedy Search)
4. PyreSwarm Çok Amaçlı Sürü PSO (PyreSwarm MO-PSO)
Monte Carlo deneyleri ile CSV ve JSON formatında bilimsel doğrulanabilir rapor üretir.
[SIMULATED]
"""

import math
import random
import time
import json
import csv
import os
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import numpy as np

from simulation.simulator import SwarmSimulationEngine, SimulationMetrics
from src.drones.state import DroneMode


class BaselineRunner:
    """
    Farklı arama algoritmalarını simülasyon ortamında çalıştırıp metrikleri toplayan test koşucusu.
    """

    def __init__(self, output_dir: str = "artifacts/benchmarks"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def run_single_benchmark(
        self,
        algorithm: str,
        num_drones: int = 5,
        area_km2: float = 4.0,
        num_fires: int = 2,
        seed: int = 42,
        max_steps: int = 250
    ) -> Dict[str, Any]:
        """Belirtilen algoritma ile tek bir simülasyon işletir."""
        random.seed(seed)
        sim = SwarmSimulationEngine(
            area_km2=area_km2,
            num_drones=num_drones,
            num_fires=num_fires,
            random_seed=seed
        )

        # Algoritma stratejisine göre optimize edici veya hedef üretim davranışı
        b = sim.boundary
        lat_min = min(p[0] for p in b)
        lat_max = max(p[0] for p in b)
        lon_min = min(p[1] for p in b)
        lon_max = max(p[1] for p in b)

        # Lawnmower için durum hafızası: [corridor_lat, target_lon_is_max]
        lm_states = []
        corridor_w = (lat_max - lat_min) / float(max(1, num_drones))
        for idx in range(num_drones):
            lm_states.append({
                "lat": lat_min + (idx + 0.5) * corridor_w,
                "going_east": True
            })

        for step in range(max_steps):
            if algorithm == "RANDOM":
                # Rastgele arama: Drone hedefe yaklaştığında veya her 15 adımda yeni rastgele hedef
                for idx, (d, adapter) in enumerate(zip(sim.drones, sim.adapters)):
                    if d.is_in_air and d.mode == DroneMode.SEARCHING:
                        dist_to_tgt = math.hypot(
                            (adapter.target_lat - d.lat) * 111139.0,
                            (adapter.target_lon - d.lon) * 111139.0
                        )
                        if dist_to_tgt < 30.0 or step % 20 == 0:
                            tgt_lat = lat_min + random.random() * (lat_max - lat_min)
                            tgt_lon = lon_min + random.random() * (lon_max - lon_min)
                            adapter.goto(tgt_lat, tgt_lon, 60.0)
                sim.step(dt=1.0, use_pso=False)

            elif algorithm == "LAWNMOWER":
                # Paralel şerit taraması (Boustrophedon)
                for idx, (d, adapter) in enumerate(zip(sim.drones, sim.adapters)):
                    if d.is_in_air and d.mode == DroneMode.SEARCHING:
                        lm = lm_states[idx]
                        dist_to_tgt = math.hypot(
                            (adapter.target_lat - d.lat) * 111139.0,
                            (adapter.target_lon - d.lon) * 111139.0
                        )
                        if dist_to_tgt < 25.0 or step == 0:
                            # Yön değiştir
                            lm["going_east"] = not lm["going_east"]
                            tgt_lon = lon_max if lm["going_east"] else lon_min
                            adapter.goto(lm["lat"], tgt_lon, 60.0)
                sim.step(dt=1.0, use_pso=False)

            elif algorithm == "GREEDY":
                # Bağımsız açgözlü: Yangın tespit edildiğinde yalnızca tespit eden yaklaşır, sosyal paylaşım kapalı
                sim.optimizer.c2_init = 0.0
                sim.step(dt=1.0, use_pso=True)

            else:  # "PYRESWARM_PSO"
                # Tam hibrit: Çok amaçlı adaptif PSO + Füzyon + Çeşitlilik Yönetimi
                sim.step(dt=1.0, use_pso=True)

            # Yangınların hepsi doğrulandıysa erken durdurma
            if len(sim.incident_manager.get_confirmed_incidents()) >= num_fires and sim.metrics.ttc_sec is not None:
                break

        # Metrikleri hesapla
        cov = sim.search_map.get_coverage_metrics()
        ttfd = sim.metrics.ttfd_sec if sim.metrics.ttfd_sec is not None else float(max_steps)
        ttc = sim.metrics.ttc_sec if sim.metrics.ttc_sec is not None else float(max_steps)

        return {
            "algorithm": algorithm,
            "seed": seed,
            "num_drones": num_drones,
            "area_km2": area_km2,
            "num_fires": num_fires,
            "steps_executed": sim.current_step,
            "ttfd_seconds": round(ttfd, 1),
            "ttc_seconds": round(ttc, 1),
            "coverage_percent": round(cov["coverage_percent"], 2),
            "redundant_ratio": round(cov["redundant_ratio"], 3),
            "total_distance_km": round(sim.total_distance_travelled_m / 1000.0, 3),
            "energy_kj": round((180.0 * sim.current_step * len(sim.drones)) / 1000.0, 1),
            "incidents_confirmed": len(sim.incident_manager.get_confirmed_incidents())
        }

    def run_comparative_suite(
        self,
        seeds: List[int] = [42, 43, 44, 45, 46],
        num_drones: int = 5,
        area_km2: float = 4.0,
        num_fires: int = 2
    ) -> Dict[str, Any]:
        """Tüm algoritmaları Monte Carlo tohumları üzerinden karşılaştırır."""
        algorithms = ["RANDOM", "LAWNMOWER", "GREEDY", "PYRESWARM_PSO"]
        all_results: List[Dict[str, Any]] = []

        print(f"[Benchmark] {len(algorithms)} algoritma, {len(seeds)} tohum üzerinden test ediliyor...")

        for algo in algorithms:
            for s in seeds:
                res = self.run_single_benchmark(
                    algorithm=algo,
                    num_drones=num_drones,
                    area_km2=area_km2,
                    num_fires=num_fires,
                    seed=s
                )
                all_results.append(res)
                print(f" -> {algo} (Seed {s}): TTFD={res['ttfd_seconds']}s, Cov={res['coverage_percent']}%")

        # İstatistiki Özet (Mean, Median, Std, p90)
        summary: Dict[str, Any] = {}
        for algo in algorithms:
            sub = [r for r in all_results if r["algorithm"] == algo]
            ttfds = [r["ttfd_seconds"] for r in sub]
            covs = [r["coverage_percent"] for r in sub]
            reds = [r["redundant_ratio"] for r in sub]
            energies = [r["energy_kj"] for r in sub]

            summary[algo] = {
                "ttfd_mean": round(float(np.mean(ttfds)), 1),
                "ttfd_median": round(float(np.median(ttfds)), 1),
                "ttfd_std": round(float(np.std(ttfds)), 1),
                "ttfd_p90": round(float(np.percentile(ttfds, 90)), 1),
                "coverage_mean": round(float(np.mean(covs)), 2),
                "redundant_ratio_mean": round(float(np.mean(reds)), 3),
                "energy_mean_kj": round(float(np.mean(energies)), 1)
            }

        # CSV ve JSON Kaydı
        csv_path = os.path.join(self.output_dir, "comparative_benchmark.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(all_results[0].keys()))
            writer.writeheader()
            writer.writerows(all_results)

        json_path = os.path.join(self.output_dir, "comparative_benchmark.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({"summary": summary, "runs": all_results}, f, indent=2)

        print(f"[Benchmark] Sonuçlar kaydedildi: {csv_path} ve {json_path}")
        return {"summary": summary, "runs": all_results}
