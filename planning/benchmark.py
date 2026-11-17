"""Run: python -m planning.benchmark --out reports/benchmark.json"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import time
import numpy as np
from .model import ARTIFACTS, HIT, IMPULSE, PLANS, RNG, load_model, rollout, scenario, seed_hash

CONDITIONS = {'normal': (.03, IMPULSE), 'noisy': (.15, IMPULSE),
              'weak_push': (.03, IMPULSE / 2), 'strong_push': (.03, IMPULSE * 1.5)}


def summary(distances):
    values = np.asarray(distances)
    n = len(values)
    rate = float(np.mean(values <= HIT))
    z = 1.959963984540054
    center = (rate + z*z/(2*n)) / (1+z*z/n)
    half = z * np.sqrt(rate*(1-rate)/n+z*z/(4*n*n)) / (1+z*z/n)
    pixels = values * 23
    error = z * float(pixels.std(ddof=1)) / np.sqrt(n) if n > 1 else 0.
    return {'n': n, 'hits': int(np.sum(values <= HIT)), 'hit_rate': rate,
            'hit_ci95_wilson': [float(center-half), float(center+half)],
            'mean_distance_px': float(pixels.mean()),
            'distance_ci95_normal': [float(pixels.mean()-error), float(pixels.mean()+error)]}


def evaluate(model, seeds, per_seed, noise=.03, impulse=IMPULSE):
    combined = {k: [] for k in ['model', 'random', 'no_push', 'shuffled_actions', 'oracle']}
    per_seed_results = []
    for seed in seeds:
        distances = {k: [] for k in combined}
        random = RNG(seed_hash('orbit-v04-baseline|' + str(seed)))
        for start in range(0, per_seed, 64):
            scenes = [scenario(seed_hash(f'orbit-v04-eval|{seed}|{i}'), noise, impulse)
                      for i in range(start, min(start+64, per_seed))]
            best, _, _ = model.rank(np.stack([s['frames'] for s in scenes]), np.stack([s['goal_frame'] for s in scenes]))
            p, v, goal = [np.stack([s[key] for s in scenes]) for key in ['p1', 'v', 'goal']]
            future = rollout(p[:, None, :], v[:, None, :], PLANS, impulse)[..., -1, :]
            errors = np.linalg.norm(future-goal[:, None, :], axis=-1)
            for row, index in enumerate(best):
                # Separate random stream; the same permutations are used for every model/condition.
                choice = int(random()*27)
                permutation = list(range(27))
                for j in range(26, 0, -1):
                    k = int(random()*(j+1)); permutation[j], permutation[k] = permutation[k], permutation[j]
                for name, distance in [('model', errors[row,index]), ('random', errors[row,choice]),
                                       ('no_push', errors[row,13]), ('shuffled_actions', errors[row,permutation[index]]),
                                       ('oracle', errors[row].min())]:
                    distances[name].append(float(distance))
        per_seed_results.append({'seed': seed, 'results': {k: summary(v) for k,v in distances.items()}})
        for k in combined: combined[k].extend(distances[k])
    return {'aggregate': {k: summary(v) for k,v in combined.items()}, 'by_evaluation_seed': per_seed_results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path('reports/benchmark.json'))
    parser.add_argument('--per-seed', type=int, default=1024)
    parser.add_argument('--seeds', type=int, nargs='+', default=[99017, 99018, 99019])
    parser.add_argument('--conditions', nargs='+', choices=CONDITIONS, default=list(CONDITIONS))
    parser.add_argument('--predictors', nargs='*', type=Path, default=[])
    args = parser.parse_args()
    if args.per_seed < 2 or len(set(args.seeds)) != len(args.seeds): parser.error('Use >=2 scenes and distinct seeds')
    report = {'protocol': 'orbit-v04-eval', 'scene_namespace': 'orbit-v04-eval|{evaluation_seed}|{scene_index}',
              'per_seed': args.per_seed, 'seeds': args.seeds, 'hit_radius': HIT,
              'notes': ['New measurement, not a claim to reproduce the historical 67.8% exactly.',
                        'Goals are reachable by construction in each tested world; oracle has exact state and physics.',
                        'Scene-level intervals do not measure variation between independent training runs.',
                        'Changed impulse affects the simulator and reachable goal, never the learned predictor.',
                        'Noise changes input observations only. No gravity or moving targets are tested.'],
              'environment': {'python': platform.python_version(), 'numpy': np.__version__, 'platform': platform.platform()},
              'models': {}}
    for path in [ARTIFACTS/'predictor.npz'] + args.predictors:
        name = 'released_v03' if path == ARTIFACTS/'predictor.npz' else path.parent.name
        if name in report['models']: raise ValueError('Predictor names must be distinct')
        entry = {'predictor_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'conditions': {}}
        model = load_model(path)
        for condition in args.conditions:
            start = time.perf_counter()
            noise, impulse = CONDITIONS[condition]
            result = evaluate(model, args.seeds, args.per_seed, noise, impulse)
            entry['conditions'][condition] = dict(noise=noise, impulse=impulse, **result)
            print(f'{name} {condition}: hit={result["aggregate"]["model"]["hit_rate"]:.4f}, {time.perf_counter()-start:.1f}s', flush=True)
        report['models'][name] = entry
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')


if __name__ == '__main__': main()
