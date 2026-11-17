# Reproduce ORBIT / Как повторить эксперимент

**v0.5 now includes the recovered full training recipe:** visual encoder + EMA teacher + temporal predictor, display probe and action predictor, all from random initialization. Start with [FROM_SCRATCH.md](FROM_SCRATCH.md) or the [training notebook](materials/ORBIT_From_Scratch.ipynb). The sections below also preserve the v0.4 inference, benchmark and predictor-only recipe.

**По-русски:** исходный код предобучения восстановлен и проверен. Теперь можно обучить всю цепочку без готовых весов. [Полная инструкция и измерения](FROM_SCRATCH.md). В игре используется исходная модель; новые модели доступны как отдельные эксперименты.

## 1. Install

Use Python **3.12** and Node.js **24**. From a fresh clone:

```sh
git clone https://github.com/ArtAndrew/tiny-jepa-lab.git
cd tiny-jepa-lab
python3.12 -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
python -m pip install -r requirements-notebook.txt
```

NumPy is the only dependency for inference and benchmarks (`requirements.txt`). PyTorch is needed only for training. The notebook dependencies provide a kernel and headless execution; use your existing Jupyter/VS Code interface to edit cells interactively.

## 2. Run the notebook and checks

```sh
python scripts/execute_notebook.py
python -m unittest discover -s tests -v
node --test scripts/test_*.cjs
```

[Open the executed notebook](materials/ORBIT_Action_Planning.ipynb). All seven code cells are run by the execution command; failures stop the command. It loads the weights, chooses a plan from images, executes it in the simulator, illustrates an error and **actually evaluates 256 fresh scenes**. Its final cell separately reads the larger published report.

The tests compare Python and JavaScript observations, feature vectors, all 27 plan predictions, decoded coordinates and simulation outcomes. Training tests are skipped when PyTorch is absent. Set `NODE=/absolute/path/to/node` if Node is outside `PATH`.

The original notebook is preserved in [materials/archive](materials/archive/ORBIT_Action_Planning_v03.ipynb), with its original missing-dependency limitation.

## 3. Repeat the published-model benchmark

```sh
OPENBLAS_NUM_THREADS=1 python -m planning.benchmark --out reports/my-benchmark.json
```

On Windows, set the environment variable separately or omit it. Defaults: evaluation seeds `99017 99018 99019`, 1,024 scenes per seed, four conditions. The command uses the original model and evaluates 12,288 scene/condition pairs. See [the protocol and results](BENCHMARK.md). Output paths may be changed without changing the protocol.

For a quick check:

```sh
python -m planning.benchmark --per-seed 32 --conditions normal --out reports/quick.json
```

This smaller run is not comparable to the published sample size. Three **evaluation seeds** are not three independent **training seeds**.

## 4. Train an action predictor

```sh
python -m pip install -r requirements-training.txt
python -m planning.training --config configs/train-actions.json --seed 31001 --out runs/my-seed-31001
python -m planning.training --config configs/train-actions.json --seed 31003 --out runs/my-seed-31003
python -m planning.training --config configs/train-actions.json --seed 31005 --out runs/my-seed-31005
python -m planning.benchmark --predictors runs/my-seed-31001/predictor.npz runs/my-seed-31003/predictor.npz runs/my-seed-31005/predictor.npz --out reports/my-comparison.json
```

On Linux without CUDA, the official CPU wheel can be installed with `python -m pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu` after installing `requirements.txt`. All training in this recipe uses CPU explicitly.

Each training output directory must be **new**. It receives `predictor.npz` and `training.json`: complete configuration, validation history, chosen step, hashes, software versions, elapsed time and process peak RSS. The committed [experiments](experiments/) also contain captured console logs for all three full 5,000-step runs.

The frozen encoder maps images to features. A randomly initialized action predictor learns future features from synthetic trajectories. Its loss contains **no coordinate targets, reward or oracle cost**. The coordinate probe is not trained or used to select actions. Validation seed `41002` selects the checkpoint; benchmark scenes are never used for training or checkpoint selection. See [the model card](MODEL_CARD.md) for exact architecture and data generation.

This v0.4 section trains only the predictor. Multiple runs here vary the predictor initialization, training trajectories and minibatches while sharing that same frozen encoder and validation set. They are **not** independent end-to-end JEPA pretrainings.

## 5. Exact weights and data provenance

The three standalone files are [encoder.npz](artifacts/action_jepa/encoder.npz), [predictor.npz](artifacts/action_jepa/predictor.npz) and [probe.npz](artifacts/action_jepa/probe.npz). They were exported without changing any tensor from the supplied HTML. [Provenance and hashes](artifacts/action_jepa/provenance.json) and [tensor shapes](artifacts/action_jepa/manifest.json) are included.

```sh
python scripts/export_weights.py
node scripts/build_failures.cjs
python3 scripts/build_site.py
```

The export regenerates the original weights, not newly trained weights. New predictors stay in their experiment directories and do not replace the browser model or change the leaderboard version.

## Limits of reproducibility

- Identical seeds and pinned dependencies repeat the tested CPU recipe. Bitwise agreement across other operating systems, BLAS libraries or PyTorch versions is not promised; [PyTorch documents this limitation](https://docs.pytorch.org/docs/2.5/notes/randomness.html).
- `experiments/environment-macos.txt` records the complete environment used for the published measurements; it is a platform-specific record, not a universal requirements file.
- Wall-clock time includes dataset encoding, optimization, validation and weight export, but excludes process startup/imports. Peak RSS is the whole process high-water mark, not tensor memory alone; it is recorded as `null` when the platform lacks the standard-library counter (Windows). Hardware model was unavailable to this sandbox and is recorded as `null`; no CPU model is guessed.
- The historical report's 67.8% describes a different scene namespace. Its recovered source and logs now live in `ml/original-training/`. The new multi-seed reports remain explicitly labelled `orbit-v04-eval`.
- Full encoder training is now available in the separate guide. No real-world robotics benchmark, moving target or closed-loop MPC is claimed.
