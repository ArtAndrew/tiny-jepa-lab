"""Downstream diagnostics, strictly separated from self-supervised JEPA training.

The small probe is supervised on simulator coordinates AFTER the encoder has
been frozen. It only decodes the embedding of an observed frame; it is NEVER
trained on predicted future embeddings or used in the JEPA training loss.
"""
from __future__ import annotations
import math
import json
from pathlib import Path
import numpy as np
import torch
from torch import Tensor, nn
from torch.nn import functional as F
from .core import World, Config, TinyJEPA, reflect


class CoordinateProbe(nn.Module):
    def __init__(self, dim: int):
        super().__init__()
        self.register_buffer("mean", torch.zeros(dim))
        self.register_buffer("scale", torch.ones(dim))
        self.net = nn.Sequential(nn.Linear(dim, 64), nn.ReLU(),
                                 nn.Linear(64, 64), nn.ReLU(), nn.Linear(64, 2))

    def forward(self, z: Tensor) -> Tensor:
        return torch.sigmoid(self.net((z - self.mean) / self.scale))


@torch.no_grad()
def observed_features(model: TinyJEPA, n: int, seed: int) -> tuple[Tensor, Tensor]:
    world = World(model.cfg, seed)
    zs, ys = [], []
    for offset in range(0, n, 128):
        batch = world.sample(min(128, n - offset))
        zs.append(model.teacher(batch.future))
        ys.append(batch.positions[:, 2])
    return torch.cat(zs), torch.cat(ys)


def fit_probe(model: TinyJEPA, directory: Path, steps: int = 800) -> CoordinateProbe:
    model.eval().requires_grad_(False)
    z, xy = observed_features(model, n=8192, seed=10001)
    torch.manual_seed(9001)
    probe = CoordinateProbe(model.cfg.dim)
    with torch.no_grad():
        probe.mean.copy_(z.mean(0))
        probe.scale.copy_(z.std(0).clamp_min(1e-3))
    opt = torch.optim.Adam(probe.parameters(), lr=0.003)
    rng = torch.Generator().manual_seed(10002)
    probe.train()
    for _ in range(steps):
        ids = torch.randint(len(z), (256,), generator=rng)
        loss = F.mse_loss(probe(z[ids]), xy[ids])
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
    probe.eval().requires_grad_(False)
    directory.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(directory / "probe.npz", **{
        name: value.numpy() for name, value in probe.state_dict().items()})
    (directory / "probe_metadata.json").write_text(json.dumps({
        "examples": 8192, "data_seed": 10001, "initialization_seed": 9001,
        "batch_sampler_seed": 10002, "steps": steps, "batch_size": 256,
        "supervision": "Coordinates of observed frames; encoder frozen; no predicted embeddings."
    }, indent=2), encoding="utf-8")
    # Also report a genuinely linear probe; it need not decode every learned geometry.
    a = torch.cat((z, torch.ones(len(z), 1)), dim=1).double()
    reg = 0.01 * torch.eye(a.shape[1], dtype=torch.float64)
    reg[-1, -1] = 0
    w = torch.linalg.solve(a.T @ a + reg, a.T @ xy.double()).float()
    np.save(directory / "linear_probe.npy", w.numpy(), allow_pickle=False)
    return probe


def load_probe(directory: Path, dim: int) -> CoordinateProbe:
    probe = CoordinateProbe(dim)
    with np.load(directory / "probe.npz", allow_pickle=False) as weights:
        probe.load_state_dict({key: torch.from_numpy(weights[key].copy()) for key in weights.files})
    return probe.eval().requires_grad_(False)


@torch.no_grad()
def centroid(images: Tensor) -> Tensor:
    """A nonlearned pixel-based baseline. No simulator positions are used."""
    n = images.shape[-1]
    mass = (images - 0.20).clamp_min(0)
    total = mass.sum((-1, -2)).clamp_min(1e-8)
    axis = torch.linspace(0, 1, n)
    x = (mass.sum(-2) * axis).sum(-1) / total
    y = (mass.sum(-1) * axis).sum(-1) / total
    return torch.stack((x, y), dim=-1)


