"""New v0.4 training recipe for an action predictor over the frozen v0.3 encoder.

This reconstructs the architecture, not the unavailable historical training run.
Synthetic positions drive the renderer but are never targets for the predictor.
"""
import argparse
import hashlib
import json
import platform
import resource
import subprocess
import time
from pathlib import Path
import numpy as np
import torch
from torch import nn
from .model import ARTIFACTS, PLANS, load_arrays, render, rollout, tick


class Encoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(nn.Flatten(start_dim=-1), nn.Linear(576,128), nn.ReLU(),
                                 nn.Linear(128,64), nn.ReLU(), nn.Linear(64,8))
        self.load_state_dict({k:torch.tensor(v,dtype=torch.float32) for k,v in load_arrays(ARTIFACTS/'encoder.npz').items()})
        self.requires_grad_(False)
        self.eval()

    def forward(self, x): return self.net(x)


class Predictor(nn.Module):
    def __init__(self, mean, scale):
        super().__init__()
        self.register_buffer('mean', torch.as_tensor(mean, dtype=torch.float32).clone())
        self.register_buffer('scale', torch.as_tensor(scale, dtype=torch.float32).clone())
        self.net = nn.Sequential(nn.Linear(27,128), nn.ReLU(), nn.Linear(128,128), nn.ReLU(), nn.Linear(128,24))

    def forward(self, context, actions):
        q = (context-self.mean)/self.scale
        x = torch.cat([q[:,0],q[:,1],q[:,1]-q[:,0],actions],dim=-1)
        return (q[:,1,None]+self.net(x).reshape(-1,3,8))*self.scale+self.mean


@torch.no_grad()
def make_dataset(encoder, count, seed):
    """Independent trajectories, fixed NumPy RNG, chunked rendering to bound memory."""
    rng = np.random.default_rng(seed)
    p0 = rng.uniform(.16,.84,(count,2))
    v = rng.uniform(.02,.055,(count,2))*rng.choice([-1,1],size=(count,2))
    p1, v = tick(p0,v)
    actions = PLANS[rng.integers(0,27,count)]
    future = rollout(p1,v,actions)
    positions = np.concatenate([p0[:,None],p1[:,None],future],axis=1)
    amplitude = rng.uniform(.7,1.,count)
    embeddings = []
    for offset in range(0,count,512):
        p = positions[offset:offset+512]
        images = render(p,amplitude[offset:offset+512,None])
        # Same noise level at observation and future target frames. Independent noise per image.
        images = np.minimum(1.,images+rng.uniform(0,.03,images.shape))
        z = encoder(torch.tensor(images.reshape(-1,576),dtype=torch.float32))
        embeddings.append(z.reshape(-1,5,8))
    return torch.cat(embeddings), torch.tensor(actions,dtype=torch.float32)


def environment():
    cpu = platform.processor() or None
    if platform.system() == 'Darwin':
        try:
            cpu = subprocess.check_output(['sysctl','-n','machdep.cpu.brand_string'],text=True,stderr=subprocess.DEVNULL).strip()
        except (OSError, subprocess.CalledProcessError):
            cpu = None
    return {'python':platform.python_version(),'numpy':np.__version__,'torch':torch.__version__,
            'platform':platform.platform(),'cpu':cpu,'architecture':platform.machine(),
            'device':'cpu','threads':torch.get_num_threads()}


def train(config, out):
    out = Path(out)
    out.mkdir(parents=True,exist_ok=False)  # Never silently overwrite a completed experiment.
    torch.set_num_threads(config['threads'])
    torch.manual_seed(config['seed'])
    torch.use_deterministic_algorithms(True)
    started = time.perf_counter()
    encoder = Encoder()
    z, actions = make_dataset(encoder,config['train_trajectories'],config['seed'])
    valid_z, valid_a = make_dataset(encoder,config['validation_trajectories'],config['validation_seed'])
    mean = z[:,:2].reshape(-1,8).mean(0)
    scale = z[:,:2].reshape(-1,8).std(0,unbiased=False).clamp_min(1e-4)
    predictor = Predictor(mean,scale)
    optimizer = torch.optim.AdamW(predictor.parameters(),lr=config['learning_rate'],weight_decay=config['weight_decay'])
    history, best, best_step, checkpoint = [], float('inf'), None, None
    def loss(context, target, a):
        return (((predictor(context,a)-target)/predictor.scale)**2).mean()
    for step in range(config['steps']+1):
        if step:
            ids = torch.randint(len(z),(config['batch_size'],))
            optimizer.zero_grad(set_to_none=True)
            objective = loss(z[ids,:2],z[ids,2:],actions[ids])
            objective.backward(); optimizer.step()
        if step % config['validate_every'] == 0 or step == config['steps']:
            with torch.no_grad():
                validation = float(loss(valid_z[:,:2],valid_z[:,2:],valid_a))
            history.append({'step':step,'validation_normalized_feature_mse':validation})
            if validation < best:
                best, best_step = validation, step
                checkpoint = {k:v.detach().cpu().numpy().copy() for k,v in predictor.state_dict().items()}
            print(f'seed={config["seed"]} step={step} validation={validation:.6f}',flush=True)
    np.savez(out/'predictor.npz',**checkpoint)
    seconds = time.perf_counter()-started
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    mib = rss/(1024**2) if platform.system()=='Darwin' else rss/1024
    report = {'recipe':'v0.4 reconstructed action-predictor training; not original v0.3 provenance',
              'config':config,'environment':environment(),'selected_step':best_step,
              'validation_normalized_feature_mse':best,'elapsed_seconds_including_data':seconds,
              'process_peak_rss_mib':mib,'history':history,
              'encoder_sha256':hashlib.sha256((ARTIFACTS/'encoder.npz').read_bytes()).hexdigest(),
              'predictor_sha256':hashlib.sha256((out/'predictor.npz').read_bytes()).hexdigest(),
              'trainable_parameters':sum(p.numel() for p in predictor.parameters()),
              'frozen_encoder_parameters':sum(p.numel() for p in encoder.parameters())}
    (out/'training.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=Path('configs/train-actions.json'))
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--seed',type=int)
    args=parser.parse_args()
    config=json.loads(args.config.read_text())
    if args.seed is not None: config['seed']=args.seed
    train(config,args.out)


if __name__=='__main__': main()
