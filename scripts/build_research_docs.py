#!/usr/bin/env python3
"""Render the measured benchmark report; never invent or hard-code results."""
from pathlib import Path
import json
import statistics

ROOT=Path(__file__).resolve().parents[1]
report=json.loads((ROOT/'reports/benchmark.json').read_text())
released=report['models']['released_v03']['conditions']
def pct(value):return f'{100*value:.2f}%'
def interval(values):return '–'.join(f'{100*x:.2f}' for x in values)+'%'
lines=['# ORBIT v0.4 — reproducible benchmark / Воспроизводимый бенчмарк','',
       '**New measurements of the original model and three newly trained predictors.** The browser model is unchanged. This does not claim to reproduce the historical 67.8% exactly.','',
       '**По-русски:** ниже — новая проверка опубликованной модели и трёх заново обученных предикторов. Прежние 67,8% относятся к другому набору сцен. Модель в игре не заменена.','',
       '## Protocol / Условия','',
       f'- {report["per_seed"]:,} scenes per evaluation seed; seeds {", ".join(map(str,report["seeds"]))}; **{report["per_seed"]*len(report["seeds"]):,} scenes per condition and model**.',
       '- Deterministic namespace: `orbit-v04-eval|{evaluation_seed}|{scene_index}`; exact RNG and renderer match JavaScript.',
       '- 27 plans, three horizontal impulses, two ticks per impulse. The planner receives only two images and a clean goal image.',
       '- A hit means final distance ≤ 0.06 normalized units (1.38 pixels at scale 23). Smaller distance is better.',
       '- Goals are constructed from reachable plans in the tested simulator. The privileged oracle knows the true state and physics; its 100% is an expected reference, not a universal claim.',
       '- Random actions and action permutations use a separate deterministic stream. All models see the same evaluation scenes.',
       '- Hit intervals: 95% Wilson. Distance intervals in JSON: normal approximation. These describe scene sampling, not uncertainty from retraining.',
       '- Held-out evaluation seeds/namespace are separate from training and validation. No benchmark scene is used to select a checkpoint.','',
       '## Released browser model: normal world / Модель в игре','',
       '| Method | Hits | 95% interval | Mean distance, px |','|---|---:|---:|---:|']
labels={'model':'JEPA-inspired planner','random':'Random plan','no_push':'No impulses','shuffled_actions':'Shuffled action association','oracle':'Privileged physics oracle'}
for name in ['model','random','no_push','shuffled_actions','oracle']:
    r=released['normal']['aggregate'][name]
    lines.append(f'| {labels[name]} | {pct(r["hit_rate"])} | {interval(r["hit_ci95_wilson"])} | {r["mean_distance_px"]:.3f} |')
lines+=['','## Observation and dynamics shifts / Изменённые условия','',
        'Each condition generates reachable goals using its own physics; predictor weights stay fixed. Noise affects observations, not physics. Impulse shifts affect physics and goals, not the model.','',
        '| Condition | Input noise | Impulse | Hits | 95% interval |','|---|---:|---:|---:|---:|']
for name,data in released.items():
    r=data['aggregate']['model'];lines.append(f'| {name} | {data["noise"]:.3f} | {data["impulse"]:.4f} | {pct(r["hit_rate"])} | {interval(r["hit_ci95_wilson"])} |')
lines+=['','## Three independent predictor trainings / Три обучения предиктора','',
        'All runs reuse the same frozen encoder and validation seed. Training data, initialization and minibatch streams vary with the training seed. These are not three independent encoder pretrainings.','',
        '| Predictor | Normal | Noisy | Weak push | Strong push | Selected step | Time, s | Peak RSS, MiB |','|---|---:|---:|---:|---:|---:|---:|---:|']
rates=[]
for name,data in report['models'].items():
    if name=='released_v03':continue
    train=json.loads((ROOT/'experiments'/name/'training.json').read_text())
    values=[pct(data['conditions'][c]['aggregate']['model']['hit_rate']) for c in ['normal','noisy','weak_push','strong_push']]
    rates.append(data['conditions']['normal']['aggregate']['model']['hit_rate'])
    lines.append('| '+name+' | '+' | '.join(values)+f' | {train["selected_step"]} | {train["elapsed_seconds_including_data"]:.2f} | {train["process_peak_rss_mib"]:.1f} |')
lines+=['',f'Normal-condition mean across three training seeds: **{pct(statistics.mean(rates))}**, sample standard deviation **{100*statistics.stdev(rates):.2f} percentage points**. Three runs are a small sample; this is not a confidence interval or a claim of significant superiority.',
        '', 'Time includes data encoding, training, validation and checkpoint export, excluding process startup/imports. RSS covers the whole process. Measurements: CPU, two threads, macOS arm64, Python 3.12, NumPy 2.1.3, PyTorch 2.5.1. CPU model was not exposed to the sandbox and is recorded as null.',
        '', '## Repeat / Повторить','', '```sh',
        'python -m planning.benchmark --out reports/repeated.json --predictors experiments/seed-31001/predictor.npz experiments/seed-31003/predictor.npz experiments/seed-31005/predictor.npz',
        '```','',
        '[Installation and training commands](REPRODUCIBILITY.md) · [Raw report, including per-evaluation-seed results](reports/benchmark.json) · [Training logs/checkpoints](experiments/) · [Model card](MODEL_CARD.md)','',
        '## Limits / Ограничения','',
        '- This is a small synthetic task with a known goal-construction procedure, not a robotics or LLM benchmark.',
        '- Only the selected noise and impulse shifts are tested. No gravity, moving target or closed-loop MPC is implemented.',
        '- The original encoder pretraining remains unavailable. Full-system training from scratch is not reproduced.',
        '- Historical report metrics and the deliberately selected failure gallery are separate from this fresh benchmark.',
        '- Floating-point/library differences may change extremely close plan rankings on another platform. Cross-language parity is tested with explicit numerical tolerances.','']
(ROOT/'BENCHMARK.md').write_text('\n'.join(lines))
print('Rendered BENCHMARK.md from measured JSON')
