"""
PyreSwarm - PSO Hiperparametre Meta-Optimizasyonu ve Duyarlılık Analizi (PSO Hyperparameter Tuning)
Yangın arama problemi için en iyi PSO parametrelerini (w, c1, c2, R_taboo)
simülasyon tabanlı meta-optimizasyon (Grid Search & Parameter Sweep) ile araştırır ve doğrular.
[SIMULATED]
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import math
import random
import json
from typing import List, Dict, Any, Tuple
import numpy as np

from simulation.simulator import SwarmSimulationEngine


class PSOHyperparameterTuner:
    """
    Farklı PSO parametre kombinasyonlarını Monte Carlo tohumlarında koşturarak
    yangın tespit süresi (TTFD) ve kapsama verimliliğine göre en uygun parametre setini belirler.
    """

    def __init__(self, output_dir: str = "artifacts/benchmarks"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def evaluate_parameter_set(
        self,
        name: str,
        w_max: float,
        w_min: float,
        c1_init: float,
        c2_init: float,
        taboo_radius_m: float,
        seeds: List[int] = [42, 43, 44],
        num_drones: int = 5,
        area_km2: float = 3.0,
        num_fires: int = 2
    ) -> Dict[str, Any]:
        """Tek bir parametre konfigürasyonunu birden fazla tohum üzerinde çoklu yangın (multi-fire) senaryosunda değerlendirir."""
        ttfds = []
        ttcs = []
        coverages = []
        redundancies = []
        energies = []
        confirmed_counts = []

        for s in seeds:
            sim = SwarmSimulationEngine(
                area_km2=area_km2,
                num_drones=num_drones,
                num_fires=num_fires,
                random_seed=s
            )
            sim.optimizer.w_max = w_max
            sim.optimizer.w_min = w_min
            sim.optimizer.c1_init = c1_init
            sim.optimizer.c2_init = c2_init
            sim.diversity_manager.taboo_radius_m = taboo_radius_m

            metrics = sim.run_simulation(max_steps=220)

            ttfd = metrics.ttfd_sec if metrics.ttfd_sec is not None else 220.0
            ttc = metrics.ttc_sec if metrics.ttc_sec is not None else 220.0
            ttfds.append(ttfd)
            ttcs.append(ttc)
            coverages.append(metrics.final_coverage_pct)
            redundancies.append(metrics.redundant_coverage_ratio)
            energies.append(metrics.total_energy_kj)
            confirmed_counts.append(metrics.incidents_confirmed)

        mean_ttfd = round(float(np.mean(ttfds)), 1)
        mean_ttc = round(float(np.mean(ttcs)), 1)
        mean_cov = round(float(np.mean(coverages)), 2)
        mean_red = round(float(np.mean(redundancies)), 3)
        mean_energy = round(float(np.mean(energies)), 1)
        mean_confirmed = round(float(np.mean(confirmed_counts)), 1)

        # Çoklu yangın bileşik skoru: Her iki yangını da bulma bonusu (+50), düşük TTFD/TTC, yüksek kapsama
        fitness_score = round(
            (mean_confirmed * 40.0) + (220.0 - mean_ttfd) * 0.2 + (220.0 - mean_ttc) * 0.2 + mean_cov * 1.5 - mean_red * 25.0,
            2
        )

        return {
            "config_name": name,
            "w_max": w_max,
            "w_min": w_min,
            "c1_init": c1_init,
            "c2_init": c2_init,
            "taboo_radius_m": taboo_radius_m,
            "ttfd_mean_sec": mean_ttfd,
            "coverage_mean_pct": mean_cov,
            "redundant_ratio_mean": mean_red,
            "energy_mean_kj": mean_energy,
            "composite_score": fitness_score
        }

    def run_meta_tuning_study(self) -> Dict[str, Any]:
        """Klasik ve optimize edilmiş parametre setlerini karşılaştırır."""
        candidates = [
            # 1. Klasik / Naive PSO (Tabu alanı yok, yüksek sosyal çekim)
            {
                "name": "Klasik / Naive PSO",
                "w_max": 0.72, "w_min": 0.72,
                "c1_init": 1.5, "c2_init": 2.5,
                "taboo_radius_m": 0.0
            },
            # 2. Aşırı Keşif Odaklı (Sosyal paylaşım çok düşük)
            {
                "name": "Aşırı Keşif (High-Exploration)",
                "w_max": 0.90, "w_min": 0.70,
                "c1_init": 2.8, "c2_init": 0.4,
                "taboo_radius_m": 80.0
            },
            # 3. Aşırı İşbirliği (Sürü çöküşüne yatkın)
            {
                "name": "Aşırı İşbirliği (High-Social Collapse)",
                "w_max": 0.60, "w_min": 0.30,
                "c1_init": 0.8, "c2_init": 2.8,
                "taboo_radius_m": 30.0
            },
            # 4. PyreSwarm Meta-Optimized MO-PSO (Adaptif w, dengeli c1/c2, dinamik tabu)
            {
                "name": "PyreSwarm Meta-Optimized MO-PSO",
                "w_max": 0.85, "w_min": 0.40,
                "c1_init": 2.0, "c2_init": 1.2,
                "taboo_radius_m": 150.0
            }
        ]

        results = []
        print("[Meta-Optimizer] PSO hiperparametre taraması başlatılıyor...")

        for c in candidates:
            res = self.evaluate_parameter_set(
                name=c["name"],
                w_max=c["w_max"],
                w_min=c["w_min"],
                c1_init=c["c1_init"],
                c2_init=c["c2_init"],
                taboo_radius_m=c["taboo_radius_m"],
                seeds=[42, 43, 44]
            )
            results.append(res)
            print(f" -> {res['config_name']}: TTFD={res['ttfd_mean_sec']}s, Kapsama=%{res['coverage_mean_pct']}, Skor={res['composite_score']}")

        # En iyi konfigürasyonu seç
        results.sort(key=lambda x: x["composite_score"], reverse=True)
        best_config = results[0]

        output_file = os.path.join(self.output_dir, "hyperparameter_tuning_results.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({"best_config": best_config, "all_evaluations": results}, f, indent=2, ensure_ascii=False)

        print(f"[Meta-Optimizer] En iyi parametre seti belirlendi: {best_config['config_name']} (Skor: {best_config['composite_score']})")
        return {"best_config": best_config, "all_evaluations": results}


if __name__ == "__main__":
    tuner = PSOHyperparameterTuner()
    tuner.run_meta_tuning_study()
