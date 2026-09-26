"""
Merge the parallel benchmark chunks into one result per scenario.

    py -3.11 scripts/merge_search_parts.py

Reads  artifacts/search_v2/parts/{uniform,spotting}_*/runs.json
Writes artifacts/search_v2/final_{uniform,spotting}/{runs,summary}.json
The per-second trajectory ("history") is dropped from the merged runs to keep the
repository small; rerun compare_swarm_search.py with the same seeds to regenerate it.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from compare_swarm_search import summarize  # noqa: E402

V2 = ROOT / "artifacts" / "search_v2"


def main():
    for kind in ("uniform", "spotting"):
        rows = []
        for part in sorted((V2 / "parts").glob(f"{kind}_*")):
            rows += json.loads((part / "runs.json").read_text(encoding="utf-8"))
        if not rows:
            continue
        names = list(dict.fromkeys(r["algorithm"] for r in rows))
        seeds = sorted({r["seed"] for r in rows})
        summary = summarize(rows, names, seeds)
        out = V2 / f"final_{kind}"
        out.mkdir(parents=True, exist_ok=True)
        slim = [{k: v for k, v in r.items() if k != "history"} for r in rows]
        (out / "runs.json").write_text(json.dumps(slim, ensure_ascii=False), encoding="utf-8")
        (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        print(kind, len(rows), "runs,", len(names), "methods, seeds", seeds[0], "-", seeds[-1], "->", out)


if __name__ == "__main__":
    main()
