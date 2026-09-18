"""
PyreSwarm - 30 Algoritma Kıyaslama Paketi Birim ve Regresyon Testleri
"""

import pytest
import os
import json
from benchmarks.multi_algorithm_suite import (
    MultiAlgorithmBenchmarkRunner,
    ALGORITHM_CATALOG,
    AlgorithmFamily
)


def test_catalog_completeness():
    """Katalogda tam olarak 30 algoritmanın ve tüm ailelerin eksiksiz olduğunu doğrular."""
    assert len(ALGORITHM_CATALOG) == 30, f"Beklenen 30 algoritma, bulunan: {len(ALGORITHM_CATALOG)}"

    families = {item.family for item in ALGORITHM_CATALOG}
    assert AlgorithmFamily.SWARM_INTELLIGENCE in families
    assert AlgorithmFamily.EVOLUTIONARY in families
    assert AlgorithmFamily.PHYSICS_BASED in families
    assert AlgorithmFamily.CLASSIC_GEOMETRIC in families

    keys = [item.key for item in ALGORITHM_CATALOG]
    assert len(keys) == len(set(keys)), "Algoritma anahtarları benzersiz olmalıdır."


def test_single_algorithm_execution():
    """Rastgele seçilen bir algoritmanın hatasız simülasyon adımı işlettiğini doğrular."""
    runner = MultiAlgorithmBenchmarkRunner()
    result = runner.run_single_algorithm(
        algorithm_key="BA",
        seed=42,
        num_drones=3,
        area_km2=1.0,
        num_fires=1,
        max_steps=15
    )

    assert result["algorithm"] == "BA"
    assert result["seed"] == 42
    assert "ttfd_seconds" in result
    assert "coverage_percent" in result
    assert "redundant_ratio" in result
    assert result["steps_executed"] <= 15


def test_benchmark_artifacts_integrity():
    """Üretilen 30 algoritma JSON ve CSV raporlarının doğruluğunu ve eksiksizliğini test eder."""
    json_path = os.path.join("artifacts", "benchmarks", "benchmark_30_algorithms.json")
    csv_path = os.path.join("artifacts", "benchmarks", "benchmark_30_algorithms.csv")

    assert os.path.exists(json_path), f"{json_path} bulunamadı."
    assert os.path.exists(csv_path), f"{csv_path} bulunamadı."

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "summary" in data
    assert len(data["summary"]) == 30
    assert "PYRESWARM_PSO" in data["summary"]
    assert "STANDARD_PSO" in data["summary"]
    assert "LAWNMOWER" in data["summary"]
    assert "RANDOM" in data["summary"]

    # PyreSwarm'ın standart PSO'dan üstün olduğunu doğrula
    pyreswarm_ttfd = data["summary"]["PYRESWARM_PSO"]["ttfd_mean"]
    standard_pso_ttfd = data["summary"]["STANDARD_PSO"]["ttfd_mean"]
    assert pyreswarm_ttfd < standard_pso_ttfd, f"PyreSwarm ({pyreswarm_ttfd}s) standart PSO'dan ({standard_pso_ttfd}s) daha hızlı olmalıdır."
