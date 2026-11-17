"""Train without labels. Resume uses the same RNG and optimizer state."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import json
import platform
from pathlib import Path
import time
import numpy as np
import torch
from tinyjepa.core import Config, World, TinyJEPA, jepa_loss, save_model, select_device


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("runs/my_jepa"))
    parser.add_argument("--steps", type=int, default=2400, help="Total step count, including resumed steps")
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--device", choices=["cpu", "cuda", "mps", "auto"], default="cpu")
    parser.add_argument("--lr", type=float, default=0.001)
    parser.add_argument("--variance-weight", type=float, default=10.0)
    parser.add_argument("--covariance-weight", type=float, default=1.0)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.steps < 1 or args.batch_size < 8 or args.threads < 1 or args.lr <= 0:
        parser.error("steps/threads/lr must be positive; batch-size must be at least 8")
    if args.variance_weight < 0 or args.covariance_weight < 0:
        parser.error("Regularization weights must be nonnegative")
    torch.set_num_threads(args.threads)
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    device = select_device(args.device)
    cfg = Config()
    world = World(cfg, args.seed)
    model = TinyJEPA(cfg).to(device)
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],
                           lr=args.lr, weight_decay=1e-4)
    start, history = 0, []
    args.out.mkdir(parents=True, exist_ok=True)
    resume_file = args.out / "resume.pt"
    train_settings = {"batch_size": args.batch_size, "seed": args.seed, "lr": args.lr,
                      "variance_weight": args.variance_weight,
                      "covariance_weight": args.covariance_weight}
    if args.resume:
        if not resume_file.exists():
            parser.error(f"Missing resume file: {resume_file}")
        state = torch.load(resume_file, map_location="cpu", weights_only=True)
        if state["settings"] != train_settings:
            parser.error("Keep seed, batch size, learning rate and loss weights unchanged when resuming")
        model.load_state_dict(state["model"])
        opt.load_state_dict(state["optimizer"])
        for optimizer_state in opt.state.values():
            for key, value in optimizer_state.items():
                if isinstance(value, torch.Tensor):
                    optimizer_state[key] = value.to(device)
        world.rng.set_state(state["rng"])
        torch.set_rng_state(state["torch_rng"])
        start, history = state["step"], state["history"]
    elif (args.out / "model.npz").exists():
        parser.error("Output contains a model. Choose a new --out or use --resume")
    if start >= args.steps:
        parser.error(f"Already at step {start}; --steps must be larger")
    model.train()
    start_time = time.perf_counter()
    print(f"Device={device}; inference parameters={model.inference_parameter_count():,}", flush=True)

    def checkpoint(step: int) -> None:
        save_model(model, args.out)
        (args.out / "history.json").write_text(json.dumps(history, indent=2), encoding="utf-8")
        torch.save({"model": model.state_dict(), "optimizer": opt.state_dict(),
                    "rng": world.rng.get_state(), "torch_rng": torch.get_rng_state(),
                    "step": step, "history": history, "settings": train_settings}, resume_file)
        info = {"step": step, "settings": train_settings, "config": asdict(cfg),
                "inference_parameters": model.inference_parameter_count(),
                "python": platform.python_version(), "torch": str(torch.__version__),
                "numpy": str(np.__version__), "device": str(device), "threads": args.threads,
                "note": "Online synthetic training; labels are not used by jepa_loss."}
        (args.out / "training.json").write_text(json.dumps(info, indent=2), encoding="utf-8")

    for step in range(start + 1, args.steps + 1):
        batch = world.sample(args.batch_size)
        loss, stats = jepa_loss(model, batch.context.to(device), batch.future.to(device),
                               batch.horizon.to(device), variance_weight=args.variance_weight,
                               covariance_weight=args.covariance_weight)
        if not torch.isfinite(loss):
            raise RuntimeError(f"Non-finite loss at step {step}")
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
        opt.step()
        model.update_teacher()
        if step == 1 or step % 25 == 0 or step == args.steps:
            history.append({"step": step, **stats})
        if step % 200 == 0 or step == args.steps:
            print(f"step={step:5d} latent_mse={stats['prediction_mse']:.5f} "
                  f"var={stats['variance_penalty']:.4f} cov={stats['covariance_penalty']:.4f} "
                  f"elapsed_this_run={time.perf_counter()-start_time:.1f}s", flush=True)
            checkpoint(step)
    print(f"Saved to {args.out}. Next: python evaluate.py --model {args.out}")


if __name__ == "__main__":
    main()
