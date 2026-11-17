"""Publish the deployed model's measured results and selection provenance."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
release = json.loads((root/'source/model-release.json').read_text())
report = json.loads((root/release['benchmark']).read_text())
entry = report['models'][release['benchmarkModel']]
normal = entry['conditions']['normal']['aggregate']
lines = ['# Current game model / Модель в игре', '',
         '**ORBIT v0.6 now runs the fully retrained temporal JEPA model `temporal-44`.**', '',
         '**По-русски:** в игре установлена новая модель, целиком обученная с нуля. Она показала лучший результат из трёх полных обучений на опубликованном тесте: **74,45% попаданий** против 69,53% у прежней модели.', '',
         '## Measured performance / Измеренное качество', '',
         '| Method | Hits | 95% Wilson interval | Mean distance, px |',
         '|---|---:|---:|---:|']
for name, label in [('model','Current JEPA'),('random','Random'),('no_push','No push'),
                    ('shuffled_actions','Shuffled actions'),('oracle','Exact-physics oracle')]:
    row=normal[name];lo,hi=row['hit_ci95_wilson']
    lines.append(f'| {label} | {100*row["hit_rate"]:.2f}% | {100*lo:.2f}–{100*hi:.2f}% | {row["mean_distance_px"]:.3f} |')
lines += ['', '| Condition | Hits |', '|---|---:|']
for condition, result in entry['conditions'].items():
    lines.append(f'| {condition} | {100*result["aggregate"]["model"]["hit_rate"]:.2f}% |')
lines += ['', 'Each condition has 3,072 scenes: 1,024 for each evaluation seed 99017, 99018 and 99019. A hit means distance ≤0.06 (1.38 pixels). The exact-physics oracle is privileged and the targets are reachable by construction.', '',
          '**Selection matters:** this model was selected after comparing the three runs on this benchmark. The 74.45% is its measured score on that selection set, not an independent post-selection estimate. Scene-level intervals do not account for model selection or training-seed variation. No guarantee about any particular daily challenge follows.', '',
          '## Reproduce / Повторить', '', '```sh',
          '# Uses the exact complete bundle deployed in the browser',
          'python -m planning.benchmark --no-released --model-dirs experiments/temporal-44 --out reports/current-model.json',
          '# Retrain the same recipe from random initialization (platform differences can change weights)',
          'python -m planning.original_training --seed 44 --action-seed 31005 --out runs/temporal-44',
          '```', '',
          '[Full training guide](FROM_SCRATCH.md) · [Executed inference notebook](materials/ORBIT_Action_Planning.ipynb) · [Raw benchmark](reports/temporal.json) · [Checkpoint and logs](experiments/temporal-44/) · [Model architecture](MODEL_CARD.md) · [Verified full retraining](reports/current-model-retraining.json)', '',
          'The single deployment record is `source/model-release.json`. The site builder, replay validator, failure gallery and promotion replay all read it. The builder verifies the binary hash and the NPZ hashes against the measured report. Deployment never rewrites experiment checkpoints.', '',
          '## Existing results / Прежние результаты', '',
          'Daily scenes and scoring rules are unchanged. Public replays for the previous and current model remain accepted under the existing 30-day window, with one best score per account/day/model. The page shows the current model’s league. Local scores remain stored under their original model key; no existing score is deleted. Old shared links display a model-change notice.', '',
          '**По-русски:** старые результаты сохранены отдельно; на странице показаны игры с новой JEPA. Старые ссылки предупреждают о смене соперника. Галерея ошибок и иллюстрированный повтор пересчитаны для новой модели.', '']
(root/'BENCHMARK.md').write_text('\n'.join(lines))
