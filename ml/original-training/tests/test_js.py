"""Optional numerical parity test; skipped when Node.js is not installed."""
from __future__ import annotations
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
import torch
import numpy as np
from tinyjepa.core import World, load_model
from tinyjepa.evaluation import load_probe
from export_demo import package

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('node'), 'Node.js not installed: browser parity test skipped')
class JavascriptParity(unittest.TestCase):
    def test_exported_network_matches_pytorch(self):
        torch.set_num_threads(2)
        model_dir = ROOT / 'artifacts/pretrained'
        if not (model_dir / 'model.npz').exists():
            self.skipTest('No pretrained weights')
        model = load_model(model_dir)
        probe = load_probe(model_dir, model.cfg.dim)
        b = World(model.cfg, 30001).sample(8)
        with torch.no_grad():
            p, _ = model(b.context, b.horizon)
            xy = probe(p)
        payload = {'pack': package(model_dir),
                   'contexts': b.context.flatten(2).tolist(),
                   'horizons': b.horizon.tolist()}
        js = """
const fs=require('fs'), E=require(process.argv[1]);
const q=JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const result=q.contexts.map((c,i)=>{const z=E.predict(q.pack,c,q.horizons[i]);return {z,xy:E.decode(q.pack,z)};});
process.stdout.write(JSON.stringify(result));
"""
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp)/'fixture.json'
            f.write_text(json.dumps(payload), encoding='utf-8')
            result = subprocess.run(['node', '-e', js, str(ROOT/'web/engine.js'), str(f)],
                                    check=True, text=True, capture_output=True, timeout=30)
        output = json.loads(result.stdout)
        np.testing.assert_allclose([r['z'] for r in output], p.numpy(), atol=2e-5, rtol=2e-5)
        np.testing.assert_allclose([r['xy'] for r in output], xy.numpy(), atol=2e-5, rtol=2e-5)


if __name__ == '__main__':
    unittest.main()
