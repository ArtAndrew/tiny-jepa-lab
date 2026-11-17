# Original numeric checkpoints

Recovered reference weights, not inputs to from-scratch training. The visual `pretrained/model.npz` contains the student encoder, EMA teacher and temporal predictor. The EMA teacher, probe and action predictor match the published browser tensors exactly.

The supplied checkpoint hash manifest is preserved. Its `resume.pt` entry refers to a historical file intentionally not distributed here; training scripts create a new local resume file when run. Numeric loads use `allow_pickle=False`.

Local retraining results and the distinction between supplied Linux evidence and independently measured macOS results are documented in [FROM_SCRATCH.md](../../FROM_SCRATCH.md).
