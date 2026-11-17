"""Independence and deterministic replay of the complete learning pipeline."""
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
from planning.model import ROOT, load_model, scenario


@unittest.skipUnless(importlib.util.find_spec('torch'), 'Install training dependencies')
class FromScratchTests(unittest.TestCase):
    def test_variance_regularization_penalizes_collapse_and_backpropagates(self):
        import torch
        from planning.from_scratch import representation_loss
        from planning.training import Encoder
        config=json.loads((ROOT/'configs/train-from-scratch.json').read_text())['encoder']
        torch.manual_seed(7)
        a=torch.randn(128,8,requires_grad=True);b=(a.detach()+.01*torch.randn(128,8)).requires_grad_()
        good,_=representation_loss(a,b,config)
        collapsed,_=representation_loss(torch.zeros_like(a),torch.zeros_like(b),config)
        self.assertGreater(float(collapsed),float(good))
        good.backward();self.assertGreater(float(a.grad.abs().sum()),0);self.assertGreater(float(b.grad.abs().sum()),0)
        encoder=Encoder(weights=None,trainable=True)
        self.assertTrue(all(p.requires_grad for p in encoder.parameters()))

    def test_clean_room_training_repeats_without_any_pretrained_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            shutil.copytree(ROOT/'planning',root/'planning',ignore=shutil.ignore_patterns('__pycache__'))
            self.assertFalse((root/'artifacts').exists())
            config=json.loads((ROOT/'configs/train-from-scratch.json').read_text())
            for stage in ['encoder','action','probe']:
                c=config[stage];c.update(steps=12,batch_size=32,validate_every=6)
                for key in list(c):
                    if key in ['train_images','train_trajectories']:c[key]=128
                    if key in ['validation_images','validation_trajectories','test_images']:c[key]=64
            (root/'config.json').write_text(json.dumps(config))
            env=dict(os.environ,OPENBLAS_NUM_THREADS='1',PYTHONPATH=str(root))
            for name in ['first','repeat']:
                subprocess.run([sys.executable,'-m','planning.from_scratch','--config','config.json','--out',name],
                               cwd=root,env=env,check=True,capture_output=True,text=True,timeout=120)
            a=json.loads((root/'first/training.json').read_text());b=json.loads((root/'repeat/training.json').read_text())
            self.assertFalse(a['pretrained_weights_read'])
            self.assertEqual(a['artifacts_sha256'],b['artifacts_sha256'])
            self.assertEqual(a['browser_model_id'],b['browser_model_id'])
            encoder=json.loads((root/'first/encoder-training/training.json').read_text())
            self.assertNotEqual(encoder['initial_state_sha256'],encoder['final_state_sha256'])
            self.assertFalse(encoder['coordinate_labels_used'])
            subprocess.run([sys.executable,'-m','planning.benchmark','--no-released','--model-dirs','first',
                            '--per-seed','8','--seeds','99017','--conditions','normal','--out','evaluation.json'],
                           cwd=root,env=env,check=True,capture_output=True,text=True,timeout=60)
            result=json.loads((root/'evaluation.json').read_text())
            self.assertEqual(result['models']['first']['conditions']['normal']['aggregate']['oracle']['hit_rate'],1.)
            model=load_model(model_dir=root/'first');scene=scenario(37)
            with self.assertRaisesRegex(ValueError,'model_dir'):
                load_model(root/'first/predictor.npz')
            before=model.rank(scene['frames'],scene['goal_frame'])
            model.probe={key:np.zeros_like(value) for key,value in model.probe.items()}
            after=model.rank(scene['frames'],scene['goal_frame'])
            np.testing.assert_array_equal(before[1],after[1])
            self.assertEqual(before[0],after[0])
            node=os.environ.get('NODE') or shutil.which('node')
            self.assertIsNotNone(node)
            raw=subprocess.check_output([node,str(ROOT/'scripts/reference_predictions.cjs'),str(root/'first')],
                                        input=json.dumps([{'seed':37,'noise':.03}]),text=True)
            reference=json.loads(raw)[0]
            self.assertEqual(int(before[0]),reference['ranked'][0]['index'])
            for plan in reference['ranked']:
                np.testing.assert_allclose(before[2][plan['index']],plan['z'],atol=3e-12,rtol=0)

    def test_published_scratch_bundles_match_javascript(self):
        node=os.environ.get('NODE') or shutil.which('node')
        self.assertIsNotNone(node)
        for directory in sorted((ROOT/'experiments').iterdir()):
            if not (directory/'model.bin').exists():continue
            if not (directory/'training.json').exists():continue
            model=load_model(model_dir=directory)
            cases=[{'seed':seed,'noise':noise} for seed,noise in [(0,0),(37,.03),(4294967295,.15)]]
            raw=subprocess.check_output([node,str(ROOT/'scripts/reference_predictions.cjs'),str(directory)],
                                        input=json.dumps(cases),text=True)
            for case,reference in zip(cases,json.loads(raw)):
                scene=scenario(**case);best,costs,z=model.rank(scene['frames'],scene['goal_frame'])
                self.assertEqual(int(best),reference['ranked'][0]['index'])
                for plan in reference['ranked']:
                    np.testing.assert_allclose(z[plan['index']],plan['z'],atol=5e-12,rtol=0)
                    np.testing.assert_allclose(model.decode(z[plan['index']]),plan['xy'],atol=5e-12,rtol=0)


if __name__=='__main__':unittest.main()