def summary(x: Tensor) -> dict[str, float]:
    mean = float(x.mean())
    se = float(x.std(unbiased=True) / math.sqrt(len(x)))
    return {"mean": mean, "ci95_low": mean - 1.96 * se, "ci95_high": mean + 1.96 * se}


@torch.no_grad()
def measure(model: TinyJEPA, probe: CoordinateProbe, n: int = 2048, seed: int = 20001,
            noise: float | None = None, speed_multiplier: float = 1.0) -> tuple[dict, dict]:
    world = World(model.cfg, seed)
    arrays: dict[str, list[Tensor]] = {key: [] for key in [
        "jepa_error", "probe_error", "stationary_error", "physics_error", "latent_mse",
        "persistence_mse", "shuffled_mse", "horizon", "target_z", "prediction_z",
        "xy", "predicted_xy", "retrieval", "persistence_retrieval"]}
    for offset in range(0, n, 64):
        b = world.sample(min(64, n - offset), noise=noise, speed_multiplier=speed_multiplier)
        prediction, _ = model(b.context, b.horizon)
        target = model.teacher(b.future)
        last_z = model.teacher(b.context[:, 1])
        predicted_xy = probe(prediction)
        reference_xy = b.positions[:, 2]
        centers = centroid(b.context)
        baseline_static = centers[:, 1]
        baseline_physics = reflect(centers[:, 1] +
            (centers[:, 1] - centers[:, 0]) * b.horizon[:, None], model.cfg.margin)
        scale = model.cfg.size - 1
        errors = {"jepa_error": ((predicted_xy - reference_xy) * scale).norm(dim=-1),
                  "probe_error": ((probe(target) - reference_xy) * scale).norm(dim=-1),
                  "stationary_error": ((baseline_static - reference_xy) * scale).norm(dim=-1),
                  "physics_error": ((baseline_physics - reference_xy) * scale).norm(dim=-1)}
        distances = (prediction[:, None] - target[None]).square().mean(-1)
        stationary_distances = (last_z[:, None] - target[None]).square().mean(-1)
        extras = {"latent_mse": (prediction - target).square().mean(-1),
                  "persistence_mse": (last_z - target).square().mean(-1),
                  "shuffled_mse": (prediction - target.roll(1, 0)).square().mean(-1),
                  "horizon": b.horizon, "target_z": target, "prediction_z": prediction,
                  "xy": reference_xy, "predicted_xy": predicted_xy,
                  "retrieval": (distances.argmin(1) == torch.arange(len(target))).float(),
                  "persistence_retrieval": (stationary_distances.argmin(1) == torch.arange(len(target))).float()}
        for key, value in {**errors, **extras}.items():
            arrays[key].append(value)
    joined = {key: torch.cat(values) for key, values in arrays.items()}
    report = {key: summary(joined[key]) for key in [
        "jepa_error", "probe_error", "stationary_error", "physics_error", "latent_mse",
        "persistence_mse", "shuffled_mse", "retrieval", "persistence_retrieval"]}
    z = joined["target_z"]
    centered = z - z.mean(0)
    eig = torch.linalg.eigvalsh(centered.T @ centered / (len(z) - 1)).clamp_min(1e-12)
    prob = eig / eig.sum()
    report["representation"] = {
        "mean_std": float(z.std(0).mean()), "min_std": float(z.std(0).min()),
        "effective_rank": float(torch.exp(-(prob * prob.log()).sum())),
        "dimension": model.cfg.dim,
    }
    report["by_horizon"] = {
        str(h): {"n": int((joined["horizon"] == h).sum()),
                 "jepa_error_px": float(joined["jepa_error"][joined["horizon"] == h].mean()),
                 "stationary_error_px": float(joined["stationary_error"][joined["horizon"] == h].mean())}
        for h in range(1, model.cfg.max_horizon + 1)}
    report["n"] = n
    report["seed"] = seed
    report["noise"] = model.cfg.noise if noise is None else noise
    report["speed_multiplier"] = speed_multiplier
    report["retrieval_candidates"] = 64
    report["retrieval_chance"] = 1 / 64
    return report, joined
