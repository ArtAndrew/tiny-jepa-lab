"""Build a standalone HTML with actual MLP inference and embedded numeric weights."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent


def state_to_json(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as arrays:
        return {key: {"shape": list(arrays[key].shape),
                      "data": [float(f"{v:.8g}") for v in arrays[key].ravel()]}
                for key in arrays.files}


def package(path: Path) -> dict:
    for filename in ["model.npz", "probe.npz", "config.json", "metrics.json"]:
        if not (path / filename).exists():
            raise FileNotFoundError(f"Missing {path / filename}; run evaluate.py first")
    return {"weights": state_to_json(path / "model.npz"),
            "probe": state_to_json(path / "probe.npz"),
            "config": json.loads((path / "config.json").read_text(encoding="utf-8")),
            "metrics": json.loads((path / "metrics.json").read_text(encoding="utf-8"))}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", type=Path, default=ROOT / "artifacts/pretrained")
    p.add_argument("--ablation", type=Path, default=None)
    p.add_argument("--output", type=Path, default=ROOT / "demo.html")
    p.add_argument("--export-json", type=Path, default=None, help="Optional test/debug export")
    args = p.parse_args()
    pack = package(args.model)
    if pack["config"] != {"size":24,"dim":8,"max_horizon":4,"margin":.08,"sigma":.042,"noise":.03,"min_speed":.025,"max_speed":.065,"ema":.99}:
        p.error("This educational UI expects the default 24x24 / 8-dimensional config")
    packs = {"pretrained": pack}
    if args.ablation is not None:
        packs["no_regularization"] = package(args.ablation)
        if packs["no_regularization"]["config"] != pack["config"]:
            p.error("Both compared models must use the same configuration")
    content = json.dumps(packs, separators=(",", ":"))
    html = (ROOT / "web/template.html").read_text(encoding="utf-8")
    html = html.replace("__WEIGHTS__", content).replace("__ENGINE__", (ROOT / "web/engine.js").read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")
    if args.export_json:
        args.export_json.write_text(content, encoding="utf-8")
    print(f"Wrote {args.output} ({args.output.stat().st_size / 1024**2:.2f} MiB). Open locally in a browser.")


if __name__ == "__main__":
    main()
