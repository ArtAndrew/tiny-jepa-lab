from pathlib import Path
import importlib.util,json,subprocess,unittest
import numpy as np
import torch
from planning.model import ActionWorld,ActionPredictor,load_predictor,load_encoder,rollout,PLANS
ROOT=Path(__file__).resolve().parents[1]
torch.set_num_threads(2)
class ActionTests(unittest.TestCase):
    def test_predictor_shapes_and_no_future_input(self):
        m=ActionPredictor();self.assertEqual(m(torch.randn(4,2,8),torch.zeros(4,3)).shape,(4,3,8))
        with self.assertRaises(ValueError):m(torch.randn(4,3,8),torch.zeros(4,3))
    def test_encoder_frozen(self):
        e=load_encoder();self.assertTrue(all(not p.requires_grad for p in e.parameters()))
    def test_finite_gradients(self):
        m=ActionPredictor();p=m(torch.randn(4,2,8),torch.zeros(4,3));p.square().mean().backward()
        self.assertTrue(all(p.grad is not None and p.grad.isfinite().all() for p in m.parameters()))
    def test_world_deterministic(self):
        a=ActionWorld(17).sample(8);b=ActionWorld(17).sample(8)
        for x,y in zip(a,b):torch.testing.assert_close(x,y,rtol=0,atol=0)
    def test_action_changes_prediction(self):
        m=load_predictor('artifacts/action_jepa');e=load_encoder();images,_,_,_=ActionWorld(18).sample(8)
        with torch.no_grad():
            z=e(images[:,:2].reshape(-1,24,24)).reshape(-1,2,8)
            delta=(m(z,torch.ones(8,3))-m(z,-torch.ones(8,3))).abs().mean()
        self.assertGreater(float(delta),.1)
    def test_export_and_javascript_parity(self):
        spec=importlib.util.spec_from_file_location('build_orbit',ROOT/'tools/build_orbit.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
        mf,data=b.bundle();self.assertEqual(mf['byteLength'],len(data))
        code="""const fs=require('fs'),C=require('./web/orbit-core.js');const m=JSON.parse(fs.readFileSync('site/assets/orbit-manifest.json'));const f=fs.readFileSync('site/assets/'+m.binary);const p=C.unpack(m,f.buffer.slice(f.byteOffset,f.byteOffset+f.byteLength));const s=C.scenario(71),r=C.predict(p,s.frames,[-1,0,1]),best=C.rankPlans(p,s.frames,s.goalFrame)[0];console.log(JSON.stringify({frames:s.frames,z:r.z,xy:r.xy,best:best.index,goal:s.goalFrame}));"""
        out=json.loads(subprocess.check_output(['node','-e',code],cwd=ROOT));encoder=load_encoder();m=load_predictor('artifacts/action_jepa')
        with torch.no_grad():
            z=encoder(torch.tensor(out['frames']).reshape(2,24,24)).reshape(1,2,8)
            pred=m(z,torch.tensor([[-1.,0.,1.]]))[0]
            goal=encoder(torch.tensor(out['goal']).reshape(1,24,24))
            allp=m(z.expand(27,-1,-1),PLANS);cost=((allp[:,2]-goal)/m.scale).square().mean(-1)
        np.testing.assert_allclose(pred.numpy(),np.array(out['z']),rtol=2e-5,atol=2e-5)
        self.assertEqual(int(cost.argmin()),out['best'])
    def test_browser_and_python_physics_match(self):
        code="""const C=require('./web/orbit-core.js'),s=C.scenario(912);console.log(JSON.stringify({p:s.p1,v:s.v,out:C.PLANS.map(a=>C.simulate(s.p1,s.v,a).ends)}));"""
        out=json.loads(subprocess.check_output(['node','-e',code],cwd=ROOT))
        a=rollout(torch.tensor([out['p']]).expand(27,-1),torch.tensor([out['v']]).expand(27,-1),PLANS)
        np.testing.assert_allclose(a.numpy(),np.array(out['out']),atol=2e-7,rtol=1e-6)
    def test_translations_and_template(self):
        import re
        d={l:json.loads((ROOT/'web/orbit-i18n'/f'{l}.json').read_text()) for l in ('en','ru','zh')}
        for lang in d:
            self.assertEqual(set(d['en']),set(d[lang]))
            for key in d['en']:self.assertEqual(sorted(re.findall(r'\{\w+\}',d['en'][key])),sorted(re.findall(r'\{\w+\}',d[lang][key])))
        for p in [ROOT/'site/index.html',ROOT/'site/ru/index.html',ROOT/'site/zh/index.html']:
            text=p.read_text();self.assertNotRegex(text,r'__[A-Z_]+__|\{\{\w+\}\}')
    def test_evaluation_is_held_out_and_finite(self):
        r=json.loads((ROOT/'artifacts/action_jepa/evaluation.json').read_text());t=json.loads((ROOT/'artifacts/action_jepa/training.json').read_text())
        self.assertEqual(r['n'],1024);self.assertTrue(t['encoder_frozen']);self.assertFalse(t['coordinate_labels_used'])
        for key in ['model','random','no_push','oracle','shuffled_actions']:
            self.assertTrue(np.isfinite(r[key]['goal_distance_px']['mean']))
            self.assertTrue(0<=r[key]['hit_rate']['mean']<=1)
    def test_read_only_replay_workflow(self):
        text=(ROOT/'.github/workflows/pages.yml').read_text()
        self.assertNotIn('contents: write',text);self.assertNotIn('issues: write',text)
        # Untrusted issue bodies/titles are never interpolated in a shell command.
        for line in text.splitlines():
            if 'run:' in line:self.assertNotIn('github.event.issue',line)
if __name__=='__main__':unittest.main()
