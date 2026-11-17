# Current game model / Модель в игре

**ORBIT v0.7 runs the fully retrained temporal JEPA model `temporal-44`.**

**По-русски:** в игре установлена новая модель, целиком обученная с нуля. Она показала лучший результат из трёх полных обучений на опубликованном тесте: **74,45% попаданий** против 69,53% у прежней модели.

## Measured performance / Измеренное качество

| Method | Hits | 95% Wilson interval | Mean distance, px |
|---|---:|---:|---:|
| Current JEPA | 74.45% | 72.87–75.96% | 0.838 |
| Random | 18.78% | 17.44–20.20% | 4.357 |
| No push | 22.62% | 21.18–24.14% | 3.485 |
| Shuffled actions | 20.28% | 18.90–21.74% | 4.271 |
| Exact-physics oracle | 100.00% | 99.88–100.00% | 0.185 |

| Condition | Hits |
|---|---:|
| normal | 74.45% |
| noisy | 32.29% |
| weak_push | 65.89% |
| strong_push | 37.47% |

Each condition has 3,072 scenes: 1,024 for each evaluation seed 99017, 99018 and 99019. A hit means distance ≤0.06 (1.38 pixels). The exact-physics oracle is privileged and the targets are reachable by construction.

**Selection matters:** this model was selected after comparing the three runs on this benchmark. The 74.45% is its measured score on that selection set, not an independent post-selection estimate. Scene-level intervals do not account for model selection or training-seed variation. No guarantee about any particular daily challenge follows.

## Reproduce / Повторить

```sh
# Uses the exact complete bundle deployed in the browser
python -m planning.benchmark --no-released --model-dirs experiments/temporal-44 --out reports/current-model.json
# Retrain the same recipe from random initialization (platform differences can change weights)
python -m planning.original_training --seed 44 --action-seed 31005 --out runs/temporal-44
```

[Full training guide](FROM_SCRATCH.md) · [Executed inference notebook](materials/ORBIT_Action_Planning.ipynb) · [Raw benchmark](reports/temporal.json) · [Checkpoint and logs](experiments/temporal-44/) · [Model architecture](MODEL_CARD.md) · [Verified full retraining](reports/current-model-retraining.json)

The single deployment record is `source/model-release.json`. The site builder, replay validator, failure gallery and promotion replay all read it. The builder verifies the binary hash and the NPZ hashes against the measured report. Deployment never rewrites experiment checkpoints.

## Existing results / Прежние результаты

Daily scenes and scoring rules are unchanged. Public replays for the previous and current model remain accepted under the existing 30-day window, with one best score per account/day/model. The page shows the current model’s league. Local scores remain stored under their original model key; no existing score is deleted. Old shared links display a model-change notice.

**По-русски:** старые результаты сохранены отдельно; на странице показаны игры с новой JEPA. Старые ссылки предупреждают о смене соперника. Галерея ошибок и иллюстрированный повтор пересчитаны для новой модели.
