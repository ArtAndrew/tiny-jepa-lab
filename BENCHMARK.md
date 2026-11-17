# ORBIT v0.4 — reproducible benchmark / Воспроизводимый бенчмарк

**New measurements of the original model and three newly trained predictors.** The browser model is unchanged. This does not claim to reproduce the historical 67.8% exactly.

**По-русски:** ниже — новая проверка опубликованной модели и трёх заново обученных предикторов. Прежние 67,8% относятся к другому набору сцен. Модель в игре не заменена.

## Protocol / Условия

- 1,024 scenes per evaluation seed; seeds 99017, 99018, 99019; **3,072 scenes per condition and model**.
- Deterministic namespace: `orbit-v04-eval|{evaluation_seed}|{scene_index}`; exact RNG and renderer match JavaScript.
- 27 plans, three horizontal impulses, two ticks per impulse. The planner receives only two images and a clean goal image.
- A hit means final distance ≤ 0.06 normalized units (1.38 pixels at scale 23). Smaller distance is better.
- Goals are constructed from reachable plans in the tested simulator. The privileged oracle knows the true state and physics; its 100% is an expected reference, not a universal claim.
- Random actions and action permutations use a separate deterministic stream. All models see the same evaluation scenes.
- Hit intervals: 95% Wilson. Distance intervals in JSON: normal approximation. These describe scene sampling, not uncertainty from retraining.
- Held-out evaluation seeds/namespace are separate from training and validation. No benchmark scene is used to select a checkpoint.

## Released browser model: normal world / Модель в игре

| Method | Hits | 95% interval | Mean distance, px |
|---|---:|---:|---:|
| JEPA-inspired planner | 69.53% | 67.88–71.13% | 0.942 |
| Random plan | 18.78% | 17.44–20.20% | 4.357 |
| No impulses | 22.62% | 21.18–24.14% | 3.485 |
| Shuffled action association | 19.24% | 17.88–20.67% | 4.324 |
| Privileged physics oracle | 100.00% | 99.88–100.00% | 0.185 |

## Observation and dynamics shifts / Изменённые условия

Each condition generates reachable goals using its own physics; predictor weights stay fixed. Noise affects observations, not physics. Impulse shifts affect physics and goals, not the model.

| Condition | Input noise | Impulse | Hits | 95% interval |
|---|---:|---:|---:|---:|
| normal | 0.030 | 0.0350 | 69.53% | 67.88–71.13% |
| noisy | 0.150 | 0.0350 | 27.54% | 25.99–29.15% |
| weak_push | 0.030 | 0.0175 | 64.06% | 62.35–65.74% |
| strong_push | 0.030 | 0.0525 | 36.17% | 34.48–37.88% |

## Three independent predictor trainings / Три обучения предиктора

All runs reuse the same frozen encoder and validation seed. Training data, initialization and minibatch streams vary with the training seed. These are not three independent encoder pretrainings.

| Predictor | Normal | Noisy | Weak push | Strong push | Selected step | Time, s | Peak RSS, MiB |
|---|---:|---:|---:|---:|---:|---:|---:|
| seed-31001 | 71.94% | 26.60% | 65.07% | 35.87% | 5000 | 8.21 | 345.2 |
| seed-31003 | 72.56% | 27.25% | 64.23% | 36.69% | 5000 | 8.25 | 313.3 |
| seed-31005 | 71.91% | 26.76% | 63.77% | 36.72% | 4750 | 8.09 | 346.0 |

Normal-condition mean across three training seeds: **72.14%**, sample standard deviation **0.37 percentage points**. Three runs are a small sample; this is not a confidence interval or a claim of significant superiority.

Time includes data encoding, training, validation and checkpoint export, excluding process startup/imports. RSS covers the whole process. Measurements: CPU, two threads, macOS arm64, Python 3.12, NumPy 2.1.3, PyTorch 2.5.1. CPU model was not exposed to the sandbox and is recorded as null.

## Repeat / Повторить

```sh
python -m planning.benchmark --out reports/repeated.json --predictors experiments/seed-31001/predictor.npz experiments/seed-31003/predictor.npz experiments/seed-31005/predictor.npz
```

[Installation and training commands](REPRODUCIBILITY.md) · [Raw report, including per-evaluation-seed results](reports/benchmark.json) · [Training logs/checkpoints](experiments/) · [Model card](MODEL_CARD.md)

## Limits / Ограничения

- This is a small synthetic task with a known goal-construction procedure, not a robotics or LLM benchmark.
- Only the selected noise and impulse shifts are tested. No gravity, moving target or closed-loop MPC is implemented.
- The original encoder pretraining remains unavailable. Full-system training from scratch is not reproduced.
- Historical report metrics and the deliberately selected failure gallery are separate from this fresh benchmark.
- Floating-point/library differences may change extremely close plan rankings on another platform. Cross-language parity is tested with explicit numerical tolerances.
