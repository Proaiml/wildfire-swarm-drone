"""
Figures and tables for the search comparison (final held-out seeds 241-280) and the ArduPilot SITL swarm trial.

    py -3.11 scripts/make_search_report.py

Reads  artifacts/search_v2/final_{uniform,spotting}/{summary,runs}.json (scripts/merge_search_parts.py)
       artifacts/sitl_trial/result.json
Writes docs/figures/search_v2_comparison.png, docs/figures/search_v2_cdf.png,
       docs/figures/sitl_swarm_tracks.png and prints the Markdown tables used in the README.
"""
import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / "artifacts" / "search_v2"
FIG = ROOT / "docs" / "figures"
HUBS = {"Hub-Hybrid-PSO": "Hub hibrit (yeni varsayılan)", "Hub-Lanes-Matched": "Hub şerit (sensöre uygun aralık)",
        "Hub-Constrained-PSO": "Hub şerit (yayımlanan eski)", "Hub-Adaptive-PSO": "Hub tam uyarlanır",
        "Random-waypoints": "Rastgele hedef"}
SCEN = {"uniform": "Rastgele konumlu yangınlar", "spotting": "Rüzgâr altı artçı yangınlar"}
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
HUB_COLOR, LIB_COLOR, OLD_COLOR = "#2563eb", "#9ca3af", "#ea580c"


def label(name):
    if name in HUBS:
        return HUBS[name]
    return "CMA-ES" if name == "ES.CMA_ES" else name.split(".")[0] + " (MEALPY)"


def load(kind):
    folder = V2 / f"final_{kind}"
    summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    runs = [r for r in json.loads((folder / "runs.json").read_text(encoding="utf-8")) if r.get("status") == "ok"]
    return summary, runs


def table(summary, top=12):
    rows = sorted(summary["ranking"], key=lambda r: (not r["safety_pass"], -r["recall"], r["penalized_delay_s"]))
    keep = [r for r in rows if r["algorithm"] in HUBS] + [r for r in rows if r["algorithm"] not in HUBS][:top - len(HUBS)]
    keep = sorted(keep, key=lambda r: (not r["safety_pass"], -r["recall"], r["penalized_delay_s"]))
    lines = ["| Sıra | Yöntem | İlk yangın (s) | Bulunan | Artçı bulunan | Artçı tespit süresi (s) | Ortalama gecikme (s) | En az ayrılma (m) |",
             "|---:|---|---:|---:|---:|---:|---:|---:|"]
    order = {r["algorithm"]: i + 1 for i, r in enumerate(rows)}
    for r in keep:
        name = label(r["algorithm"])
        if r["algorithm"] == "Hub-Hybrid-PSO":
            name = f"**{name}**"
        lines.append(f"| {order[r['algorithm']]}/{len(rows)} | {name} | {r['first_detection_s']:.1f} | %{100 * r['recall']:.1f} | "
                     f"%{100 * r['secondary_recall']:.1f} | {r['secondary_delay_s']:.1f} | {r['penalized_delay_s']:.1f} | "
                     f"{r['minimum_separation_m']:.1f} |")
    return "\n".join(lines)


