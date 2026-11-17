# Train ORBIT from scratch / Обучить ORBIT с нуля

**ORBIT includes the complete temporal JEPA training code and independent full reruns. No pretrained weights are required.** **Since v0.6, the browser runs `temporal-44`, the best of the three published temporal trainings on the selection benchmark.** [Current model](BENCHMARK.md). New training commands create separate bundles and do not deploy automatically.

**По-русски:** восстановлен исходный рецепт обучения энкодера: модель по двум изображениям учится предсказывать признаки будущего кадра. Затем обучаются отдельный координатный probe для рисунка и предиктор действий. Всё начинается со случайных весов. Нужны только Python, PyTorch, NumPy и Node.js; данные генерируются локально.

[Executed training notebook](materials/ORBIT_From_Scratch.ipynb) · [Recovered code](ml/original-training/INTEGRATION.md) · [Model card](MODEL_CARD.md) · [Original numeric checkpoints](artifacts/original-training/)

## Run the complete pipeline

From the repository root, with Python 3.12 and Node.js 24:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
# Windows: .venv\Scripts\activate
python -m pip install -r requirements-training.txt
python -m planning.original_training --seed 44 --action-seed 31005 --out runs/temporal-44
```

The tested local stack is Python 3.12.14, PyTorch 2.5.1, NumPy 2.1.3, macOS arm64 / Apple M2, two PyTorch CPU threads. Linux CI uses Python 3.12 and PyTorch 2.5.1 CPU. For Linux, the CPU-only install is:

```sh
python -m pip install -r requirements.txt
python -m pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu
```

The supplied historical reproduction used Python 3.13.5, PyTorch 2.10.0+cpu and NumPy 2.3.5 on Linux. Its pinned dependencies are preserved in `ml/original-training/requirements-original.txt`; that report is separate from our local measurements.

The output directory must be new. The runner verifies the 17 recovered source hashes, copies only source and reports into an empty workspace, checks that no `.npz` or `.pt` weights are present, then runs the original numerical code unchanged. It trains, evaluates, exports the browser binary and runs the original 26 tests. `--ablation` additionally trains a visual model without variance/covariance regularization. Resume checkpoints exist during training but are not loaded from the supplied package.

The resulting directory contains:

- `encoder.npz`, `predictor.npz`, `probe.npz`, `model.bin`, `manifest.json`: a complete compatible model bundle. The exported encoder is the **EMA teacher**.
- `pretrained/model.npz`: the full visual training result, including student, teacher and temporal predictor; configuration, loss history and visual metrics sit beside it.
- `action_jepa/`: action-predictor history, selected checkpoint and the original 1,024-scene evaluation.
- `logs/` and `training.json`: commands, source hashes, actual environment, elapsed times, weight comparisons and results.

To repeat the three published independent training runs:

```sh
python -m planning.original_training --seed 42 --action-seed 31001 --out runs/temporal-42
python -m planning.original_training --seed 43 --action-seed 31003 --out runs/temporal-43
python -m planning.original_training --seed 44 --action-seed 31005 --out runs/temporal-44
python -m planning.benchmark --no-released --model-dirs runs/temporal-42 runs/temporal-43 runs/temporal-44 --out reports/my-temporal.json
```

Load all components together: `load_model(model_dir="runs/temporal-44")`. Mixing a new encoder with an old predictor is invalid. Pass complete bundles via `--model-dirs`.

## What is trained

| Stage | Inputs and target | Recipe |
|---|---|---|
| Visual temporal JEPA | Images at t=0 and t=1 plus horizon h=1…4 → EMA features of image at t=1+h | Random student 576→128→64→8; temporal predictor 28→128→128→8; 2,400 steps, batch 128; AdamW 0.001, weight decay 0.0001; gradient clip 5; final checkpoint |
| Display probe | Frozen teacher features of observed images → simulator coordinates | 8→64→64→2 + sigmoid; 8,192 examples; 800 steps, batch 256; Adam 0.003; data/init/batch seeds 10001/9001/10002 |
| Action predictor | Two frozen teacher embeddings + three actions → three future embeddings | 27→128→128→24; 65,536 training and 2,048 validation trajectories; 5,000 steps, batch 256; AdamW 0.001 with cosine decay to 0.0001; clip 5; best validation checkpoint |

Visual examples are generated online: position in [0.08, 0.92]², signed speed per axis 0.025–0.065, reflections at 0.08 and 0.92. Images are 24×24 Gaussian spots with sigma 0.042, trajectory brightness 0.7–1.0 and independent additive pixel noise 0–0.03. The visual run processes 307,200 trajectory examples.

The visual objective is **10 × prediction MSE + 10 × variance penalty + covariance penalty**. Prediction targets are stop-gradient EMA-teacher outputs. EMA is 0.99. Regularization uses the concatenated student embeddings of both context frames and the future frame (3×batch). The variance penalty uses population variance with epsilon 0.0001 and target standard deviation 1; covariance uses N−1 and divides the off-diagonal squared sum by 8. No BatchNorm, L2 output normalization or coordinate loss is used.

Action data uses the game's three horizontal pushes, two ticks per push, impulse 0.035 and speed cap 0.14. Normalization statistics are estimated from all five training-frame embeddings with sample standard deviation and floor 0.01. Validation seed is action seed + 1. Validation is checked at step 1 and every 250 steps. Test scenes are never used for checkpoint selection.

The separately supervised probe only draws predictions. The planner ranks 27 action sequences by predicted feature distance to the goal image; it does not use probe coordinates, simulator states or oracle costs. This is an educational JEPA-inspired implementation, not Meta I-JEPA or V-JEPA.

## Independently measured results

<!-- measured:start -->
| Model | Normal hits, 95% CI | More image noise | Weaker push | Stronger push |
|---|---:|---:|---:|---:|
| temporal-42 | 68.65% [66.99, 70.27] | 27.67% | 64.84% | 35.55% |
| temporal-43 | 67.51% [65.84, 69.15] | 28.06% | 64.65% | 37.40% |
| temporal-44 (current game) | 74.45% [72.87, 75.96] | 32.29% | 65.89% | 37.47% |
| VICReg 51001 | 43.78% [42.04, 45.54] | 34.05% | 57.42% | 32.03% |
| VICReg 51003 | 46.58% [44.82, 48.35] | 34.47% | 59.54% | 32.65% |
| VICReg 51005 | 45.54% [43.79, 47.31] | 34.47% | 58.92% | 31.48% |

Random control: **18.78%** normal-condition hits; exact-physics oracle: **100%**.

[Temporal report](reports/temporal.json) · [VICReg and released-model report](reports/from-scratch.json) · [All checkpoints and logs](experiments/)
<!-- measured:end -->

The evaluation uses the shared [evaluation protocol](BENCHMARK.md): 1,024 scenes for each of seeds 99017, 99018 and 99019, 3,072 scenes per condition, hit radius 0.06. Intervals are 95% Wilson intervals across scenes, not confidence intervals across training seeds. The oracle knows the physics and goals are reachable by construction. Noise and impulse changes are the same for every model.

The earlier VICReg experiment is preserved in `planning/from_scratch.py`, `configs/train-from-scratch.json` and `experiments/scratch-*`. It aligns two noisy views of one state, without EMA or a temporal pretraining target. Repeat it with:

```sh
python -m planning.from_scratch --config configs/train-from-scratch.json --seed 51001 --out runs/vicreg-51001
```

**These are comparisons between complete training recipes, not a controlled ablation of the encoder loss.** Data generators, optimizer schedules, normalization, step counts and seeds also differ. The observed quality gap does not establish which individual choice caused it.

## Reproducibility evidence and limits

- All supplied EMA teacher, probe and action-predictor tensors match the published browser tensors exactly. Source hashes establish which recovered code was run; they do not independently establish the history of files before recovery.
- The supplied [Linux report](ml/original-training/reference/reproduction_verified/validation.json) records byte-identical numeric reference checkpoints. It is clearly retained as supplied evidence.
- Our independent macOS run does **not** match those historical bytes. It produces 0.7766-pixel visual prediction error and 68.36% hits on the original 1,024-scene test; the historical report has 0.8233 pixels and 67.77%. These are different from the larger 3,072-scene test above.
- [Local repeat proof](reports/temporal-repeat.json) compares an unchanged-script run, the integrated runner and the fully executed notebook. Same-seed full retraining repeats locally; no cross-platform byte identity is promised. The separate [VICReg repeat proof](reports/vicreg-repeat.json) verifies its four exported artifacts after training without historical weights.
- The no-regularization control is also trained from scratch. On this Mac its visual error is 6.0782 pixels, versus 0.7766 with regularization. Its small latent loss is not evidence of good predictions; collapsed representations can yield misleadingly small latent losses.
- Local hardware is read from the current machine, not inferred for the original training. The historical CPU model, original memory use and early hyperparameter search remain unknown. Stage timings include process startup/imports, and are not a hardware-performance benchmark. No peak-memory measurement is claimed for these new temporal runs.

## Notebook and checks

```sh
python -m pip install -r requirements-notebook.txt
python scripts/execute_notebook.py --notebook materials/ORBIT_From_Scratch.ipynb
python -m unittest discover -s tests -v
node --test scripts/test_*.cjs
```

The notebook trains all components, loads the new bundle and actually evaluates 256 fresh scenes. CI runs the full recipe, including all original tests. `ORBIT_NOTEBOOK_SMOKE=1` optionally reduces training and is explicitly labelled an execution check. The published notebook contains a full local run. The current game uses `temporal-44`; retraining never automatically deploys a model. Historical and current leaderboard results are kept separately.
