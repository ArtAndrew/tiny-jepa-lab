# Run and reproduce ORBIT / Запуск и воспроизведение ORBIT

**Current game: ORBIT v0.6, fully trained model `temporal-44`.** [Benchmark](BENCHMARK.md) · [Architecture](MODEL_CARD.md) · [Full training recipe](FROM_SCRATCH.md).

**По-русски:** ниже — команды для той модели, которая сейчас работает в игре. Она показала 74,45% попаданий на тесте из 3 072 сцен, по которому её выбрали из трёх полных обучений. Можно запустить готовую модель или повторить всю цепочку обучения с нуля.

## 1. Install / Установка

Use Python 3.12 and Node.js 24:

```sh
git clone https://github.com/ArtAndrew/tiny-jepa-lab.git
cd tiny-jepa-lab
python3.12 -m venv .venv
source .venv/bin/activate
# Windows: .venv\Scripts\activate
python -m pip install -r requirements-notebook.txt
```

NumPy is sufficient for inference and benchmarks. PyTorch is needed for training; no external dataset, model service or GPU is required.

## 2. Run the current game model / Запустить модель из игры

```sh
python scripts/execute_notebook.py
```

[The inference notebook](materials/ORBIT_Action_Planning.ipynb) loads the exact deployed model, chooses a plan from images, illustrates a measured failure and evaluates 256 fresh scenes. All seven code cells are executed and any error stops the command.

To load the current model in Python:

```python
from planning.model import load_active_model
model = load_active_model()
```

## 3. Repeat the benchmark / Повторить бенчмарк

```sh
OPENBLAS_NUM_THREADS=1 python -m planning.benchmark --no-released --model-dirs experiments/temporal-44 --out reports/current-model.json
```

The command loads the complete deployed encoder, predictor and probe and evaluates 1,024 scenes for each of seeds 99017, 99018 and 99019 under four conditions. On Windows, set the environment variable separately or omit it. [Measured results and selection limits](BENCHMARK.md).

For a quick execution check:

```sh
python -m planning.benchmark --no-released --model-dirs experiments/temporal-44 --per-seed 32 --conditions normal --out reports/quick.json
```

This smaller check is not comparable to the full sample size.

## 4. Train from scratch / Обучить с нуля

```sh
python -m pip install -r requirements-training.txt
python -m planning.original_training --seed 44 --action-seed 31005 --out runs/my-model
python -m planning.benchmark --no-released --model-dirs runs/my-model --out reports/my-model.json
```

On Linux, a CPU-only PyTorch wheel can be installed with `python -m pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu`. The tested recipe uses CPU explicitly.

Every output directory must be new. The runner starts the visual encoder, EMA teacher, temporal predictor, display probe and action predictor from random initialization. It uses the recovered numerical code in a fresh workspace without pretrained checkpoints and records configuration, environment, logs, hashes and measured results. [Full method and three independent runs](FROM_SCRATCH.md).

The [training notebook](materials/ORBIT_From_Scratch.ipynb) executes this full process:

```sh
python scripts/execute_notebook.py --notebook materials/ORBIT_From_Scratch.ipynb
```

## 5. Verify and build / Проверить и собрать

```sh
python -m unittest discover -s tests -v
node scripts/build_failures.cjs
python scripts/build_research_docs.py
python3 scripts/build_site.py
node --test scripts/test_*.cjs
```

Set `NODE=/absolute/path/to/node` if Node is outside `PATH`. Python/JavaScript parity checks compare observations, embeddings, all 27 plans, decoded coordinates and outcomes. GitHub Actions also executes both notebooks, including full training from scratch.

The deployed bundle is selected by `source/model-release.json`. The builder verifies its binary hash and all NPZ hashes against the measured report. The game, gallery, illustrations and leaderboard use that same selection. Training never deploys automatically.

## Limits / Ограничения

Identical seeds repeat in the tested local environment. Bitwise equality across operating systems, hardware or PyTorch versions is not guaranteed. The deployed model was selected using the displayed benchmark; this is not an independent post-selection evaluation. The experiment concerns a synthetic ball world, not real-world robotics or an LLM comparison.
