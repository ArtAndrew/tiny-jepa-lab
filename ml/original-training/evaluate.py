"""Fit a frozen-encoder diagnostic probe, then test on independent trajectories."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import torch
from tinyjepa.core import load_model
from tinyjepa.evaluation import fit_probe, load_probe, measure


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=Path("artifacts/pretrained"))
    parser.add_argument("--samples", type=int, default=2048)
    parser.add_argument("--probe-steps", type=int, default=800)
    parser.add_argument("--reuse-probe", action="store_true")
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()
    if args.samples < 64 or args.samples % 64 != 0:
        parser.error("--samples must be a positive multiple of 64")
    if args.probe_steps < 1 or args.threads < 1:
        parser.error("--probe-steps and --threads must be positive")
    torch.set_num_threads(args.threads)
    model = load_model(args.model)
    print("Frozen encoder. Fitting a diagnostic coordinate probe; not training JEPA.", flush=True)
    probe = load_probe(args.model, model.cfg.dim) if args.reuse_probe else fit_probe(
        model, args.model, args.probe_steps)
    results = {}
    for label, seed, noise, speed in [("in_distribution", 20001, None, 1.0),
                                     ("high_noise", 20002, 0.18, 1.0),
                                     ("double_speed", 20003, None, 2.0)]:
        report, arrays = measure(model, probe, args.samples, seed, noise, speed)
        if label == "in_distribution":
            np.savez_compressed(args.model / "test_predictions.npz", **{
                key: value.numpy() for key, value in arrays.items()})
            linear_path = args.model / "linear_probe.npy"
            if linear_path.exists():
                w = torch.from_numpy(np.load(linear_path, allow_pickle=False))
                z = arrays["target_z"]
                estimate = torch.cat((z, torch.ones(len(z), 1)), dim=1) @ w
                report["linear_observed_probe_error_px"] = float(
                    ((estimate - arrays["xy"]) * (model.cfg.size - 1)).norm(dim=1).mean())
        results[label] = report
        print(f"{label}: JEPA={report['jepa_error']['mean']:.3f}px; "
              f"stationary={report['stationary_error']['mean']:.3f}px; "
              f"explicit physics={report['physics_error']['mean']:.3f}px; "
              f"probe={report['probe_error']['mean']:.3f}px; "
              f"retrieval={100*report['retrieval']['mean']:.1f}%", flush=True)
    results["protocol"] = {
        "training_seed": 42, "probe_examples": 8192, "probe_seed": 10001,
        "probe_steps": args.probe_steps,
        "error": "Mean Euclidean position error in a 24x24 frame, NOT pixel reconstruction loss",
        "confidence_intervals": "Approximate normal 95% CI across test examples, not across training seeds",
        "scope": "One trained checkpoint, synthetic data; no claim of real-world generalization",
        "probe_supervision": "Coordinates used only after JEPA is frozen; probe fits observed, not predicted embeddings",
        "physics_baseline": "Pixel centroid + two-frame velocity + hardcoded reflection at known walls",
        "ood": "High noise and double speed deliberately differ from training; no retraining",
    }
    probe_info = args.model / "probe_metadata.json"
    if probe_info.exists():
        results["protocol"]["probe_steps"] = json.loads(probe_info.read_text())["steps"]
    elif args.reuse_probe:
        results["protocol"]["probe_steps"] = "unknown: reused probe without metadata"
    training_file = args.model / "training.json"
    if training_file.exists():
        results["protocol"]["training_seed"] = json.loads(training_file.read_text())["settings"]["seed"]
    (args.model / "metrics.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Saved {args.model / 'metrics.json'}")


if __name__ == "__main__":
    main()
