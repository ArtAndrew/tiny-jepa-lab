"""Recovered-source provenance and independence of temporal encoder training."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import numpy as np
from planning.model import ROOT


@unittest.skipUnless(importlib.util.find_spec('torch'), 'Install training dependencies')
class OriginalTrainingTests(unittest.TestCase):
    def test_source_hashes_and_supplied_tensors_match_the_game(self):
        from planning.original_training import verify_source
        self.assertEqual(len(verify_source()), 17)
        for name, source, prefix in [('encoder', 'pretrained/model.npz', 'teacher.'),
                                     ('probe', 'pretrained/probe.npz', ''),
                                     ('predictor', 'action_jepa/predictor.npz', '')]:
            with np.load(ROOT/'artifacts/action_jepa'/f'{name}.npz', allow_pickle=False) as a, \
                 np.load(ROOT/'artifacts/original-training'/source, allow_pickle=False) as b:
                for key in a.files:
                    np.testing.assert_array_equal(a[key], b[prefix+key])

    def test_temporal_training_repeats_without_reference_weights(self):
        source = ROOT/'ml/original-training'
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            shutil.copyfile(source/'train.py', work/'train.py')
            shutil.copytree(source/'tinyjepa', work/'tinyjepa', ignore=shutil.ignore_patterns('__pycache__'))
            self.assertFalse(list(work.rglob('*.npz')))
            env = dict(os.environ, OPENBLAS_NUM_THREADS='1')
            env.pop('PYTHONPATH', None)
            for name in ['first', 'repeat']:
                subprocess.run([sys.executable, 'train.py', '--out', name, '--steps', '30'],
                               cwd=work, env=env, check=True, capture_output=True, timeout=120)
            with np.load(work/'first/model.npz', allow_pickle=False) as a, \
                 np.load(work/'repeat/model.npz', allow_pickle=False) as b:
                for key in a.files:
                    np.testing.assert_array_equal(a[key], b[key])
                self.assertFalse(np.array_equal(a['encoder.net.1.weight'], a['teacher.net.1.weight']))


if __name__ == '__main__':
    unittest.main()
