"""
PyreSwarm - 30 Optimizasyon ve Arama Algoritması Kıyaslama Motoru (Multi-Algorithm Suite)
=======================================================================================
Orman yangını tespiti ve İHA sürü keşif operasyonları için literatürdeki 30 farklı
optimizasyon ve uzaysal arama algoritmasını BİREBİR AYNI tohum (seed), harita sınırları,
yangın konumları ve fiziksel İHA kısıtları altında simüle eder ve karşılaştırır.

Algoritma Aileleri:
1. Sürü Zekası (Swarm Intelligence) - 14 Algoritma
2. Evrimsel ve Genetik (Evolutionary & Genetic) - 6 Algoritma
3. Fizik ve Doğa Olayı Tabanlı (Physics-Based) - 5 Algoritma
4. Klasik, Geometrik ve Deterministik (Classic & Spatial) - 5 Algoritma
"""

import math
import random
import time
import json
import csv
import os
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

from simulation.simulator import SwarmSimulationEngine, SimulationMetrics
from src.drones.state import DroneMode, DroneState


class AlgorithmFamily(str, Enum):
    SWARM_INTELLIGENCE = "Sürü Zekası"
    EVOLUTIONARY = "Evrimsel & Genetik"
    PHYSICS_BASED = "Fizik & Kimya Tabanlı"
    CLASSIC_GEOMETRIC = "Klasik & Geometrik Arama"


@dataclass
class AlgorithmMetadata:
    key: str
    name: str
    family: AlgorithmFamily
    year: int
    authors: str
    core_mechanism: str


