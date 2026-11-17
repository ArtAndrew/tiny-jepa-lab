#!/usr/bin/env python3
"""Prepare GitHub Pages from the supplied self-contained ORBIT release."""
from pathlib import Path
import hashlib
import html
import json
import re
import base64
import argparse

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://artandrew.github.io/tiny-jepa-lab/"
REPO = "https://github.com/ArtAndrew/tiny-jepa-lab"
source = (ROOT / "source/ORBIT_JEPA_RU_EN_ZH.html").read_text()
parser = argparse.ArgumentParser()
parser.add_argument('--leaderboard', type=Path, help='Verified leaderboard snapshot to embed')
args = parser.parse_args()
board = json.loads(args.leaderboard.read_text()) if args.leaderboard else {"version": 1, "updated": None, "entries": []}
assert board.get('version') == 1 and isinstance(board.get('entries'), list)

# Server verification executes the exact same deterministic rules as the browser.
executables = [body for attr, body in re.findall(r'<script\b([^>]*)>(.*?)</script>', source, re.S) if 'type=' not in attr]
assert len(executables) == 3 and 'rankPlans' in executables[1]
(ROOT / 'game').mkdir(exist_ok=True)
for name, body in zip(['engine.js', 'orbit.js'], executables[:2]):
    (ROOT / 'game' / name).write_text(body)


def embedded(text, key):
    return json.loads(re.search(rf'<script id="{key}"[^>]*>(.*?)</script>', text, re.S)[1])


def replace_json(text, key, value):
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    return re.sub(rf'(<script id="{key}"[^>]*>).*?(</script>)',
                  lambda m: m[1] + payload + m[2], text, flags=re.S)


manifest = embedded(source, "orbit-manifest")
weights = base64.b64decode(re.search(r'<script id="orbit-bytes"[^>]*>(.*?)</script>', source, re.S)[1])
assert len(weights) == manifest["byteLength"]
assert hashlib.sha256(weights).hexdigest() == manifest["sha256"]

i18n = embedded(source, "orbit-i18n")
introduction = json.loads((ROOT / "source/introduction.json").read_text())
intro_html = (ROOT / "source/introduction.html").read_text()
intro_css = (ROOT / "source/introduction.css").read_text()
explainer = json.loads((ROOT / "source/explainer.json").read_text())
glass = json.loads((ROOT / 'source/glass-example.json').read_text())
failures_i18n = json.loads((ROOT / 'source/failures.json').read_text())
failures = json.loads((ROOT / 'docs/assets/failures.json').read_text())
assert failures['modelId'] == manifest['modelId']
research_copy = json.loads((ROOT / 'source/research.json').read_text())
research_report = json.loads((ROOT / 'reports/benchmark.json').read_text())
measured = research_report['models']['released_v03']['conditions']['normal']['aggregate']
benchmark_data = {'n': research_report['per_seed'] * len(research_report['seeds']),
                  'protocol': research_report['protocol'], 'evaluation_seeds': research_report['seeds']}
for name, result in measured.items():
    benchmark_data[name] = {'hit_rate': {'mean': result['hit_rate'], 'ci95': result['hit_ci95_wilson']},
                            'goal_distance_px': {'mean': result['mean_distance_px'], 'ci95': result['distance_ci95_normal']}}
intro_html = intro_html.replace('<details class="intro-details">',
    (ROOT / 'source/glass-example.html').read_text() + '\n' +
    (ROOT / "source/explainer.html").read_text() + '\n<details class="intro-details">')
extra_css = '\n'.join((ROOT / ("source/" + name + ".css")).read_text() for name in ["explainer", "theme", "controls", "glass-example", "failures"])
theme_js = (ROOT / "source/theme.js").read_text()
theme_html = (ROOT / "source/theme.html").read_text()
for language, values in introduction.items():
    i18n[language].update(values)
    i18n[language].update(explainer[language])
    i18n[language].update(glass[language])
    i18n[language].update(failures_i18n[language])
    i18n[language].update(research_copy[language])


def replace_once(text, old, new):
    assert text.count(old) == 1, f"Expected one injection marker: {old}"
    return text.replace(old, new, 1)


def themed_canvas(text, start, end):
    """Only replace display colors; physics, inputs and model weights stay intact."""
    a, b = text.index(start), text.index(end, text.index(start))
    block = re.sub(r"'(#(?:[a-fA-F0-9]{8}|[a-fA-F0-9]{6}))'",
                   lambda m: "window.OrbitTheme.color('" + m[1] + "')", text[a:b])
    return text[:a] + block + text[b:]
updates = json.loads((ROOT / 'source/leaderboard.json').read_text())
for language, values in updates.items():
    i18n[language].update(values)

