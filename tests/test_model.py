import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
import numpy as np
from planning.model import ARTIFACTS, PLANS, ROOT, load_model, load_active_model, rollout, scenario, seed_hash
from planning.benchmark import evaluate, summary


class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.model = load_model()

    def test_export_contains_exact_released_tensors(self):
        source = (ROOT/'source/ORBIT_JEPA_RU_EN_ZH.html').read_text()
        manifest = json.loads(re.search(r'<script id="orbit-manifest"[^>]*>(.*?)</script>',source,re.S)[1])
        binary = base64.b64decode(re.search(r'<script id="orbit-bytes"[^>]*>(.*?)</script>',source,re.S)[1])
        self.assertEqual(hashlib.sha256(binary).hexdigest(),manifest['sha256'])
        for group, weights in [('weights',self.model.encoder),('action',self.model.action),('probe',self.model.probe)]:
            for key,spec in manifest[group].items():
                actual = weights[key.removeprefix('teacher.')].astype('<f4').tobytes()
                self.assertEqual(actual,binary[spec['offset']:spec['offset']+4*spec['length']])

    def test_independent_browser_parity_all_plans(self):
        node = os.environ.get('NODE') or shutil.which('node')
        self.assertIsNotNone(node,'Set NODE to the Node executable for cross-language verification')
        cases = [dict(seed=seed,noise=noise) for seed,noise in [(0,0),(1,.03),(4294967295,.3),(seed_hash('orbit-1|2026-11-16|0'),.03)]]
        raw = subprocess.check_output([node,str(ROOT/'scripts/reference_predictions.cjs'),'--legacy'],input=json.dumps(cases),text=True)
        for case, ref in zip(cases,json.loads(raw)):
            scene = scenario(**case)
            for key in ['p0','p1','v','goal','frames']:
                np.testing.assert_allclose(scene[key],ref['scene'][key],rtol=0,atol=2e-14)
            np.testing.assert_allclose(self.model.encode(scene['frames']),ref['encoded'],atol=2e-13,rtol=0)
            best,costs,predicted = self.model.rank(scene['frames'],scene['goal_frame'])
            self.assertEqual(int(best),ref['ranked'][0]['index'])
            for plan in ref['ranked']:
                index=plan['index']
                np.testing.assert_allclose(predicted[index],plan['z'],atol=2e-12,rtol=0)
                self.assertAlmostEqual(float(costs[index]),plan['cost'],places=10)
                np.testing.assert_allclose(self.model.decode(predicted[index]),plan['xy'],atol=2e-12,rtol=0)
            np.testing.assert_allclose(rollout(scene['p1'],scene['v'],PLANS),ref['futures'],atol=1e-14,rtol=0)

    def test_benchmark_is_deterministic_and_oracle_reaches_goals(self):
        a=evaluate(self.model,[991],8)
        self.assertEqual(a,evaluate(self.model,[991],8))
        self.assertEqual(a['aggregate']['oracle']['hit_rate'],1.)
        for impulse in [.0175,.0525]:
            self.assertEqual(evaluate(self.model,[991],8,impulse=impulse)['aggregate']['oracle']['hit_rate'],1.)

    def test_current_deployment_matches_browser_loader_and_measured_checkpoint(self):
        release=json.loads((ROOT/'source/model-release.json').read_text())
        model=load_active_model()
        report=json.loads((ROOT/release['benchmark']).read_text())['models'][release['benchmarkModel']]
        for name in ['encoder','predictor','probe']:
            self.assertEqual(hashlib.sha256((ROOT/release['directory']/(name+'.npz')).read_bytes()).hexdigest(),
                             report[name+'_sha256'])
        node=os.environ.get('NODE') or shutil.which('node')
        cases=[{'seed':37,'noise':.03},{'seed':2144274839,'noise':.15}]
        reference=json.loads(subprocess.check_output([node,str(ROOT/'scripts/reference_predictions.cjs')],
                                                    input=json.dumps(cases),text=True))
        for case,row in zip(cases,reference):
            scene=scenario(**case);best,_,predictions=model.rank(scene['frames'],scene['goal_frame'])
            self.assertEqual(int(best),row['ranked'][0]['index'])
            for plan in row['ranked']:
                np.testing.assert_allclose(predictions[plan['index']],plan['z'],atol=2e-12,rtol=0)

    def test_wilson_interval_does_not_collapse_at_perfect_accuracy(self):
        result=summary(np.zeros(100))
        self.assertLess(result['hit_ci95_wilson'][0],1.)
        self.assertAlmostEqual(result['hit_ci95_wilson'][1],1.)

    def test_torch_forward_and_frozen_encoder(self):
        try:
            import torch
            from planning.training import Encoder,Predictor
        except ImportError: self.skipTest('Optional training dependencies not installed')
        torch.set_num_threads(2)
        encoder=Encoder(); predictor=Predictor(self.model.action['mean'],self.model.action['scale'])
        predictor.load_state_dict({k:torch.tensor(v,dtype=torch.float32) for k,v in self.model.action.items()})
        scene=scenario(37)
        frames=torch.tensor(scene['frames'],dtype=torch.float32)
        before={k:v.clone() for k,v in encoder.state_dict().items()}
        z=encoder(frames).unsqueeze(0)
        actions=torch.tensor([[1,0,-1]],dtype=torch.float32)
        prediction=predictor(z,actions)
        expected=self.model.predict_z(self.model.encode(scene['frames'])[None],np.array([[1,0,-1]]))
        np.testing.assert_allclose(prediction.detach().numpy(),expected,atol=3e-6,rtol=3e-6)
        prediction.square().mean().backward()
        self.assertTrue(all(p.grad is None for p in encoder.parameters()))
        self.assertTrue(any(p.grad is not None and p.grad.abs().sum()>0 for p in predictor.parameters()))
        for k,v in encoder.state_dict().items(): self.assertTrue(torch.equal(v,before[k]))

    def test_training_recipe_repeats_and_saves_best_validation_checkpoint(self):
        try:
            from planning.training import train
        except ImportError: self.skipTest('Optional training dependencies not installed')
        config={'seed':37,'validation_seed':38,'train_trajectories':128,'validation_trajectories':64,
                'steps':40,'batch_size':32,'learning_rate':.003,'weight_decay':.0001,'validate_every':20,'threads':2}
        with tempfile.TemporaryDirectory() as directory:
            a=train(config,Path(directory)/'first');b=train(config,Path(directory)/'second')
            self.assertEqual(a['predictor_sha256'],b['predictor_sha256'])
            self.assertEqual(a['history'],b['history'])
            self.assertLess(a['validation_normalized_feature_mse'],a['history'][0]['validation_normalized_feature_mse'])
            self.assertEqual(a['validation_normalized_feature_mse'],min(x['validation_normalized_feature_mse'] for x in a['history']))
            self.assertEqual(a['trainable_parameters'],23192)
            model=load_model(Path(directory)/'first/predictor.npz')
            scene=scenario(99)
            self.assertTrue(np.isfinite(model.rank(scene['frames'],scene['goal_frame'])[1]).all())


if __name__=='__main__': unittest.main()
