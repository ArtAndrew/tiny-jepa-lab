"""Train every ORBIT tensor from random initialization, without legacy weights.

Stage 1: self-supervised VICReg-style image representations (not Meta I-JEPA).
Stage 2: action-conditioned future-feature prediction over the frozen encoder.
Stage 3: a supervised coordinate probe for display only, outside planning.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time
import numpy as np
import torch
from torch import nn
from .model import load_model, render
from .training import Encoder, environment, train as train_actions


def save_state(module, path):
    np.savez(path, **{k:v.detach().cpu().numpy() for k,v in module.state_dict().items()})
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def state_digest(module):
    digest = hashlib.sha256()
    for name, value in sorted(module.state_dict().items()):
        digest.update(name.encode())
        digest.update(value.detach().cpu().numpy().astype('<f4').tobytes())
    return digest.hexdigest()


def initialize(seed, threads):
    torch.set_num_threads(threads)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)


def base_images(count, seed):
    """Return pixels only; positions are used solely inside the renderer."""
    rng = np.random.default_rng(seed)
    positions = rng.uniform(.08, .92, (count, 2))
    return torch.cat([torch.from_numpy(render(positions[i:i+512]).astype(np.float32))
                      for i in range(0, count, 512)])


def augment(images, generator, noise=.03):
    amplitude = .7 + .3 * torch.rand((len(images), 1), generator=generator)
    return (images*amplitude + noise*torch.rand(images.shape, generator=generator)).clamp(max=1)


def representation_loss(a, b, config):
    """Variance and covariance penalties prevent a constant-vector solution.

    Implements the VICReg objective on the eight encoder features directly;
    no projector, labels, EMA teacher, pixel decoder or pretrained network.
    """
    invariance = (a-b).square().mean()
    centered = [z-z.mean(0) for z in (a,b)]
    covariances = [z.T@z/(len(z)-1) for z in centered]
    variances = [torch.diag(cov) for cov in covariances]
    stds = [(v+1e-4).sqrt() for v in variances]
    variance = sum((1-std).clamp(min=0).mean() for std in stds)/2
    covariance = sum((cov-torch.diag(torch.diag(cov))).square().sum()/cov.shape[0] for cov in covariances)
    loss = config['invariance_weight']*invariance + config['variance_weight']*variance + config['covariance_weight']*covariance
    return loss, {'invariance':float(invariance.detach()),'variance_penalty':float(variance.detach()),
                  'covariance_penalty':float(covariance.detach()),'min_feature_std':float(stds[0].min().detach())}


@torch.no_grad()
def representation_validation(encoder, views, config):
    a,b = [encoder(view) for view in views]
    objective, stats = representation_loss(a,b,config)
    eigenvalues = torch.linalg.eigvalsh(torch.cov(a.T)).clamp(min=0)
    mass = eigenvalues/eigenvalues.sum().clamp(min=1e-12)
    effective_rank = torch.exp(-(mass*mass.clamp(min=1e-12).log()).sum())
    stats.update(objective=float(objective),effective_rank=float(effective_rank))
    return stats


def pretrain_encoder(config, out, seed, threads):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    initialize(seed,threads);started=time.perf_counter()
    encoder=Encoder(weights=None,trainable=True)
    initial_digest=state_digest(encoder)
    images=base_images(config['train_images'],seed+1000)
    validation=base_images(config['validation_images'],config['validation_seed'])
    validation_rng=torch.Generator().manual_seed(config['validation_seed']+1)
    views=[augment(validation,validation_rng) for _ in range(2)]
    rng=torch.Generator().manual_seed(seed+2000)
    optimizer=torch.optim.AdamW(encoder.parameters(),lr=config['learning_rate'],weight_decay=config['weight_decay'])
    history=[];best=float('inf');best_state=None;best_step=None
    for step in range(config['steps']+1):
        if step:
            batch=images[torch.randint(len(images),(config['batch_size'],),generator=rng)]
            a,b=[encoder(augment(batch,rng)) for _ in range(2)]
            objective,_=representation_loss(a,b,config)
            optimizer.zero_grad(set_to_none=True);objective.backward();optimizer.step()
        if step%config['validate_every']==0 or step==config['steps']:
            stats=representation_validation(encoder,views,config)
            history.append(dict(step=step,**stats))
            if stats['objective']<best:
                best=stats['objective'];best_step=step
                best_state={k:v.detach().clone() for k,v in encoder.state_dict().items()}
            print(f'encoder seed={seed} step={step} val={stats["objective"]:.5f} std_min={stats["min_feature_std"]:.3f} rank={stats["effective_rank"]:.2f}',flush=True)
    encoder.load_state_dict(best_state)
    weights_sha=save_state(encoder,out/'encoder.npz')
    report={'method':'VICReg-style self-supervised encoder; direct 8D features, no projector',
            'seed':seed,'config':config,'initial_state_sha256':initial_digest,'final_state_sha256':state_digest(encoder),
            'weights_sha256':weights_sha,'selected_step':best_step,'history':history,
            'selected_validation':representation_validation(encoder,views,config),
            'coordinate_labels_used':False,'pretrained_weights_read':False,
            'elapsed_seconds':time.perf_counter()-started,'environment':environment()}
    (out/'training.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report


class Probe(nn.Module):
    def __init__(self,mean,scale):
        super().__init__()
        self.register_buffer('mean',mean.clone())
        self.register_buffer('scale',scale.clone())
        self.net=nn.Sequential(nn.Linear(8,64),nn.ReLU(),nn.Linear(64,64),nn.ReLU(),nn.Linear(64,2))

    def forward(self,z):return torch.sigmoid(self.net((z-self.mean)/self.scale))


@torch.no_grad()
def probe_data(encoder,count,seed):
    """Labeled coordinates are confined to the separately trained display probe."""
    rng=np.random.default_rng(seed);positions=rng.uniform(.08,.92,(count,2));features=[]
    for offset in range(0,count,512):
        p=positions[offset:offset+512]
        images=render(p,rng.uniform(.7,1.,len(p)))
        images=np.minimum(1.,images+rng.uniform(0,.03,images.shape))
        features.append(encoder(torch.from_numpy(images.astype(np.float32))))
    return torch.cat(features),torch.from_numpy(positions.astype(np.float32))


def train_probe(config,out,encoder_path,seed,threads):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    initialize(seed,threads);started=time.perf_counter()
    encoder=Encoder(encoder_path)
    z,xy=probe_data(encoder,config['train_images'],seed+1000)
    vz,vxy=probe_data(encoder,config['validation_images'],config['validation_seed'])
    probe=Probe(z.mean(0),z.std(0,unbiased=False).clamp_min(1e-4))
    initial_digest=state_digest(probe)
    optimizer=torch.optim.AdamW(probe.parameters(),lr=config['learning_rate'],weight_decay=config['weight_decay'])
    history=[];best=float('inf');best_state=None;best_step=None
    for step in range(config['steps']+1):
        if step:
            ids=torch.randint(len(z),(config['batch_size'],))
            loss=(probe(z[ids])-xy[ids]).square().mean()
            optimizer.zero_grad(set_to_none=True);loss.backward();optimizer.step()
        if step%config['validate_every']==0 or step==config['steps']:
            with torch.no_grad():validation=float((probe(vz)-vxy).square().mean())
            history.append({'step':step,'coordinate_mse':validation})
            if validation<best:
                best=validation;best_step=step;best_state={k:v.detach().clone() for k,v in probe.state_dict().items()}
            print(f'probe seed={seed} step={step} validation={validation:.7f}',flush=True)
    probe.load_state_dict(best_state)
    tz,txy=probe_data(encoder,config['test_images'],config['test_seed'])
    with torch.no_grad():test_error=float(torch.linalg.vector_norm(probe(tz)-txy,dim=-1).mean()*23)
    weights_sha=save_state(probe,out/'probe.npz')
    report={'method':'Supervised coordinate probe, display only; no gradients into encoder or planner',
            'seed':seed,'config':config,'initial_state_sha256':initial_digest,'weights_sha256':weights_sha,
            'selected_step':best_step,'history':history,'test_mean_distance_px':test_error,
            'elapsed_seconds':time.perf_counter()-started,'coordinate_labels_used':True,'pretrained_weights_read':False}
    (out/'training.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report


def export_browser_bundle(directory):
    """Create a new standalone JS model pack using only this run's three NPZs."""
    directory=Path(directory);manifest={};chunks=[];offset=0
    for group,name in [('weights','encoder'),('probe','probe'),('action','predictor')]:
        manifest[group]={}
        with np.load(directory/(name+'.npz'),allow_pickle=False) as state:
            for key in sorted(state.files):
                tensor=state[key].astype('<f4');binary=tensor.tobytes()
                browser_key='teacher.'+key if group=='weights' else key
                manifest[group][browser_key]={'shape':list(tensor.shape),'offset':offset,'length':int(tensor.size)}
                chunks.append(binary);offset+=len(binary)
    binary=b''.join(chunks);digest=hashlib.sha256(binary).hexdigest()
    manifest.update(version=1,rules='orbit-1',sha256=digest,modelId=digest[:12],byteLength=len(binary),binary='model.bin')
    (directory/'model.bin').write_bytes(binary)
    (directory/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


class Tee:
    def __init__(self,*streams):self.streams=streams
    def write(self,text):
        for stream in self.streams:stream.write(text)
    def flush(self):
        for stream in self.streams:stream.flush()


def train_pipeline(config,out):
    import contextlib
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    with (out/'training.log').open('w') as log,contextlib.redirect_stdout(Tee(sys.stdout,log)):
        started=time.perf_counter();seed=config['seed'];threads=config['threads']
        encoder=pretrain_encoder(config['encoder'],out/'encoder-training',seed,threads)
        shutil.copyfile(out/'encoder-training/encoder.npz',out/'encoder.npz')
        action_config=dict(config['action'],seed=seed+100000,threads=threads)
        action=train_actions(action_config,out/'action-training',encoder_path=out/'encoder.npz')
        shutil.copyfile(out/'action-training/predictor.npz',out/'predictor.npz')
        probe=train_probe(config['probe'],out/'probe-training',out/'encoder.npz',seed+200000,threads)
        shutil.copyfile(out/'probe-training/probe.npz',out/'probe.npz')
        manifest=export_browser_bundle(out)
        report={'recipe':'orbit-v05-from-scratch','config':config,'environment':environment(),
                'pretrained_weights_read':False,'stages':['self-supervised encoder','action predictor','supervised display probe'],
                'encoder_selected_step':encoder['selected_step'],'action_selected_step':action['selected_step'],
                'probe_selected_step':probe['selected_step'],'probe_test_mean_distance_px':probe['test_mean_distance_px'],
                'browser_model_id':manifest['modelId'],'elapsed_seconds':time.perf_counter()-started,
                'artifacts_sha256':{name:hashlib.sha256((out/name).read_bytes()).hexdigest()
                                    for name in ['encoder.npz','predictor.npz','probe.npz','model.bin']}}
        (out/'training.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
        print('Complete from-scratch bundle:',manifest['modelId'],flush=True)
        return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=Path('configs/train-from-scratch.json'))
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--seed',type=int)
    args=parser.parse_args();config=json.loads(args.config.read_text())
    if args.seed is not None:config['seed']=args.seed
    train_pipeline(config,args.out)


if __name__=='__main__':main()