for language, route in [("en", ""), ("ru", "ru/"), ("zh", "zh/")]:
    text = source
    text = replace_once(text, '</style>', intro_css + '\n' + extra_css + '\n</style>')
    text = replace_once(text, '<style>', '<script>' + theme_js + '</script>\n<style>')
    text = replace_once(text, '<style>', '<script>' + (ROOT / 'source/navigation.js').read_text() + '</script>\n<style>')
    failure_json = json.dumps(failures, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    text = replace_once(text, '<section id="learn"',
                        (ROOT / 'source/failures.html').read_text() + '\n<script id="orbit-failures" type="application/json">' + failure_json + '</script>\n<section id="learn"')
    text = replace_once(text, '<div id="action-controls">', '<p id="failure-active" class="small" hidden></p><div id="action-controls">')
    text = replace_once(text, 'function setLanguage(next)', (ROOT / 'source/navigation-ui.js').read_text() + '\nfunction setLanguage(next)')
    text = replace_once(text, "try{const u=new URL(location.href);u.searchParams.set('lang',lang);history.replaceState(null,'',u);}catch{}", 'syncLanguageUrl();renderFailures();')
    text = replace_once(text, 'function newScene(){animationKey++;', 'function newScene(){clearFailure();animationKey++;')
    text = replace_once(text, 'newScene();setLanguage(lang);if(cfg.live', "newScene();if(params.has('example'))openFailure(params.get('example'),false);setLanguage(lang);if(cfg.live")
    localized_intro = intro_html.replace('{{ASSET_PREFIX}}', '../assets/' if route else 'assets/')
    text = replace_once(text, '<div id="notice"', localized_intro + '\n<div id="notice"')
    text = replace_once(text, '<div class="languages"', theme_html + '<div class="languages"')
    text = replace_once(text, '<p id="board-note" class="board-note">',
                        '<p id="board-note" class="board-note" role="status" aria-live="polite">')
    text = replace_once(text, '<button id="clear-local"',
                        '<button id="refresh-board" class="text-btn" data-t="boardRefresh" hidden></button><button id="clear-local"')
    a, b = text.index('function boardRow('), text.index('function payload(')
    text = text[:a] + (ROOT / 'source/leaderboard-ui.js').read_text() + '\n' + text[b:]
    a, b = text.index('function submit(){'), text.index('function card(){')
    text = text[:a] + """function submit(){if(!finished||!canSubmit())return;const body=T('submissionBody')+'\\n\\n<!-- ORBIT_REPLAY -->\\n```json\\n'+JSON.stringify(payload())+'\\n```';const u=new URL('https://github.com/'+cfg.repo+'/issues/new');u.searchParams.set('title','[ORBIT replay] '+day);u.searchParams.set('body',body);window.open(u.href,'_blank','noopener,noreferrer');toast(T('submitOpened'));}
""" + text[b:]
    fetch_start = text.index("if(cfg.live&&!cfg.offline){try{const r=await fetch")
    fetch_end = text.index("window.dispatchEvent(new CustomEvent('orbit-ready'))", fetch_start)
    text = text[:fetch_start] + 'await loadLeaderboard();' + text[fetch_end:]
    text = replace_once(text, "b.type='button';b.dataset.step=i;", "b.append(el('span','choice-caption',T(a===-1?'choiceLeft':a===1?'choiceRight':'choiceCoast')));b.type='button';b.dataset.step=i;")
    text = replace_once(text, "txt('model-id',manifest?manifest.modelId.slice(0,8):'');", "txt('model-id','');")
    text = replace_once(text, "document.title=T('pageTitle');", "document.title=T('pageTitle');document.querySelectorAll('[data-t-alt]').forEach(n=>n.alt=T(n.dataset.tAlt));")
    text = replace_once(text, "mode==='daily'?day+' UTC':C.RULES.toUpperCase()", "mode==='daily'?day+' UTC':T('playground')")
    text = replace_once(text, "mode==='daily'?`${day} · ${round+1}/5 · ${C.RULES}`:`SEED ${scene?.seed??'—'} · ${C.RULES}`", "mode==='daily'?`${day} · ${round+1}/5`:T('playground')")
    text = themed_canvas(text, 'function draw(){', 'function renderInspection(){')
    text = themed_canvas(text, 'function card(){', '\nasync function boot(')
    text = replace_once(text, 'setLanguage(lang);boot();',
                        (ROOT / 'source/failures-ui.js').read_text() + "\nwindow.addEventListener('orbit-theme-change',draw);\n$('refresh-board').onclick=loadLeaderboard;\nwindow.addEventListener('focus',()=>{if(Date.now()-boardFetchedAt>15000)loadLeaderboard();});\nsetLanguage(lang);boot();")
    config = embedded(text, "orbit-config")
    config.update(lang=language, offline=False, live=True, published=True,
                  baseUrl=BASE, repo="ArtAndrew/tiny-jepa-lab",
                  assetPrefix="../assets/" if route else "assets/")
    text = replace_json(text, "orbit-config", config)
    text = replace_json(text, "orbit-i18n", i18n)
    text = replace_json(text, "orbit-board", board)
    text = replace_json(text, "orbit-benchmark", benchmark_data)
    text = replace_once(text, 'MIT · v0.3', 'MIT · v0.5')
    text = re.sub(r'<html lang="[^"]+">', '<html lang="' + ("zh-Hans" if language == "zh" else language) + '">', text, count=1)
    title = html.escape(i18n[language]["pageTitle"], quote=True)
    description = html.escape(i18n[language]["description"], quote=True)
    text = re.sub(r'<title>.*?</title>', lambda _: '<title>' + title + '</title>', text, count=1)
    for attr, key, value in [("name", "description", description), ("property", "og:title", title),
                             ("property", "og:description", description), ("property", "og:url", BASE + route)]:
        text = re.sub(rf'<meta {attr}="{key}" content="[^"]*">',
                      lambda _, a=attr, k=key, v=value: f'<meta {a}="{k}" content="{v}">', text, count=1)
    text = re.sub(r'<link rel="canonical" href="[^"]*">',
                  lambda _: '<link rel="canonical" href="' + BASE + route + '">', text, count=1)
    # Public previews are generated from a real replay by scripts/build_media.py.
    social_image = BASE + 'assets/orbit-social-' + language + '.png'
    text = re.sub(r'<meta property="og:image" content="[^"]*">',
                  lambda _: '<meta property="og:image" content="' + social_image + '">', text)
    preview_meta = '\n'.join([
        '<meta property="og:image:width" content="1280">',
        '<meta property="og:image:height" content="640">',
        '<meta property="og:image:alt" content="' + description + '">',
        '<meta name="twitter:image" content="' + social_image + '">',
        '<meta name="twitter:title" content="' + title + '">',
        '<meta name="twitter:description" content="' + description + '">',
    ])
    text = replace_once(text, '</head>', preview_meta + '\n</head>')
    text = text.replace(BASE + 'predict/', REPO + '/blob/main/REPRODUCIBILITY.md')
    research_links = '<p class="small">' + ' · '.join(
        '<a href="' + REPO + '/blob/main/' + path + '" data-t="' + key + '"></a>'
        for path, key in [('materials/ORBIT_Action_Planning.ipynb', 'researchNotebook'),
                          ('materials/ORBIT_From_Scratch.ipynb', 'researchTraining'),
                          ('BENCHMARK.md', 'researchBenchmark'), ('MODEL_CARD.md', 'researchModel')]) + '</p>'
    text = replace_once(text, '</a></div></div></section>', '</a>' + research_links + '</div></div></section>')
    # Sharing a public URL is independent of enabling a public replay backend.
    text = text.replace("if(cfg.live)s+='\\n'+shareLink();", "if(cfg.published)s+='\\n'+shareLink();")
    text = text.replace("cfg.live?new URL(cfg.baseUrl).host", "cfg.published?new URL(cfg.baseUrl).host")
    # Translate existing text-only labels before JavaScript boots.
    text = re.sub(r'(<([a-z0-9]+)\b[^>]*\bdata-t="([^"]+)"[^>]*>)([^<]*)(</\2>)',
                  lambda m: m[1] + html.escape(i18n[language].get(m[3], html.unescape(m[4]))) + m[5], text)
    text = re.sub(r'(<img\b[^>]*\bdata-t-alt="([^"]+)"[^>]*\balt=")[^"]*(")',
                  lambda m: m[1] + html.escape(i18n[language][m[2]], quote=True) + m[3], text)
    destination = ROOT / "docs" / route / "index.html"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text)
    print(destination.relative_to(ROOT), len(text.encode()), "bytes")

(ROOT / "docs/.nojekyll").touch()
(ROOT / 'docs/assets').mkdir(exist_ok=True)
(ROOT / 'docs/assets/leaderboard.json').write_text(json.dumps(board, ensure_ascii=False, separators=(',', ':'))+'\n')
(ROOT / "docs/robots.txt").write_text("User-agent: *\nAllow: /\nSitemap: " + BASE + "sitemap.xml\n")
(ROOT / "docs/sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
    ''.join('<url><loc>' + BASE + route + '</loc></url>\n' for route in ["", "ru/", "zh/"]) + '</urlset>\n')
print("Original model verified:", manifest["modelId"], manifest["sha256"])