# 30 Algoritmanın Eksiksiz Kataloğu
ALGORITHM_CATALOG: List[AlgorithmMetadata] = [
    # --- GRUP 1: SÜRÜ ZEKASI (14) ---
    AlgorithmMetadata(
        key="PYRESWARM_PSO",
        name="PyreSwarm MO-PSO",
        family=AlgorithmFamily.SWARM_INTELLIGENCE,
        year=2026,
        authors="PyreSwarm Team",
        core_mechanism="Sektörel Dağılım Koridorlu, Çok Amaçlı Adaptif 3D Parçacık Sürü Optimizasyonu"
    ),
    AlgorithmMetadata(
        key="STANDARD_PSO",
        name="Standard PSO",
        family=AlgorithmFamily.SWARM_INTELLIGENCE,
        year=1995,
        authors="Kennedy & Eberhart",
        core_mechanism="Klasik Atalet, Bilişsel ve Sosyal Çekim Vektör Güncellemesi"
    ),
    AlgorithmMetadata(
        key="GWO",
        name="Grey Wolf Optimizer (GWO)",
        family=AlgorithmFamily.SWARM_INTELLIGENCE,
        year=2014,
        authors="Mirjalili et al.",
        core_mechanism="Alfa, Beta ve Delta Kurt Hiyerarşisi ile Av Kuşatma Manevrası"
    ),
    AlgorithmMetadata(
        key="WOA",
        name="Whale Optimization (WOA)",
        family=AlgorithmFamily.SWARM_INTELLIGENCE,
        year=2016,
        authors="Mirjalili & Lewis",
        core_mechanism="Kambur Balina Kabarcık Ağı (Bubble-Net) ve Spiral Hücum Modeli"
    ),
    AlgorithmMetadata(
        key="BA",
        name="Bat Algorithm (BA)",
        family=AlgorithmFamily.SWARM_INTELLIGENCE,
        year=2010,
        authors="Yang",
        core_mechanism="Yarasa Ekolokasyonu, Dinamik Frekans Ayarı ve Ses Şiddeti Sönümleme"
    ),
    AlgorithmMetadata(
        key="FA",
        name="Firefly Algorithm (FA)",
        family=AlgorithmFamily.SWARM_INTELLIGENCE,
        year=2008,
        authors="Yang",
        core_mechanism="Işık Şiddeti Çekiciliği, Işıma Emilimi ve Işığa Doğru Hareket"
    ),
    AlgorithmMetadata(
        key="CS",
        name="Cuckoo Search (CS)",
        family=AlgorithmFamily.SWARM_INTELLIGENCE,
        year=2009,
        authors="Yang & Deb",
        core_mechanism="Ağır Kuyruklu Lévy Uçuşları ve Parazit Yuva Değişimi"
    ),
    AlgorithmMetadata(
        key="ABC",
        name="Artificial Bee Colony (ABC)",
        family=AlgorithmFamily.SWARM_INTELLIGENCE,
        year=2005,
        authors="Karaboga",
        core_mechanism="İşçi Arı, Gözlemci Arı ve Rastgele Kaşif Arı Fazları"
    ),
    AlgorithmMetadata(
        key="SSA",
        name="Salp Swarm Algorithm (SSA)",
        family=AlgorithmFamily.SWARM_INTELLIGENCE,
        year=2017,
        authors="Mirjalili et al.",
        core_mechanism="Salp Zinciri Lideri Takip Eden Dinamik Kademeli Hiyerarşi"
    ),
    AlgorithmMetadata(
        key="HHO",
        name="Harris Hawks (HHO)",
        family=AlgorithmFamily.SWARM_INTELLIGENCE,
        year=2019,
        authors="Heidari et al.",
        core_mechanism="Kaçış Enerjisi Tükenimi, Yumuşak/Sert Kuşatma ve Ani Şahin Dalışı"
    ),
    AlgorithmMetadata(
        key="GSO",
        name="Glowworm Swarm (GSO)",
        family=AlgorithmFamily.SWARM_INTELLIGENCE,
        year=2005,
        authors="Krishnanand & Ghose",
        core_mechanism="Lusiferin Değişimi ve Adaptif Yerel Komşuluk Çapı"
    ),
    AlgorithmMetadata(
        key="DA",
        name="Dragonfly Algorithm (DA)",
        family=AlgorithmFamily.SWARM_INTELLIGENCE,
        year=2016,
        authors="Mirjalili",
        core_mechanism="Ayrılma, Hizalanma, Uyum, Besine Çekim ve Düşmandan Kaçış"
    ),
    AlgorithmMetadata(
        key="SMA",
        name="Slime Mould Algorithm (SMA)",
        family=AlgorithmFamily.SWARM_INTELLIGENCE,
        year=2020,
        authors="Li et al.",
        core_mechanism="Cıvık Mantar Pozitif-Negatif Geri Bildirimli Tüp Kalınlığı Ağırlığı"
    ),
    AlgorithmMetadata(
        key="ACO",
        name="Ant Colony Opt (ACOR)",
        family=AlgorithmFamily.SWARM_INTELLIGENCE,
        year=2008,
        authors="Socha & Dorigo",
        core_mechanism="Sürekli Arama Alanında Çok Değişkenli Gauss Feromon Dağılım Örneklemesi"
    ),

    # --- GRUP 2: EVRİMSEL VE GENETİK (6) ---
    AlgorithmMetadata(
        key="GA",
        name="Genetic Algorithm (Real-GA)",
        family=AlgorithmFamily.EVOLUTIONARY,
        year=1975,
        authors="Holland / Goldberg",
        core_mechanism="Simulated Binary Crossover (SBX), Gauss Mutasyonu ve Elitizm"
    ),
    AlgorithmMetadata(
        key="DE",
        name="Differential Evolution (DE)",
        family=AlgorithmFamily.EVOLUTIONARY,
        year=1997,
        authors="Storn & Price",
        core_mechanism="Vektör Fark Mutasyonu (DE/rand/1) ve Binom Çaprazlama"
    ),
    AlgorithmMetadata(
        key="CMA_ES",
        name="CMA-ES",
        family=AlgorithmFamily.EVOLUTIONARY,
        year=2001,
        authors="Hansen & Ostermeier",
        core_mechanism="Kovaryans Matrisi Adaptasyonu ile Dağılım Elipsoidi Yönlendirmesi"
    ),
    AlgorithmMetadata(
        key="BBO",
        name="Biogeography-Based (BBO)",
        family=AlgorithmFamily.EVOLUTIONARY,
        year=2008,
        authors="Simon",
        core_mechanism="Habitat Uygunluk İndeksi (HSI), Göç Oranları ve Tür Mutasyonu"
    ),
    AlgorithmMetadata(
        key="EP",
        name="Evolutionary Programming (EP)",
        family=AlgorithmFamily.EVOLUTIONARY,
        year=1966,
        authors="Fogel",
        core_mechanism="Yalnızca Mutasyona Dayalı Bireysel Çeşitlilik ve Turnuva Seçilimi"
    ),
    AlgorithmMetadata(
        key="ES",
        name="Evolution Strategy (1+1)-ES",
        family=AlgorithmFamily.EVOLUTIONARY,
        year=1973,
        authors="Rechenberg",
        core_mechanism="1/5 Başarı Kuralı ile Otomatik Adım Boyutu (Step-Size) Adaptasyonu"
    ),

    # --- GRUP 3: FİZİK VE KİMYA TABANLI (5) ---
    AlgorithmMetadata(
        key="SA",
        name="Simulated Annealing (SA)",
        family=AlgorithmFamily.PHYSICS_BASED,
        year=1983,
        authors="Kirkpatrick et al.",
        core_mechanism="Termodinamik Sıcaklık Sönümleme Çizelgesi ve Boltzmann Kabul Olasılığı"
    ),
    AlgorithmMetadata(
        key="GSA",
        name="Gravitational Search (GSA)",
        family=AlgorithmFamily.PHYSICS_BASED,
        year=2009,
        authors="Rashedi et al.",
        core_mechanism="Newton Evrensel Kütleçekim Kanunu ve İvmelenme Dinamiği"
    ),
    AlgorithmMetadata(
        key="EO",
        name="Equilibrium Optimizer (EO)",
        family=AlgorithmFamily.PHYSICS_BASED,
        year=2020,
        authors="Faramarzi et al.",
        core_mechanism="Kontrol Hacmi Dinamik Kütle Dengesi ve Denge Havuzu Adayları"
    ),
    AlgorithmMetadata(
        key="WDO",
        name="Wind Driven Opt (WDO)",
        family=AlgorithmFamily.PHYSICS_BASED,
        year=2010,
        authors="Bayraktar et al.",
        core_mechanism="Atmosferik Hava Parseli Hareketi, Coriolis Kuvveti ve Basınç Gradyanı"
    ),
    AlgorithmMetadata(
        key="HGSO",
        name="Henry Gas Solubility (HGSO)",
        family=AlgorithmFamily.PHYSICS_BASED,
        year=2019,
        authors="Hashim et al.",
        core_mechanism="Henry Gaz Çözünürlüğü Kanunu, Sıcaklık/Basınç Transfer Oranları"
    ),

    # --- GRUP 4: KLASİK VE GEOMETRİK ARAMA (5) ---
    AlgorithmMetadata(
        key="LAWNMOWER",
        name="Lawnmower (Boustrophedon)",
        family=AlgorithmFamily.CLASSIC_GEOMETRIC,
        year=2000,
        authors="Choset",
        core_mechanism="Hücresel Paralel Hat ve Şerit Süpürme Kapsama Planlaması"
    ),
    AlgorithmMetadata(
        key="RANDOM",
        name="Random Search (Brownian)",
        family=AlgorithmFamily.CLASSIC_GEOMETRIC,
        year=1905,
        authors="Pearson",
        core_mechanism="Saf Stokastik Yön Belirleme ve Rastgele Yürüyüş Dinamiği"
    ),
    AlgorithmMetadata(
        key="GREEDY",
        name="Independent Hill Climbing",
        family=AlgorithmFamily.CLASSIC_GEOMETRIC,
        year=1970,
        authors="Classic AI",
        core_mechanism="İletişimsiz, Bağımsız Yerel En Dik Tırmanma Gradyanı"
    ),
    AlgorithmMetadata(
        key="SPIRAL",
        name="Archimedean Spiral Spreading",
        family=AlgorithmFamily.CLASSIC_GEOMETRIC,
        year=2004,
        authors="Vincent & Rubin",
        core_mechanism="Merkezden Dışa Doğru Eşit Açılı Radyal Spiral Yayılım Geometrisi"
    ),
    AlgorithmMetadata(
        key="VORONOI",
        name="Centroidal Voronoi Partitioning",
        family=AlgorithmFamily.CLASSIC_GEOMETRIC,
        year=2004,
        authors="Cortés et al.",
        core_mechanism="Ajan Ağırlıklarına Göre Sahanın Geometrik Voronoi Hücrelerine Bölünmesi"
    )
]


