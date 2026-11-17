"""Build ORBIT v0.3, its standalone HTML, and the preserved v0.2 prediction lab."""
from pathlib import Path
import argparse,base64,hashlib,html,json,re,shutil,subprocess,sys
from urllib.parse import urlparse
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def js_json(data):return json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
def bundle():
    blob=[];offset=0;meta={}
    for group,path in [('weights',ROOT/'artifacts/pretrained/model.npz'),('probe',ROOT/'artifacts/pretrained/probe.npz'),('action',ROOT/'artifacts/action_jepa/predictor.npz')]:
        meta[group]={}
        with np.load(path,allow_pickle=False) as f:
            for key in sorted(f.files):
                if group=='weights' and not key.startswith('teacher.'):continue
                a=np.asarray(f[key],dtype='<f4')
                if not np.isfinite(a).all():raise ValueError('Non-finite weight')
                meta[group][key]={'shape':list(a.shape),'offset':offset,'length':a.size}
                b=a.tobytes();blob.append(b);offset+=len(b)
    data=b''.join(blob);sha=hashlib.sha256(data).hexdigest()
    meta.update(version=1,rules='orbit-1',sha256=sha,modelId=sha[:12],byteLength=len(data),binary=f'orbit-weights-{sha[:12]}.bin')
    return meta,data

def render(lang,translations,manifest,weights,benchmark,board,base,repo,offline,live):
    d=translations[lang];prefix='./' if lang=='en' else '../';page=base+('' if lang=='en' else lang+'/')
    config={'lang':lang,'assetPrefix':prefix+'assets/','baseUrl':base,'repo':repo,'offline':offline,'live':bool(live and not offline)}
    if offline:
        style='<style>'+(ROOT/'web/orbit.css').read_text()+'</style>'
        scripts='\n'.join('<script>'+(ROOT/'web'/s).read_text()+'</script>' for s in ('engine.js','orbit-core.js','orbit.js'))
        wb='<script id="orbit-manifest" type="application/json">'+js_json(manifest)+'</script><script id="orbit-bytes" type="application/octet-stream">'+base64.b64encode(weights).decode()+'</script>'
    else:
        style=f'<link rel="stylesheet" href="{prefix}assets/orbit.css">'
        scripts='\n'.join(f'<script src="{prefix}assets/{s}"></script>' for s in ('engine.js','orbit-core.js','orbit.js'));wb=''
    tokens={'__LANG__':lang,'__PAGE_URL__':html.escape(page,quote=True),'__BASE_URL__':html.escape(base,quote=True),'__REPO_URL__':'https://github.com/'+repo,'__STYLES__':style,'__SCRIPTS__':scripts,'__WEIGHTS__':wb,'__CONFIG__':js_json(config),'__I18N__':js_json(translations),'__BENCHMARK__':js_json(benchmark),'__BOARD__':js_json(board)}
    text=(ROOT/'web/orbit.html').read_text()
    text=re.sub(r'\{\{(\w+)\}\}',lambda m:html.escape(d[m.group(1)]),text)
    for k,v in tokens.items():text=text.replace(k,v)
    return text

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',default='ArtAndrew/tiny-jepa-lab');p.add_argument('--base-url',default='https://artandrew.github.io/tiny-jepa-lab/');p.add_argument('--offline',action='store_true');p.add_argument('--live',action='store_true',help='Enable GitHub submission only in the hosted build');p.add_argument('--skip-legacy',action='store_true')
    a=p.parse_args();base=a.base_url.rstrip('/')+'/'
    u=urlparse(base)
    if u.scheme!='https' or not u.netloc or u.query or u.fragment:p.error('Expected absolute HTTPS base URL')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',a.repo):p.error('Invalid OWNER/REPO')
    out=ROOT/'site';assets=out/'assets';assets.mkdir(parents=True,exist_ok=True)
    if not a.skip_legacy:subprocess.run([sys.executable,str(ROOT/'tools/build_site.py'),'--output',str(out/'predict'),'--repo',a.repo,'--base-url',base+'predict/'],check=True)
    translations={l:json.loads((ROOT/'web/orbit-i18n'/f'{l}.json').read_text()) for l in ('en','ru','zh')}
    for lang,d in translations.items():
        if set(d)!=set(translations['en']):raise ValueError('Translation mismatch: '+lang)
    manifest,data=bundle();(assets/manifest['binary']).write_bytes(data)
    (assets/'orbit-manifest.json').write_text(js_json(manifest))
    # The validator checks this exact model fingerprint; changing weights creates a new league.
    (ROOT/'artifacts/action_jepa/release.json').write_text(json.dumps({'rules':'orbit-1','model':manifest['modelId'],'sha256':manifest['sha256']},indent=2))
    benchmark=json.loads((ROOT/'artifacts/action_jepa/evaluation.json').read_text())
    board=json.loads((ROOT/'leaderboard/board.json').read_text())
    (assets/'leaderboard.json').write_text(js_json(board))
    for name in ('engine.js','orbit-core.js','orbit.js','orbit.css'):shutil.copy2(ROOT/'web'/name,assets/name)
    for lang in translations:
        page=out/('index.html' if lang=='en' else lang+'/index.html');page.parent.mkdir(parents=True,exist_ok=True)
        page.write_text(render(lang,translations,manifest,data,benchmark,board,base,a.repo,False,a.live))
        if (ROOT/'web'/f'orbit-social-{lang}.png').exists():shutil.copy2(ROOT/'web'/f'orbit-social-{lang}.png',assets/f'social-{lang}.png')
    (out/'.nojekyll').write_text('');(out/'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: '+base+'sitemap.xml\n')
    (out/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+base+s+'</loc></url>' for s in ('','ru/','zh/','predict/'))+'</urlset>')
    if a.offline:
        directory=ROOT/'offline';directory.mkdir(exist_ok=True)
        (directory/'ORBIT_Action_JEPA_RU_EN_ZH.html').write_text(render('ru',translations,manifest,data,benchmark,board,base,a.repo,True,False))
    print(f'ORBIT weights: {len(data):,} bytes; model: {manifest["modelId"]}; live: {a.live}')

if __name__=='__main__':main()
