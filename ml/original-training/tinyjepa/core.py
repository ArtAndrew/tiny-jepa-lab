"""JEPA-inspired learning on pixels, with an EMA teacher and VICReg-style penalties.

No coordinates, velocities, physics function or labels enter the neural network.
This is NOT an implementation of Meta's full I-JEPA / V-JEPA architecture.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from copy import deepcopy
from pathlib import Path
import json
import math
import numpy as np
import torch
from torch import Tensor, nn
from torch.nn import functional as F


@dataclass(frozen=True)
class Config:
    size: int = 24
    dim: int = 8
    max_horizon: int = 4
    margin: float = 0.08
    sigma: float = 0.042
    noise: float = 0.03
    min_speed: float = 0.025
    max_speed: float = 0.065
    ema: float = 0.99

    def validate(self) -> None:
        if self.size < 8 or self.dim < 2 or self.max_horizon < 1:
            raise ValueError("size >= 8, dim >= 2 and max_horizon >= 1 are required")
        if not 0 < self.margin < 0.5 or not 0 < self.sigma < 0.5:
            raise ValueError("Invalid margin or sigma")
        if not 0 <= self.noise <= 1 or not 0 <= self.min_speed <= self.max_speed:
            raise ValueError("Invalid noise or speed")
        if not 0 <= self.ema < 1:
            raise ValueError("ema must be in [0, 1)")


@dataclass
class Batch:
    context: Tensor       # [B, 2, H, W]: the ONLY observations given to the predictor
    future: Tensor        # [B, H, W]: teacher target, never predictor input
    horizon: Tensor       # [B], integer 1..max_horizon
    positions: Tensor     # [B, 3, 2]: t=0, t=1, t=1+h; EVALUATION ONLY


def reflect(x: Tensor, margin: float) -> Tensor:
    """Simulator / explicit physics baseline. Never called inside the neural model."""
    width = 1 - 2 * margin
    return margin + width - torch.abs(torch.remainder(x - margin, 2 * width) - width)


class World:
    """Independent synthetic trajectories from an explicit CPU random generator."""
    def __init__(self, config: Config, seed: int = 42):
        config.validate()
        self.cfg = config
        self.rng = torch.Generator(device="cpu").manual_seed(seed)
        axis = torch.linspace(0, 1, config.size)
        yy, xx = torch.meshgrid(axis, axis, indexing="ij")
        self.grid = torch.stack((xx, yy), dim=-1)

    @torch.no_grad()
    def sample(self, n: int, noise: float | None = None,
               speed_multiplier: float = 1.0) -> Batch:
        if n < 1 or speed_multiplier <= 0:
            raise ValueError("n and speed_multiplier must be positive")
        cfg, g = self.cfg, self.rng
        level = cfg.noise if noise is None else noise
        if not 0 <= level <= 1:
            raise ValueError("noise must be between zero and one")
        p = cfg.margin + (1 - 2 * cfg.margin) * torch.rand(n, 2, generator=g)
        v = (cfg.min_speed + (cfg.max_speed - cfg.min_speed) *
             torch.rand(n, 2, generator=g)) * speed_multiplier
        v *= torch.where(torch.rand(n, 2, generator=g) > 0.5, 1.0, -1.0)
        h = torch.randint(1, cfg.max_horizon + 1, (n,), generator=g)
        times = torch.stack((torch.zeros(n), torch.ones(n), 1 + h), dim=1)
        xy = reflect(p[:, None] + v[:, None] * times[:, :, None], cfg.margin)
        distance2 = ((self.grid[None, None] - xy[:, :, None, None]) ** 2).sum(-1)
        amplitude = 0.7 + 0.3 * torch.rand(n, 1, 1, 1, generator=g)
        frames = amplitude * torch.exp(-distance2 / (2 * cfg.sigma ** 2))
        frames += level * torch.rand(n, 3, cfg.size, cfg.size, generator=g)
        frames.clamp_(0, 1)
        return Batch(frames[:, :2], frames[:, 2], h, xy)


class Encoder(nn.Module):
    """Small spatial MLP; flattening preserves the location of each pixel."""
    def __init__(self, cfg: Config):
        super().__init__()
        self.net = nn.Sequential(
            nn.Flatten(), nn.Linear(cfg.size ** 2, 128), nn.ReLU(),
            nn.Linear(128, 64), nn.ReLU(), nn.Linear(64, cfg.dim),
        )

    def forward(self, images: Tensor) -> Tensor:
        return self.net(images)


class TinyJEPA(nn.Module):
    def __init__(self, cfg: Config = Config()):
        super().__init__()
        cfg.validate()
        self.cfg = cfg
        self.encoder = Encoder(cfg)
        self.teacher = deepcopy(self.encoder).requires_grad_(False)
        self.predictor = nn.Sequential(
            nn.Linear(3 * cfg.dim + cfg.max_horizon, 128), nn.ReLU(),
            nn.Linear(128, 128), nn.ReLU(), nn.Linear(128, cfg.dim),
        )

    def forward(self, context: Tensor, horizon: Tensor) -> tuple[Tensor, Tensor]:
        if context.ndim != 4 or tuple(context.shape[1:]) != (2, self.cfg.size, self.cfg.size):
            raise ValueError(f"context must be [B, 2, {self.cfg.size}, {self.cfg.size}]")
        if horizon.dtype not in (torch.int32, torch.int64):
            raise ValueError("horizon must be an integer tensor")
        if horizon.shape != (context.shape[0],):
            raise ValueError("horizon must have shape [B]")
        if torch.any(horizon < 1) or torch.any(horizon > self.cfg.max_horizon):
            raise ValueError("horizon is outside the trained range")
        z = self.encoder(context.reshape(-1, self.cfg.size, self.cfg.size))
        z = z.reshape(-1, 2, self.cfg.dim)
        onehot = F.one_hot(horizon.long() - 1, self.cfg.max_horizon).to(z.dtype)
        # A residual inductive bias, NOT a hardcoded motion law:
        # all motion-dependent changes must be learned by this MLP.
        features = torch.cat((z[:, 0], z[:, 1], z[:, 1] - z[:, 0], onehot), dim=-1)
        prediction = z[:, 1] + self.predictor(features)
        return prediction, z

    @torch.no_grad()
    def update_teacher(self) -> None:
        for target, online in zip(self.teacher.parameters(), self.encoder.parameters()):
            target.lerp_(online, 1.0 - self.cfg.ema)

    def inference_parameter_count(self) -> int:
        return sum(p.numel() for p in self.encoder.parameters()) + sum(
            p.numel() for p in self.predictor.parameters())


def variance_covariance(z: Tensor) -> tuple[Tensor, Tensor]:
    """VICReg-inspired regularization; full collapse remains an empirical diagnostic.

    The variance term discourages constant features; off-diagonal covariance
    discourages redundant feature dimensions. These are educational design
    choices, not an exact copy of the official V-JEPA training objective.
    """
    if z.ndim != 2 or z.shape[0] < 2:
        raise ValueError("At least two examples are required")
    centered = z - z.mean(dim=0)
    std = (centered.var(dim=0, unbiased=False) + 1e-4).sqrt()
    variance = F.relu(1.0 - std).mean()
    cov = centered.T @ centered / (z.shape[0] - 1)
    off = cov - torch.diag_embed(cov.diagonal())
    covariance = off.square().sum() / z.shape[1]
    return variance, covariance


def jepa_loss(model: TinyJEPA, context: Tensor, future: Tensor, horizon: Tensor,
              prediction_weight: float = 10.0, variance_weight: float = 10.0,
              covariance_weight: float = 1.0) -> tuple[Tensor, dict[str, float]]:
    """No coordinate / velocity arguments: the entire training objective uses pixels."""
    prediction, z = model(context, horizon)
    with torch.no_grad():
        target = model.teacher(future)
    # Future pixels also participate in anti-collapse statistics, never as context.
    online_future = model.encoder(future)
    var, cov = variance_covariance(torch.cat((z[:, 0], z[:, 1], online_future), dim=0))
    pred = F.mse_loss(prediction, target)
    total = prediction_weight * pred + variance_weight * var + covariance_weight * cov
    stats = {"loss": float(total.detach()), "prediction_mse": float(pred.detach()),
             "variance_penalty": float(var.detach()), "covariance_penalty": float(cov.detach())}
    return total, stats


def save_model(model: TinyJEPA, directory: str | Path) -> None:
    """Portable numeric weights, no pickle and no network downloads."""
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path / "model.npz", **{
        key: value.detach().cpu().numpy() for key, value in model.state_dict().items()})
    (path / "config.json").write_text(json.dumps(asdict(model.cfg), indent=2), encoding="utf-8")


def load_model(directory: str | Path, device: str | torch.device = "cpu") -> TinyJEPA:
    path = Path(directory)
    if not (path / "model.npz").is_file():
        raise FileNotFoundError(f"No weights in {path}. Run python train.py --out {path}")
    config = Config(**json.loads((path / "config.json").read_text(encoding="utf-8")))
    model = TinyJEPA(config)
    with np.load(path / "model.npz", allow_pickle=False) as data:
        state = {name: torch.from_numpy(data[name].copy()) for name in data.files}
    model.load_state_dict(state, strict=True)
    return model.to(device).eval()


def select_device(name: str) -> torch.device:
    if name == "auto":
        # CPU is deliberately the default reference. CUDA/MPS are optional paths.
        name = "cuda" if torch.cuda.is_available() else (
            "mps" if hasattr(torch.backends, "mps") and torch.backends.mps.is_available() else "cpu")
    if name == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; use --device cpu")
    if name == "mps" and not torch.backends.mps.is_available():
        raise RuntimeError("MPS is unavailable; use --device cpu")
    return torch.device(name)
