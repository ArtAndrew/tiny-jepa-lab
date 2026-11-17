"""Held-out planning evaluation. Test cases come from the browser's exact game rules.
Model selection uses separate validation data, not this report. No LLM baseline is implied.
"""
from pathlib import Path
import json, subprocess, itertools, math
import numpy as np
import torch
from planning.model import load_encoder,load_predictor,PLANS
from tinyjepa.evaluation import load_probe

def stats(x):
    x=np.asarray(x,dtype=float);mu=x.mean();se=x.std(ddof=1)/np.sqrt(len(x))
    return {'mean':float(mu),'ci95':[float(mu-1.96*se),float(mu+1.96*se)]}

def rate(x):
    x=np.asarray(x,dtype=float); n=len(x); p=float(x.mean()); z=1.96
    den=1+z*z/n; center=(p+z*z/(2*n))/den
    half=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return {"mean":p,"ci95":[float(max(0,center-half)),float(min(1,center+half))],"method":"Wilson interval"}

def main():
    torch.set_num_threads(2)
    script="""const C=require('./web/orbit-core.js');const out=[];for(let i=0;i<1024;i++){const s=C.scenario(C.hash('held-out-orbit-20261116|'+i));out.push({...s,all:C.PLANS.map(a=>C.outcome(s,a))});}process.stdout.write(JSON.stringify(out));"""
    cases=json.loads(subprocess.check_output(['node','-e',script]))
    encoder=load_encoder();model=load_predictor('artifacts/action_jepa');probe=load_probe(Path('artifacts/pretrained'),8)
    rows=[];rng=np.random.default_rng(99017)
    with torch.no_grad():
        for offset in range(0,len(cases),64):
            c=cases[offset:offset+64];n=len(c)
            frames=torch.tensor([s['frames'] for s in c]).reshape(-1,24,24)
            goal=encoder(torch.tensor([s['goalFrame'] for s in c]).reshape(-1,24,24))
            z=encoder(frames).reshape(n,2,8)
            z=z[:,None].expand(-1,27,-1,-1).reshape(-1,2,8)
            act=PLANS[None].expand(n,-1,-1).reshape(-1,3)
            p=model(z,act).reshape(n,27,3,8)
            # Goal-space planning: no coordinate probe or physical simulator in selection.
            cost=((p[:,:,2]-goal[:,None])/model.scale).square().mean(-1)
            ids=cost.argmin(1).numpy()
            xy=probe(p[:,:,2].reshape(-1,8)).reshape(n,27,2).numpy()
            for j,s in enumerate(c):
                ds=np.array([a['distance'] for a in s['all']]);k=int(ids[j]);r=int(rng.integers(27))
                # Shuffling actions fed to the predictor preserves candidates but breaks their meaning.
                perm=rng.permutation(27);broken=int(perm[k])
                err=np.linalg.norm(xy[j]-np.array([a['final'] for a in s['all']]),axis=1)*23
                rows.append({'model':float(ds[k]),'random':float(ds[r]),'no_push':float(ds[13]),
                             'oracle':float(ds.min()),'shuffled_actions':float(ds[broken]),
                             'prediction_error_px':float(err.mean()),'selected':k})
    report={'n':len(rows),'seed_namespace':'held-out-orbit-20261116','protocol':'3 impulses, 2 ticks each, 27 candidate sequences; clean goal image; pixel input only',
            'goal_hit_radius_normalized':.06,'pixel_scale':23,'single_training_seed':True,
            'warning':'Synthetic task, frozen pretrained encoder, direct multi-horizon predictor. Not a universal world model or real robotic controller.'}
    for name in ['model','random','no_push','oracle','shuffled_actions']:
        ds=np.array([r[name] for r in rows]);report[name]={'goal_distance_px':stats(ds*23),'hit_rate':rate(ds<=.06),
              'mean_round_score':stats(np.maximum(0,np.floor(1000*(1-ds/.5)+.5)))}
    report['prediction_error_px']=stats([r['prediction_error_px'] for r in rows])
    out=Path('artifacts/action_jepa');(out/'evaluation.json').write_text(json.dumps(report,indent=2))
    (out/'eval_cases.json').write_text(json.dumps(rows,separators=(',',':')))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