def comparison_figure(data):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.2), sharex=False)
    for ax, (kind, (summary, _)) in zip(axes, data.items()):
        rows = sorted(summary["ranking"], key=lambda r: r["penalized_delay_s"])
        libs = [r for r in rows if r["algorithm"] not in HUBS][:6]
        chosen = [r for r in rows if r["algorithm"] in HUBS] + libs
        chosen = sorted(chosen, key=lambda r: r["penalized_delay_s"], reverse=True)
        names = [label(r["algorithm"]) for r in chosen]
        colors = [HUB_COLOR if r["algorithm"] == "Hub-Hybrid-PSO" else OLD_COLOR if r["algorithm"] == "Hub-Constrained-PSO"
                  else "#e5e7eb" if r["algorithm"] == "Random-waypoints"
                  else "#60a5fa" if r["algorithm"] in HUBS else LIB_COLOR for r in chosen]
        y = np.arange(len(chosen))
        ax.barh(y, [r["penalized_delay_s"] for r in chosen], color=colors, height=0.62)
        for i, r in enumerate(chosen):
            ax.text(r["penalized_delay_s"] + 3, i, f"%{100 * r['recall']:.0f} bulundu · artçı %{100 * r['secondary_recall']:.0f}",
                    va="center", fontsize=8.5, color="#374151")
        ax.set_yticks(y, names)
        ax.set_xlabel("Tutuşmadan tespite ort. süre (s), kısa = iyi; kaçırılan = 600 s")
        ax.set_title(f"{SCEN[kind]} · {summary['completed_runs'] // len(summary['algorithms'])} yeni tohum")
        ax.set_xlim(0, max(r["penalized_delay_s"] for r in chosen) * 1.62)
    seeds = f"{data['uniform'][0]['seeds'][0]}-{data['uniform'][0]['seeds'][-1]}"
    fig.suptitle(f"Yangın ve artçı yangın arama karşılaştırması (ayar sırasında hiç kullanılmamış tohumlar {seeds})", fontsize=12)
    fig.tight_layout()
    path = FIG / "search_v2_comparison.png"
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def cdf_figure(data):
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6), sharey=True)
    for ax, (kind, (summary, runs)) in zip(axes, data.items()):
        best_lib = next(r["algorithm"] for r in sorted(summary["ranking"], key=lambda r: r["penalized_delay_s"])
                        if r["algorithm"] not in HUBS)
        for name, color, style in (("Hub-Hybrid-PSO", HUB_COLOR, "-"), ("Hub-Constrained-PSO", OLD_COLOR, "--"),
                                   (best_lib, "#6b7280", "-."), ("Random-waypoints", "#d1d5db", ":")):
            delays = []
            for r in runs:
                if r["algorithm"] != name:
                    continue
                for t in r["targets"]:
                    delays.append((t["detected_s"] - t["ignition_s"]) if t["detected_s"] is not None else np.inf)
            grid = np.linspace(0, 600, 301)
            frac = [np.mean(np.array(delays) <= g) for g in grid]
            ax.plot(grid, frac, style, color=color, lw=2 if name == "Hub-Hybrid-PSO" else 1.5, label=label(name))
        ax.set_title(SCEN[kind])
        ax.set_xlabel("Tutuşmadan bu yana geçen süre (s)")
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("Bulunan yangın oranı")
    axes[1].legend(loc="lower right", frameon=False)
    fig.tight_layout()
    path = FIG / "search_v2_cdf.png"
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def sitl_figure():
    path = ROOT / "artifacts" / "sitl_trial" / "result.json"
    if not path.exists():
        return None
    r = json.loads(path.read_text(encoding="utf-8"))
    if not r.get("tracks"):
        return None
    lat0 = r["aoi"]["min_lat"]
    lon0 = r["aoi"]["min_lon"]
    sx = 111139 * math.cos(math.radians(lat0))

    def xy(lat, lon):
        return (lon - lon0) * sx, (lat - lat0) * 111139

    fig, ax = plt.subplots(figsize=(7.4, 7))
    b = r["aoi"]
    x1, y1 = xy(b["max_lat"], b["max_lon"])
    ax.add_patch(plt.Rectangle((0, 0), x1, y1, fill=False, ls="--", color="#0e7490", lw=1.2))
    colors = ["#2563eb", "#9333ea", "#059669"]
    ids = list(r["tracks"][0]["drones"].keys())
    for i, did in enumerate(ids):
        pts = np.array([xy(s["drones"][did][0], s["drones"][did][1]) for s in r["tracks"] if s["drones"][did][0]])
        ax.plot(pts[:, 0], pts[:, 1], color=colors[i % 3], lw=1.3, label=f"{did} (ArduPilot SITL)")
        ax.plot(*pts[-1], "o", color=colors[i % 3], ms=5)
    for t in r["targets"]:
        tx, ty = xy(t["lat"], t["lon"])
        drill = next((d for d in r["steps"]["drill"] if d["id"] == t["id"]), {})
        ax.plot(tx, ty, "*", ms=17, color="#dc2626" if not t["aftershock"] else "#f59e0b", mec="k", mew=0.6)
        if drill.get("delay_s") is None:
            text = f"{'artçı' if t['aftershock'] else 'yangın'}: bulunamadı"
        elif t["aftershock"]:
            text = f"artçı ({t['ignition_s']:.0f}. s'de tutuştu):\n{drill['delay_s']:.0f} s sonra bulundu"
        else:
            text = f"yangın: {drill['delay_s']:.0f}. s'de bulundu"
        ax.annotate(text, (tx, ty), xytext=(8, 8), textcoords="offset points", fontsize=9,
                    bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#d1d5db"))
    for c in r["incidents"]:
        ax.plot(*xy(c["lat"], c["lon"]), "o", ms=13, mfc="none", mec="#f97316", mew=1.8)
    ax.set_aspect("equal")
    ax.set_xlabel("doğu (m)")
    ax.set_ylabel("kuzey (m)")
    ax.set_title("Gerçek ArduPilot uçuş koduyla (SITL) 3 drone'luk sürü\n★ gizli tatbikat yangını · ○ hub'ın bulduğu olay")
    ax.legend(loc="lower left", fontsize=8, frameon=True)
    fig.tight_layout()
    out = FIG / "sitl_swarm_tracks.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    FIG.mkdir(parents=True, exist_ok=True)
    data = {kind: load(kind) for kind in ("uniform", "spotting") if (V2 / f"final_{kind}" / "summary.json").exists()}
    for kind, (summary, _) in data.items():
        print(f"\n### {SCEN[kind]} ({summary['completed_runs']} koşu, durum: {summary['status']})\n")
        print(table(summary))
    if len(data) == 2:
        print("\n", comparison_figure(data))
        print(cdf_figure(data))
    print(sitl_figure())


if __name__ == "__main__":
    main()
