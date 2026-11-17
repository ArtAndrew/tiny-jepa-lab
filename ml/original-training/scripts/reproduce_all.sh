#!/usr/bin/env bash
# Rebuild each model from random initialization. No pretrained weights shipped in this archive.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p logs artifacts
echo "== Reference environment =="
python - <<'ENV' | tee logs/environment.txt
import sys, platform, torch, numpy as np, os
print('python:',sys.version)
print('platform:',platform.platform())
print('CPU:',platform.processor() or '(not reported)')
print('torch:',torch.__version__,'numpy:',np.__version__)
print('torch threads:',torch.get_num_threads())
ENV
if command -v node >/dev/null 2>&1; then node --version | tee -a logs/environment.txt; else echo 'Node.js required for action held-out evaluation' >&2; exit 2; fi
if test -e artifacts/pretrained/model.npz || test -e artifacts/action_jepa/predictor.npz; then
  echo 'Refusing to overwrite existing weights: use a clean unpacked folder.' >&2
  exit 3
fi
python train.py --out artifacts/pretrained --steps 2400 --batch-size 128 --seed 42 --device cpu --threads 2 --lr .001 --variance-weight 10 --covariance-weight 1 | tee logs/01_visual_train.log
python evaluate.py --model artifacts/pretrained --samples 2048 --probe-steps 800 --threads 2 | tee logs/02_probe_evaluate.log
python train_actions.py --out artifacts/action_jepa --steps 5000 --examples 65536 --seed 31001 --threads 2 --encoder artifacts/pretrained | tee logs/03_action_train.log
python evaluate_actions.py | tee logs/04_action_evaluate.log
python tools/build_orbit.py --skip-legacy | tee logs/05_web_export.log
python -m unittest discover -s tests -p 'test_core.py' -v > logs/05_visual_tests.log 2>&1
python -m unittest discover -s tests -p 'test_actions.py' -v > logs/06_action_tests.log 2>&1
python -m unittest discover -s tests -p 'test_js.py' -v > logs/07_js_tests.log 2>&1
python scripts/check_reproduction.py | tee logs/08_check.log
if [[ "${WITH_ABLATION:-0}" == "1" ]]; then
  python train.py --out artifacts/no_regularization --steps 2400 --batch-size 128 --seed 42 --device cpu --threads 2 --lr .001 --variance-weight 0 --covariance-weight 0 | tee logs/09_ablation_train.log
  python evaluate.py --model artifacts/no_regularization --samples 2048 --probe-steps 800 --threads 2 | tee logs/10_ablation_evaluate.log
fi
echo 'Complete: artifacts/pretrained, artifacts/action_jepa, logs/'