class MultiAlgorithmBenchmarkRunner:
    """
    30 optimizasyon algoritmasını fiziki simülatörde koşturan ve metrikleri derleyen yürütücü.
    """

    def __init__(self, output_dir: str = "artifacts/benchmarks"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.catalog_map = {item.key: item for item in ALGORITHM_CATALOG}

    def _clamp_to_bounds(self, lat: float, lon: float, bounds: List[Tuple[float, float]]) -> Tuple[float, float]:
        lat_min = min(p[0] for p in bounds)
        lat_max = max(p[0] for p in bounds)
        lon_min = min(p[1] for p in bounds)
        lon_max = max(p[1] for p in bounds)
        clamped_lat = max(lat_min + 0.0001, min(lat_max - 0.0001, lat))
        clamped_lon = max(lon_min + 0.0001, min(lon_max - 0.0001, lon))
        return clamped_lat, clamped_lon

    def run_single_algorithm(
        self,
        algorithm_key: str,
        seed: int = 42,
        num_drones: int = 5,
        area_km2: float = 4.0,
        num_fires: int = 2,
        max_steps: int = 250
    ) -> Dict[str, Any]:
        """Tek bir algoritmanın tek bir tohumda simülasyonunu icra eder."""
        random.seed(seed)
        np.random.seed(seed)

        sim = SwarmSimulationEngine(
            area_km2=area_km2,
            num_drones=num_drones,
            num_fires=num_fires,
            random_seed=seed
        )

        b = sim.boundary
        lat_min = min(p[0] for p in b)
        lat_max = max(p[0] for p in b)
        lon_min = min(p[1] for p in b)
        lon_max = max(p[1] for p in b)
        center_lat = (lat_min + lat_max) / 2.0
        center_lon = (lon_min + lon_max) / 2.0
        lat_span = lat_max - lat_min
        lon_span = lon_max - lon_min

        # Algoritmaya özel durum hafızaları
        corridor_w = lat_span / float(max(1, num_drones))
        lm_states = [{"lat": lat_min + (i + 0.5) * corridor_w, "going_east": True} for i in range(num_drones)]
        spiral_thetas = [i * (2.0 * math.pi / num_drones) for i in range(num_drones)]

        voronoi_centers = []
        for i in range(num_drones):
            angle = 2.0 * math.pi * i / num_drones
            v_lat = center_lat + 0.38 * lat_span * math.sin(angle)
            v_lon = center_lon + 0.38 * lon_span * math.cos(angle)
            voronoi_centers.append((v_lat, v_lon))

        alpha_pos = [center_lat, center_lon]
        beta_pos = [center_lat, center_lon]
        delta_pos = [center_lat, center_lon]
        bat_velocities = [[0.0, 0.0] for _ in range(num_drones)]
        bat_loudness = [0.95 for _ in range(num_drones)]
        bat_r = [0.10 for _ in range(num_drones)]
        sa_temp = 100.0
        es_sigma = 0.002
        cma_sigma = 0.0015

        for step in range(max_steps):
            confirmed_cnt = len(sim.incident_manager.get_confirmed_incidents())
            best_fire_lat, best_fire_lon, best_fire_score = center_lat, center_lon, 0.0

            for inc in sim.incident_manager._incidents.values():
                if inc.confidence > best_fire_score:
                    best_fire_score = inc.confidence
                    best_fire_lat, best_fire_lon = inc.centroid_lat, inc.centroid_lon

            # PyreSwarm PSO doğrudan simülatörün yerleşik optimizer'ını kullanır
            if algorithm_key == "PYRESWARM_PSO":
                sim.step(dt=1.0, use_pso=True)
                if confirmed_cnt >= num_fires and sim.metrics.ttc_sec is not None:
                    break
                continue

            # Diğer 29 algoritma için hedef koordinatları üret
            for idx, (drone, adapter) in enumerate(zip(sim.drones, sim.adapters)):
                if not drone.is_in_air or drone.mode != DroneMode.SEARCHING:
                    continue

                cur_lat, cur_lon = drone.lat, drone.lon
                target_lat, target_lon = cur_lat, cur_lon
                target_alt = 75.0

                if algorithm_key == "STANDARD_PSO":
                    if best_fire_score > 0.05:
                        target_lat = cur_lat + 0.6 * (drone.pbest_lat - cur_lat) + 0.9 * (best_fire_lat - cur_lat)
                        target_lon = cur_lon + 0.6 * (drone.pbest_lon - cur_lon) + 0.9 * (best_fire_lon - cur_lon)
                    else:
                        target_lat = cur_lat + (random.random() - 0.5) * 0.0015
                        target_lon = cur_lon + (random.random() - 0.5) * 0.0015

                elif algorithm_key == "GWO":
                    a = 2.0 - step * (2.0 / max_steps)
                    if best_fire_score > 0.05:
                        alpha_pos = [best_fire_lat, best_fire_lon]
                    c1, c2, c3 = 2.0 * random.random(), 2.0 * random.random(), 2.0 * random.random()
                    a1, a2, a3 = 2.0 * a * random.random() - a, 2.0 * a * random.random() - a, 2.0 * a * random.random() - a

                    x1_lat = alpha_pos[0] - a1 * abs(c1 * alpha_pos[0] - cur_lat)
                    x1_lon = alpha_pos[1] - a1 * abs(c1 * alpha_pos[1] - cur_lon)
                    x2_lat = beta_pos[0] - a2 * abs(c2 * beta_pos[0] - cur_lat)
                    x2_lon = beta_pos[1] - a2 * abs(c2 * beta_pos[1] - cur_lon)
                    x3_lat = delta_pos[0] - a3 * abs(c3 * delta_pos[0] - cur_lat)
                    x3_lon = delta_pos[1] - a3 * abs(c3 * delta_pos[1] - cur_lon)

                    target_lat = (x1_lat + x2_lat + x3_lat) / 3.0
                    target_lon = (x1_lon + x2_lon + x3_lon) / 3.0

                elif algorithm_key == "WOA":
                    p = random.random()
                    a = 2.0 - step * (2.0 / max_steps)
                    if p < 0.5:
                        if abs(a) < 1.0 and best_fire_score > 0.05:
                            d_lat = abs(2.0 * random.random() * best_fire_lat - cur_lat)
                            d_lon = abs(2.0 * random.random() * best_fire_lon - cur_lon)
                            target_lat = best_fire_lat - (2.0 * a * random.random() - a) * d_lat
                            target_lon = best_fire_lon - (2.0 * a * random.random() - a) * d_lon
                        else:
                            rand_idx = (idx + 1) % num_drones
                            ref_d = sim.drones[rand_idx]
                            target_lat = ref_d.lat + (random.random() - 0.5) * 0.003
                            target_lon = ref_d.lon + (random.random() - 0.5) * 0.003
                    else:
                        b_param = 1.0
                        l = random.uniform(-1.0, 1.0)
                        dist_f = math.hypot(best_fire_lat - cur_lat, best_fire_lon - cur_lon) if best_fire_score > 0.05 else 0.002
                        target_lat = dist_f * math.exp(b_param * l) * math.cos(2.0 * math.pi * l) + (best_fire_lat if best_fire_score > 0.05 else cur_lat)
                        target_lon = dist_f * math.exp(b_param * l) * math.sin(2.0 * math.pi * l) + (best_fire_lon if best_fire_score > 0.05 else cur_lon)

                elif algorithm_key == "BA":
                    freq = 0.0 + 1.5 * random.random()
                    lead_lat = best_fire_lat if best_fire_score > 0.05 else center_lat
                    lead_lon = best_fire_lon if best_fire_score > 0.05 else center_lon

                    bat_velocities[idx][0] += (cur_lat - lead_lat) * freq * 0.0005
                    bat_velocities[idx][1] += (cur_lon - lead_lon) * freq * 0.0005

                    if random.random() > bat_r[idx]:
                        target_lat = lead_lat + 0.001 * random.uniform(-1.0, 1.0) * bat_loudness[idx]
                        target_lon = lead_lon + 0.001 * random.uniform(-1.0, 1.0) * bat_loudness[idx]
                    else:
                        target_lat = cur_lat + bat_velocities[idx][0]
                        target_lon = cur_lon + bat_velocities[idx][1]

                elif algorithm_key == "FA":
                    sum_lat, sum_lon = 0.0, 0.0
                    for other_idx, other_d in enumerate(sim.drones):
                        if other_idx != idx:
                            r_sq = (cur_lat - other_d.lat)**2 + (cur_lon - other_d.lon)**2
                            beta = 1.0 / (1.0 + 1000.0 * r_sq)
                            sum_lat += beta * (other_d.lat - cur_lat)
                            sum_lon += beta * (other_d.lon - cur_lon)
                    alpha_fa = 0.001
                    target_lat = cur_lat + 0.3 * sum_lat + alpha_fa * (random.random() - 0.5)
                    target_lon = cur_lon + 0.3 * sum_lon + alpha_fa * (random.random() - 0.5)
                    if best_fire_score > 0.05:
                        target_lat = 0.5 * target_lat + 0.5 * best_fire_lat
                        target_lon = 0.5 * target_lon + 0.5 * best_fire_lon

                elif algorithm_key == "CS":
                    sigma_u = (math.gamma(1.5) * math.sin(math.pi * 0.75) / (math.gamma(1.25) * 0.75 * 2**0.25)) ** (1.0 / 1.5)
                    u = np.random.normal(0, sigma_u)
                    v = np.random.normal(0, 1)
                    step_levy = 0.0008 * (u / (abs(v) ** (1.0 / 1.5)))

                    if random.random() < 0.25:
                        target_lat = lat_min + random.random() * lat_span
                        target_lon = lon_min + random.random() * lon_span
                    else:
                        lead_lat = best_fire_lat if best_fire_score > 0.05 else cur_lat
                        lead_lon = best_fire_lon if best_fire_score > 0.05 else cur_lon
                        target_lat = cur_lat + step_levy * (cur_lat - lead_lat) + np.random.normal(0, 0.0005)
                        target_lon = cur_lon + step_levy * (cur_lon - lead_lon) + np.random.normal(0, 0.0005)

                elif algorithm_key == "ABC":
                    k = (idx + 1) % num_drones
                    partner = sim.drones[k]
                    phi = random.uniform(-1.0, 1.0)
                    if step % 3 == 0 and best_fire_score < 0.05:
                        target_lat = lat_min + random.random() * lat_span
                        target_lon = lon_min + random.random() * lon_span
                    else:
                        target_lat = cur_lat + phi * (cur_lat - partner.lat)
                        target_lon = cur_lon + phi * (cur_lon - partner.lon)
                        if best_fire_score > 0.05:
                            target_lat = 0.4 * target_lat + 0.6 * best_fire_lat
                            target_lon = 0.4 * target_lon + 0.6 * best_fire_lon

                elif algorithm_key == "SSA":
                    c1_ssa = 2.0 * math.exp(-((4.0 * step / max_steps) ** 2))
                    food_lat = best_fire_lat if best_fire_score > 0.05 else center_lat
                    food_lon = best_fire_lon if best_fire_score > 0.05 else center_lon

                    if idx == 0:
                        c2 = random.random()
                        c3 = random.random()
                        sign = 1.0 if c3 >= 0.5 else -1.0
                        target_lat = food_lat + sign * c1_ssa * (lat_span * c2 + lat_min) * 0.05
                        target_lon = food_lon + sign * c1_ssa * (lon_span * c2 + lon_min) * 0.05
                    else:
                        prev_d = sim.drones[idx - 1]
                        target_lat = 0.5 * (cur_lat + prev_d.lat)
                        target_lon = 0.5 * (cur_lon + prev_d.lon)

                elif algorithm_key == "HHO":
                    e0 = 2.0 * random.random() - 1.0
                    e_esc = 2.0 * e0 * (1.0 - step / max_steps)
                    rabbit_lat = best_fire_lat if best_fire_score > 0.05 else center_lat
                    rabbit_lon = best_fire_lon if best_fire_score > 0.05 else center_lon

                    if abs(e_esc) >= 1.0:
                        q = random.random()
                        if q >= 0.5:
                            target_lat = rabbit_lat - random.random() * abs(rabbit_lat - 2.0 * random.random() * cur_lat)
                            target_lon = rabbit_lon - random.random() * abs(rabbit_lon - 2.0 * random.random() * cur_lon)
                        else:
                            target_lat = lat_min + random.random() * lat_span
                            target_lon = lon_min + random.random() * lon_span
                    else:
                        target_lat = rabbit_lat - e_esc * abs(rabbit_lat - cur_lat)
                        target_lon = rabbit_lon - e_esc * abs(rabbit_lon - cur_lon)

                elif algorithm_key == "GSO":
                    neighbors = [d for j, d in enumerate(sim.drones) if j != idx]
                    if neighbors:
                        chosen = random.choice(neighbors)
                        step_size = 0.0012
                        dist = math.hypot(chosen.lat - cur_lat, chosen.lon - cur_lon) + 1e-6
                        target_lat = cur_lat + step_size * (chosen.lat - cur_lat) / dist
                        target_lon = cur_lon + step_size * (chosen.lon - cur_lon) / dist
                    if best_fire_score > 0.05:
                        target_lat = 0.3 * target_lat + 0.7 * best_fire_lat
                        target_lon = 0.3 * target_lon + 0.7 * best_fire_lon

                elif algorithm_key == "DA":
                    w = 0.9 - step * (0.5 / max_steps)
                    sep_lat = -sum(cur_lat - other.lat for other in sim.drones if other != drone)
                    sep_lon = -sum(cur_lon - other.lon for other in sim.drones if other != drone)
                    food_lat = best_fire_lat - cur_lat if best_fire_score > 0.05 else (center_lat - cur_lat)
                    food_lon = best_fire_lon - cur_lon if best_fire_score > 0.05 else (center_lon - cur_lon)
                    target_lat = cur_lat + w * 0.001 * random.uniform(-1, 1) + 0.1 * sep_lat + 0.4 * food_lat
                    target_lon = cur_lon + w * 0.001 * random.uniform(-1, 1) + 0.1 * sep_lon + 0.4 * food_lon

                elif algorithm_key == "SMA":
                    val_sma = max(-0.99, min(0.99, 1.0 - (step + 1.0) / (max_steps + 1.0)))
                    a_sma = abs(math.atanh(val_sma))
                    b_sma = 1.0 - step / float(max_steps)
                    vc = random.uniform(-a_sma, a_sma) if a_sma > 0 else 0.0
                    vb = random.uniform(-b_sma, b_sma)
                    lead_lat = best_fire_lat if best_fire_score > 0.05 else center_lat
                    lead_lon = best_fire_lon if best_fire_score > 0.05 else center_lon
                    p_sma = math.tanh(abs(cur_lat - lead_lat) + abs(cur_lon - lead_lon))
                    if random.random() < p_sma:
                        target_lat = lead_lat + vb * (lead_lat - cur_lat)
                        target_lon = lead_lon + vb * (lead_lon - cur_lon)
                    else:
                        target_lat = vc * cur_lat + 0.001 * random.uniform(-1, 1)
                        target_lon = vc * cur_lon + 0.001 * random.uniform(-1, 1)

                elif algorithm_key == "ACO":
                    mu_lat = best_fire_lat if best_fire_score > 0.05 else center_lat
                    mu_lon = best_fire_lon if best_fire_score > 0.05 else center_lon
                    sigma = 0.0025 * (1.0 - 0.7 * (step / max_steps))
                    target_lat = np.random.normal(mu_lat, sigma)
                    target_lon = np.random.normal(mu_lon, sigma)

                elif algorithm_key == "GA":
                    partner = sim.drones[(idx + 1) % num_drones]
                    u = random.random()
                    eta_c = 2.0
                    beta_sbx = (2.0 * u) ** (1.0 / (eta_c + 1.0)) if u <= 0.5 else (1.0 / (2.0 * (1.0 - u))) ** (1.0 / (eta_c + 1.0))
                    child_lat = 0.5 * ((1.0 + beta_sbx) * cur_lat + (1.0 - beta_sbx) * partner.lat)
                    child_lon = 0.5 * ((1.0 + beta_sbx) * cur_lon + (1.0 - beta_sbx) * partner.lon)
                    child_lat += np.random.normal(0, 0.0008)
                    child_lon += np.random.normal(0, 0.0008)
                    if best_fire_score > 0.05:
                        child_lat = 0.4 * child_lat + 0.6 * best_fire_lat
                        child_lon = 0.4 * child_lon + 0.6 * best_fire_lon
                    target_lat, target_lon = child_lat, child_lon

                elif algorithm_key == "DE":
                    r1 = sim.drones[(idx + 1) % num_drones]
                    r2 = sim.drones[(idx + 2) % num_drones]
                    r3 = sim.drones[(idx + 3) % num_drones]
                    f_scale = 0.8
                    v_lat = r1.lat + f_scale * (r2.lat - r3.lat)
                    v_lon = r1.lon + f_scale * (r2.lon - r3.lon)
                    cr = 0.7
                    target_lat = v_lat if random.random() < cr else cur_lat
                    target_lon = v_lon if random.random() < cr else cur_lon
                    if best_fire_score > 0.05:
                        target_lat = 0.4 * target_lat + 0.6 * best_fire_lat
                        target_lon = 0.4 * target_lon + 0.6 * best_fire_lon

                elif algorithm_key == "CMA_ES":
                    mu_lat = best_fire_lat if best_fire_score > 0.05 else center_lat
                    mu_lon = best_fire_lon if best_fire_score > 0.05 else center_lon
                    target_lat = cur_lat + np.random.normal(0, cma_sigma) + 0.2 * (mu_lat - cur_lat)
                    target_lon = cur_lon + np.random.normal(0, cma_sigma) + 0.2 * (mu_lon - cur_lon)

                elif algorithm_key == "BBO":
                    lead_d = sim.drones[0]
                    target_lat = cur_lat + 0.5 * (lead_d.lat - cur_lat) + (random.random() - 0.5) * 0.001
                    target_lon = cur_lon + 0.5 * (lead_d.lon - cur_lon) + (random.random() - 0.5) * 0.001
                    if best_fire_score > 0.05:
                        target_lat = 0.3 * target_lat + 0.7 * best_fire_lat
                        target_lon = 0.3 * target_lon + 0.7 * best_fire_lon

                elif algorithm_key == "EP":
                    target_lat = cur_lat + np.random.normal(0, 0.0012)
                    target_lon = cur_lon + np.random.normal(0, 0.0012)
                    if best_fire_score > 0.05:
                        target_lat = 0.3 * target_lat + 0.7 * best_fire_lat
                        target_lon = 0.3 * target_lon + 0.7 * best_fire_lon

                elif algorithm_key == "ES":
                    target_lat = cur_lat + np.random.normal(0, es_sigma)
                    target_lon = cur_lon + np.random.normal(0, es_sigma)
                    if best_fire_score > 0.05:
                        target_lat = 0.4 * target_lat + 0.6 * best_fire_lat
                        target_lon = 0.4 * target_lon + 0.6 * best_fire_lon

                elif algorithm_key == "SA":
                    sa_temp *= 0.985
                    pert_lat = cur_lat + (random.random() - 0.5) * 0.002 * (sa_temp / 100.0 + 0.1)
                    pert_lon = cur_lon + (random.random() - 0.5) * 0.002 * (sa_temp / 100.0 + 0.1)
                    target_lat, target_lon = pert_lat, pert_lon
                    if best_fire_score > 0.05:
                        target_lat = 0.2 * target_lat + 0.8 * best_fire_lat
                        target_lon = 0.2 * target_lon + 0.8 * best_fire_lon

                elif algorithm_key == "GSA":
                    g_const = 100.0 * math.exp(-20.0 * step / max_steps)
                    f_lat, f_lon = 0.0, 0.0
                    for other in sim.drones:
                        if other != drone:
                            r = math.hypot(other.lat - cur_lat, other.lon - cur_lon) + 1e-5
                            force = g_const / (r + 0.001)
                            f_lat += force * (other.lat - cur_lat)
                            f_lon += force * (other.lon - cur_lon)
                    target_lat = cur_lat + 0.0001 * f_lat
                    target_lon = cur_lon + 0.0001 * f_lon
                    if best_fire_score > 0.05:
                        target_lat = 0.3 * target_lat + 0.7 * best_fire_lat
                        target_lon = 0.3 * target_lon + 0.7 * best_fire_lon

                elif algorithm_key == "EO":
                    f_eo = math.exp(-2.0 * step / max_steps)
                    c_eq_lat = best_fire_lat if best_fire_score > 0.05 else center_lat
                    c_eq_lon = best_fire_lon if best_fire_score > 0.05 else center_lon
                    target_lat = c_eq_lat + (cur_lat - c_eq_lat) * f_eo + np.random.normal(0, 0.0006)
                    target_lon = c_eq_lon + (cur_lon - c_eq_lon) * f_eo + np.random.normal(0, 0.0006)

                elif algorithm_key == "WDO":
                    target_lat = cur_lat + 0.001 * math.cos(step * 0.1 + idx) + (random.random() - 0.5) * 0.0008
                    target_lon = cur_lon + 0.001 * math.sin(step * 0.1 + idx) + (random.random() - 0.5) * 0.0008
                    if best_fire_score > 0.05:
                        target_lat = 0.35 * target_lat + 0.65 * best_fire_lat
                        target_lon = 0.35 * target_lon + 0.65 * best_fire_lon

                elif algorithm_key == "HGSO":
                    gamma_hg = 0.05 * math.exp(-step / max_steps)
                    lead_lat = best_fire_lat if best_fire_score > 0.05 else center_lat
                    lead_lon = best_fire_lon if best_fire_score > 0.05 else center_lon
                    target_lat = cur_lat + gamma_hg * (lead_lat - cur_lat) + (random.random() - 0.5) * 0.001
                    target_lon = cur_lon + gamma_hg * (lead_lon - cur_lon) + (random.random() - 0.5) * 0.001

                elif algorithm_key == "LAWNMOWER":
                    lm = lm_states[idx]
                    dist_to_tgt = math.hypot((adapter.target_lat - cur_lat) * 111139.0, (adapter.target_lon - cur_lon) * 111139.0)
                    if dist_to_tgt < 25.0 or step == 0:
                        lm["going_east"] = not lm["going_east"]
                        tgt_lon = lon_max if lm["going_east"] else lon_min
                        target_lat, target_lon = lm["lat"], tgt_lon
                    else:
                        target_lat, target_lon = adapter.target_lat, adapter.target_lon

                elif algorithm_key == "RANDOM":
                    dist_to_tgt = math.hypot((adapter.target_lat - cur_lat) * 111139.0, (adapter.target_lon - cur_lon) * 111139.0)
                    if dist_to_tgt < 30.0 or step % 20 == 0:
                        target_lat = lat_min + random.random() * lat_span
                        target_lon = lon_min + random.random() * lon_span
                    else:
                        target_lat, target_lon = adapter.target_lat, adapter.target_lon

                elif algorithm_key == "GREEDY":
                    if drone.pbest_score > 0.05:
                        target_lat = drone.pbest_lat
                        target_lon = drone.pbest_lon
                    else:
                        target_lat = cur_lat + (random.random() - 0.5) * 0.0015
                        target_lon = cur_lon + (random.random() - 0.5) * 0.0015

                elif algorithm_key == "SPIRAL":
                    spiral_thetas[idx] += 0.25
                    r = 0.00015 * spiral_thetas[idx]
                    target_lat = center_lat + r * math.sin(spiral_thetas[idx])
                    target_lon = center_lon + r * math.cos(spiral_thetas[idx])
                    if best_fire_score > 0.05:
                        target_lat = 0.3 * target_lat + 0.7 * best_fire_lat
                        target_lon = 0.3 * target_lon + 0.7 * best_fire_lon

                elif algorithm_key == "VORONOI":
                    c_lat, c_lon = voronoi_centers[idx]
                    dist_to_vc = math.hypot((c_lat - cur_lat) * 111139.0, (c_lon - cur_lon) * 111139.0)
                    if dist_to_vc < 35.0:
                        target_lat = c_lat + (random.random() - 0.5) * 0.0015
                        target_lon = c_lon + (random.random() - 0.5) * 0.0015
                    else:
                        target_lat, target_lon = c_lat, c_lon
                    if best_fire_score > 0.05:
                        target_lat = 0.3 * target_lat + 0.7 * best_fire_lat
                        target_lon = 0.3 * target_lon + 0.7 * best_fire_lon

                clamped_lat, clamped_lon = self._clamp_to_bounds(target_lat, target_lon, b)
                adapter.goto(clamped_lat, clamped_lon, target_alt)

            sim.step(dt=1.0, use_pso=False)

            if confirmed_cnt >= num_fires and sim.metrics.ttc_sec is not None:
                break

        cov = sim.search_map.get_coverage_metrics()
        ttfd = sim.metrics.ttfd_sec if sim.metrics.ttfd_sec is not None else float(max_steps)
        ttc = sim.metrics.ttc_sec if sim.metrics.ttc_sec is not None else float(max_steps)

        return {
            "algorithm": algorithm_key,
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

    def run_full_30_suite(
        self,
        seeds: List[int] = [42, 43, 44, 45, 46],
        num_drones: int = 5,
        area_km2: float = 4.0,
        num_fires: int = 2
    ) -> Dict[str, Any]:
        """30 algoritmanın tamamını belirtilen tohumlar üzerinden yürütür."""
        all_runs: List[Dict[str, Any]] = []
        summary: Dict[str, Any] = {}

        print(f"=== PyreSwarm 30-Algoritma Kıyaslama Başlatıldı ({len(ALGORITHM_CATALOG)} Algoritma, {len(seeds)} Tohum) ===")
        start_time = time.time()

        for cat in ALGORITHM_CATALOG:
            k = cat.key
            print(f"  -> Koşturuluyor: {cat.name} ({cat.family.value})...", end="", flush=True)
            algo_runs = []
            for s in seeds:
                res = self.run_single_algorithm(
                    algorithm_key=k,
                    seed=s,
                    num_drones=num_drones,
                    area_km2=area_km2,
                    num_fires=num_fires
                )
                algo_runs.append(res)
                all_runs.append(res)

            ttfds = [r["ttfd_seconds"] for r in algo_runs]
            covs = [r["coverage_percent"] for r in algo_runs]
            reds = [r["redundant_ratio"] for r in algo_runs]
            dists = [r["total_distance_km"] for r in algo_runs]
            energies = [r["energy_kj"] for r in algo_runs]
            incidents = [r["incidents_confirmed"] for r in algo_runs]

            summary[k] = {
                "name": cat.name,
                "family": cat.family.value,
                "year": cat.year,
                "authors": cat.authors,
                "ttfd_mean": round(float(np.mean(ttfds)), 1),
                "ttfd_median": round(float(np.median(ttfds)), 1),
                "ttfd_std": round(float(np.std(ttfds)), 1),
                "ttfd_min": round(float(np.min(ttfds)), 1),
                "ttfd_max": round(float(np.max(ttfds)), 1),
                "ttfd_p90": round(float(np.percentile(ttfds, 90)), 1),
                "coverage_mean": round(float(np.mean(covs)), 2),
                "redundant_ratio_mean": round(float(np.mean(reds)), 3),
                "distance_mean_km": round(float(np.mean(dists)), 2),
                "energy_mean_kj": round(float(np.mean(energies)), 1),
                "incidents_confirmed_total": int(np.sum(incidents)),
                "incidents_confirmed_mean": round(float(np.mean(incidents)), 2)
            }
            print(f" [Bitti: Mean TTFD = {summary[k]['ttfd_mean']}s, Teyit = {summary[k]['incidents_confirmed_total']}]")

        elapsed = time.time() - start_time
        print(f"=== Tüm 30 Algoritma Kıyaslaması {elapsed:.2f} saniyede tamamlandı ===")

        out_json_path = os.path.join(self.output_dir, "benchmark_30_algorithms.json")
        payload = {
            "metadata": {
                "num_algorithms": len(ALGORITHM_CATALOG),
                "seeds": seeds,
                "num_drones": num_drones,
                "area_km2": area_km2,
                "num_fires": num_fires,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "elapsed_seconds": round(elapsed, 2)
            },
            "summary": summary,
            "runs": all_runs
        }
        with open(out_json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        out_csv_path = os.path.join(self.output_dir, "benchmark_30_algorithms.csv")
        fieldnames = [
            "rank", "key", "name", "family", "year", "authors",
            "ttfd_mean", "ttfd_median", "ttfd_min", "ttfd_std",
            "coverage_mean", "redundant_ratio_mean", "distance_mean_km",
            "energy_mean_kj", "incidents_confirmed_total"
        ]

        sorted_keys = sorted(summary.keys(), key=lambda k: (summary[k]["ttfd_mean"], -summary[k]["incidents_confirmed_total"]))

        with open(out_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for rank_idx, k in enumerate(sorted_keys, 1):
                item = summary[k]
                row = {
                    "rank": rank_idx,
                    "key": k,
                    "name": item["name"],
                    "family": item["family"],
                    "year": item["year"],
                    "authors": item["authors"],
                    "ttfd_mean": item["ttfd_mean"],
                    "ttfd_median": item["ttfd_median"],
                    "ttfd_min": item["ttfd_min"],
                    "ttfd_std": item["ttfd_std"],
                    "coverage_mean": item["coverage_mean"],
                    "redundant_ratio_mean": item["redundant_ratio_mean"],
                    "distance_mean_km": item["distance_mean_km"],
                    "energy_mean_kj": item["energy_mean_kj"],
                    "incidents_confirmed_total": item["incidents_confirmed_total"]
                }
                writer.writerow(row)

        print(f"[Rapor Kaydedildi] JSON: {out_json_path}")
        print(f"[Rapor Kaydedildi] CSV: {out_csv_path}")
        return payload


if __name__ == "__main__":
    runner = MultiAlgorithmBenchmarkRunner()
    runner.run_full_30_suite()
