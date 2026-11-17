# ORBIT: Original Tiny JEPA Training (reconstructed from source archives)

An educational *temporal-prediction* JEPA-like visual encoder, an EMA target encoder, a post-hoc coordinate probe, and an action-conditioned predictor. **Not** Meta's I-JEPA/V-JEPA. Full original Python sources, synthetic generators, validation, source checksums and logs are included. Pretrained `.npz` weights are available as a separate download; this package **trains from random initialization**.

## From scratch

Use Python 3.13.5, `torch==2.10.0` (CPU), `numpy==2.3.5`, Node.js 22.x. The original training was done on Linux with two PyTorch threads. On a clean unpacked folder:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-original.txt
bash scripts/reproduce_all.sh
```

To add an anti-collapse ablation on the **first** execution:

```bash
WITH_ABLATION=1 bash scripts/reproduce_all.sh
```

Read [README_REPRODUCTION_RU.md](README_REPRODUCTION_RU.md) for exact loss, data distribution, schedules, seeds, validation protocol and notes about incomplete hardware provenance. Saved original reports and freshly verified logs are under `reference/`.

The visual encoder was **not trained using two noisy views of the same state**: it was optimized to predict the EMA teacher embedding of a *future* frame from two prior frames plus a prediction horizon. The action model was trained afterward against frozen EMA teacher embeddings.
