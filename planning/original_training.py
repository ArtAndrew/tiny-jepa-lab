"""Run the recovered temporal JEPA recipe without reading pretrained weights.

The historical source stays unchanged in ml/original-training. Each invocation
copies code into an empty temporary directory, trains there and exports a
complete bundle compatible with the current Python/JavaScript planner.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import numpy as np
import torch
from .model import ROOT
from .from_scratch import export_browser_bundle
from .training import environment


SOURCE = ROOT / 'ml/original-training'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_source(source=SOURCE):
    records = json.loads((source/'reference/ORIGINAL_SOURCE_SHA256.json').read_text())
    for name, record in records.items():
        if sha(source/name) != record['sha256']:
            raise ValueError('Recovered source differs from supplied hash: '+name)
    return {name: record['sha256'] for name, record in records.items()}


def export_run(work, out, metadata):
    """Keep numeric checkpoints and logs; never load a supplied pickle checkpoint."""
    for name in ['pretrained', 'action_jepa', 'no_regularization']:
        if not (work/'artifacts'/name).exists():
            continue
        shutil.copytree(work/'artifacts'/name, out/name,
                        ignore=shutil.ignore_patterns('resume.pt', 'test_predictions.npz', 'eval_cases.json'))
    with np.load(out/'pretrained/model.npz', allow_pickle=False) as weights:
        np.savez(out/'encoder.npz', **{k.removeprefix('teacher.'): weights[k]
                 for k in weights.files if k.startswith('teacher.')})
    shutil.copyfile(out/'pretrained/probe.npz', out/'probe.npz')
    shutil.copyfile(out/'action_jepa/predictor.npz', out/'predictor.npz')
    manifest = export_browser_bundle(out)
    expected = json.loads((SOURCE/'reference/CHECKPOINT_SHA256.json').read_text())
    comparisons = {}
    for name in ['pretrained/model.npz', 'pretrained/probe.npz', 'action_jepa/predictor.npz']:
        actual = sha(out/name)
        comparisons[name] = {'sha256': actual, 'reference_sha256': expected['artifacts/'+name],
                             'matches_supplied_reference_bytes': actual == expected['artifacts/'+name]}
    visual = json.loads((out/'pretrained/metrics.json').read_text())
    actions = json.loads((out/'action_jepa/evaluation.json').read_text())
    metadata.update(browser_model_id=manifest['modelId'],
                    historical_weight_comparison=comparisons,
                    visual_position_error_px=visual['in_distribution']['jepa_error']['mean'],
                    historical_scene_hit_rate=actions['model']['hit_rate']['mean'],
                    artifacts_sha256={name: sha(out/name) for name in
                                      ['encoder.npz', 'predictor.npz', 'probe.npz', 'model.bin']})
    (out/'training.json').write_text(json.dumps(metadata, indent=2, allow_nan=False)+'\n')
    return metadata


def train_pipeline(out, seed=42, action_seed=31001, smoke=False, ablation=False):
    hashes = verify_source()
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out/'logs').mkdir()
    torch.set_num_threads(2)
    started = time.perf_counter()
    env = dict(os.environ, OPENBLAS_NUM_THREADS='1')
    env.pop('PYTHONPATH', None)  # The preserved package owns its own planning module.
    if env.get('NODE'):
        env['PATH'] = str(Path(env['NODE']).parent)+os.pathsep+env.get('PATH', '')
    if not shutil.which('node', path=env.get('PATH')):
        raise RuntimeError('Node.js is required; add it to PATH or set NODE.')
    stages = []
    with tempfile.TemporaryDirectory(prefix='orbit-original-') as temp:
        work = Path(temp)/'source'
        shutil.copytree(SOURCE, work, ignore=shutil.ignore_patterns(
            'artifacts', 'logs', 'site', 'offline', '__pycache__', '*.pyc'))
        # Numeric checkpoints cannot accidentally enter the training workspace.
        if any(work.rglob('*.npz')) or any(work.rglob('*.pt')):
            raise ValueError('The recovered source directory must contain code and reports only')
        def run(label, *args):
            print(label, flush=True)
            before = time.perf_counter()
            with (out/'logs'/f'{label}.log').open('w') as log:
                result = subprocess.run([sys.executable, *map(str,args)], cwd=work, env=env,
                                        stdout=log, stderr=subprocess.STDOUT, timeout=600)
            stages.append({'name': label, 'command': [*map(str,args)],
                           'elapsed_seconds_including_imports': time.perf_counter()-before,
                           'exit_code': result.returncode})
            if result.returncode:
                raise RuntimeError(f'{label} failed; see {out}/logs/{label}.log')
        run('01_visual_train', 'train.py', '--out', 'artifacts/pretrained',
            '--steps', 20 if smoke else 2400, '--seed', seed, '--threads', 2)
        run('02_probe_evaluate', 'evaluate.py', '--model', 'artifacts/pretrained',
            '--samples', 64 if smoke else 2048, '--probe-steps', 20 if smoke else 800)
        run('03_action_train', 'train_actions.py', '--out', 'artifacts/action_jepa',
            '--encoder', 'artifacts/pretrained', '--steps', 20 if smoke else 5000,
            '--examples', 256 if smoke else 65536, '--seed', action_seed)
        run('04_action_evaluate', 'evaluate_actions.py')
        run('05_browser_export', 'tools/build_orbit.py', '--skip-legacy')
        run('06_visual_tests', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_core.py', '-v')
        if not smoke:
            run('07_action_tests', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_actions.py', '-v')
        run('08_browser_parity', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_js.py', '-v')
        if ablation:
            run('09_ablation_train', 'train.py', '--out', 'artifacts/no_regularization',
                '--steps', 20 if smoke else 2400, '--seed', seed,
                '--variance-weight', 0, '--covariance-weight', 0)
            run('10_ablation_evaluate', 'evaluate.py', '--model', 'artifacts/no_regularization',
                '--samples', 64 if smoke else 2048, '--probe-steps', 20 if smoke else 800)
        metadata = {'recipe': 'recovered-temporal-jepa', 'date': datetime.now(timezone.utc).date().isoformat(),
                    'seed': seed, 'action_seed': action_seed, 'smoke_only': smoke,
                    'environment': environment(), 'source_sha256': hashes,
                    'pretrained_weights_read': False, 'empty_training_workspace_verified': True,
                    'stages': stages, 'elapsed_seconds': time.perf_counter()-started,
                    'note': 'Original numerical code unchanged. Cross-platform byte identity is not guaranteed. '
                            'Probe supervision is limited to display; planner uses frozen EMA teacher features.'}
        report = export_run(work, out, metadata)
    print(f'Complete: {out.name}; historical-scene hit rate {report["historical_scene_hit_rate"]:.4f}', flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--action-seed', type=int, default=31001)
    parser.add_argument('--smoke', action='store_true', help='Small execution check, not a quality benchmark')
    parser.add_argument('--ablation', action='store_true', help='Also train without variance/covariance penalties')
    args = parser.parse_args()
    train_pipeline(args.out, args.seed, args.action_seed, args.smoke, args.ablation)


if __name__ == '__main__':
    main()
