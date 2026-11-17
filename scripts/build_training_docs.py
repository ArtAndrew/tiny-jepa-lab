"""Render the from-scratch comparison directly from measured JSON reports."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
vicreg = json.loads((root/'reports/from-scratch.json').read_text())
temporal = json.loads((root/'reports/temporal.json').read_text())
rows = []
rows += [(name + (' (current game)' if name == json.loads((root/'source/model-release.json').read_text())['benchmarkModel'] else ''), entry) for name, entry in temporal['models'].items()]
rows += [('VICReg '+name.removeprefix('scratch-'), entry)
         for name, entry in vicreg['models'].items() if name != 'released_v03']
table = ['| Model | Normal hits, 95% CI | More image noise | Weaker push | Stronger push |',
         '|---|---:|---:|---:|---:|']
for name, entry in rows:
    cells = []
    for condition in ['normal', 'noisy', 'weak_push', 'strong_push']:
        result = entry['conditions'][condition]['aggregate']['model']
        value = f"{100*result['hit_rate']:.2f}%"
        if condition == 'normal':
            low, high = result['hit_ci95_wilson']
            value += f' [{100*low:.2f}, {100*high:.2f}]'
        cells.append(value)
    table.append('| '+name+' | '+' | '.join(cells)+' |')
random = rows[0][1]['conditions']['normal']['aggregate']['random']['hit_rate']
content = '\n'.join(table)+f'\n\nRandom control: **{100*random:.2f}%** normal-condition hits; exact-physics oracle: **100%**.\n\n'
content += '[Temporal report](reports/temporal.json) · [VICReg and released-model report](reports/from-scratch.json) · [All checkpoints and logs](experiments/)'
path = root/'FROM_SCRATCH.md'
text = path.read_text()
before, tail = text.split('<!-- measured:start -->')
_, after = tail.split('<!-- measured:end -->')
path.write_text(before+'<!-- measured:start -->\n'+content+'\n<!-- measured:end -->'+after)
