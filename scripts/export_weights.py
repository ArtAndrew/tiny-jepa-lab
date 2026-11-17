#!/usr/bin/env python3
"""Export the exact released tensors; this is not retraining."""
import base64
import hashlib
import json
from pathlib import Path
import re
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def export():
    source = (ROOT / 'source/ORBIT_JEPA_RU_EN_ZH.html').read_text()
    def embedded(name):
        return re.search(r'<script id="' + name + r'"[^>]*>(.*?)</script>', source, re.S)[1]
    manifest = json.loads(embedded('orbit-manifest'))
    binary = base64.b64decode(embedded('orbit-bytes'))
    assert hashlib.sha256(binary).hexdigest() == manifest['sha256']
    assert len(binary) == manifest['byteLength']
    destination = ROOT / 'artifacts/action_jepa'
    destination.mkdir(parents=True, exist_ok=True)
    files = {}
    for group, filename in [('weights', 'encoder.npz'), ('action', 'predictor.npz'), ('probe', 'probe.npz')]:
        tensors = {}
        for key, spec in manifest[group].items():
            tensor = np.frombuffer(binary, dtype='<f4', count=spec['length'], offset=spec['offset']).reshape(spec['shape'])
            tensors[key.removeprefix('teacher.')] = tensor
        path = destination / filename
        np.savez(path, **tensors)
        files[filename] = hashlib.sha256(path.read_bytes()).hexdigest()
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    provenance = {'origin': 'Exact tensors exported from the supplied v0.3 HTML; no retraining.',
                  'source': 'source/ORBIT_JEPA_RU_EN_ZH.html', 'source_binary_sha256': manifest['sha256'],
                  'model_id': manifest['modelId'], 'files_sha256': files,
                  'encoder_pretraining': 'Original pretraining code/data are unavailable. Encoder is supplied as a frozen dependency.'}
    (destination / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print(json.dumps(provenance, indent=2))


if __name__ == '__main__':
    export()
