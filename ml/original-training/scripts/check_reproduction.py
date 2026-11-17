from pathlib import Path
import json, hashlib
root=Path(__file__).resolve().parents[1]
ref=json.loads((root/'reference/action_jepa/evaluation.json').read_text())
new=json.loads((root/'artifacts/action_jepa/evaluation.json').read_text())
vis=json.loads((root/'artifacts/pretrained/metrics.json').read_text())
print('Visual position error, px:',round(vis['in_distribution']['jepa_error']['mean'],6))
print('Original visual error, px:',round(json.loads((root/'reference/pretrained/metrics.json').read_text())['in_distribution']['jepa_error']['mean'],6))
print('Action hit rate:',f"{100*new['model']['hit_rate']['mean']:.3f}%", 'reference:',f"{100*ref['model']['hit_rate']['mean']:.3f}%")
for key in ['model','random','no_push','oracle']:
    print(key, f"reproduced {100*new[key]['hit_rate']['mean']:.3f}%, original {100*ref[key]['hit_rate']['mean']:.3f}%")
sha=hashlib.sha256((root/'artifacts/pretrained/model.npz').read_bytes()).hexdigest()
expected=json.loads((root/'reference/CHECKPOINT_SHA256.json').read_text())['artifacts/pretrained/model.npz']
print('Encoder model.npz sha256:',sha, 'matches original bytes:',sha==expected)
print('NOTE: same seeds need not imply bitwise identical results across hardware/library versions.')
