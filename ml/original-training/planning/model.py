"""Frozen visual encoder + a newly trained action-conditioned JEPA-style predictor.
Only images and action sequences enter the learner. Positions live in the simulator.
"""
from __future__ import annotations
from pathlib import Path
import itertools
import json
import numpy as np
import torch
from torch import nn
from tinyjepa.core import load_model

PLANS = torch.tensor(list(itertools.product((-1., 0., 1.), repeat=3)))
MARGIN = .08
IMPULSE = .035
MAX_SPEED = .14
TICKS = 2
RULES = 'orbit-1'

class ActionPredictor(nn.Module):
    def __init__(self, dim: int = 8):
        super().__init__()
        self.register_buffer('mean', torch.zeros(dim))
        self.register_buffer('scale', torch.ones(dim))
        self.net = nn.Sequential(nn.Linear(3*dim+3,128), nn.ReLU(),
                                 nn.Linear(128,128), nn.ReLU(), nn.Linear(128,3*dim))
    def forward(self, z: torch.Tensor, actions: torch.Tensor) -> torch.Tensor:
        if z.ndim != 3 or z.shape[1:] != (2,8) or actions.shape != (z.shape[0],3):
            raise ValueError('Expected context [B,2,8] and actions [B,3]')
        q = (z-self.mean)/self.scale
        x = torch.cat([q[:,0],q[:,1],q[:,1]-q[:,0],actions],-1)
        out = q[:,1,None,:] + self.net(x).reshape(-1,3,8)
        return out*self.scale+self.mean

@torch.no_grad()
def tick(p, v):
    p = p+v
    low, high = p<MARGIN, p>1-MARGIN
    p = torch.where(low, 2*MARGIN-p, p)
    p = torch.where(high, 2*(1-MARGIN)-p, p)
    v = torch.where(low|high, -v, v)
    return p,v

@torch.no_grad()
def rollout(p, v, actions):
    p,v = p.clone(),v.clone()
    result=[]
    for k in range(3):
        v[:,0] = (v[:,0]+actions[:,k]*IMPULSE).clamp(-MAX_SPEED,MAX_SPEED)
        for _ in range(TICKS): p,v=tick(p,v)
        result.append(p.clone())
    return torch.stack(result,1)

class ActionWorld:
    def __init__(self, seed=31001):
        self.g=torch.Generator().manual_seed(seed)
        axis=torch.linspace(0,1,24)
        yy,xx=torch.meshgrid(axis,axis,indexing='ij')
        self.grid=torch.stack([xx,yy],-1)
    @torch.no_grad()
    def render(self,xy,amplitude=None,noise=.03):
        n=xy.shape[0]
        if amplitude is None: amplitude=.7+.3*torch.rand(n,generator=self.g)
        d=((self.grid[None]-xy[:,None,None])**2).sum(-1)
        return (amplitude[:,None,None]*torch.exp(-d/(2*.042**2))+
                noise*torch.rand(n,24,24,generator=self.g)).clamp(0,1)
    @torch.no_grad()
    def sample(self,n):
        # Initial positions avoid an ambiguous, unobserved bounce between input frames.
        p0=.16+.68*torch.rand(n,2,generator=self.g)
        v=(.02+.035*torch.rand(n,2,generator=self.g))*torch.where(torch.rand(n,2,generator=self.g)>.5,1.,-1.)
        p1,v=tick(p0,v)
        actions=torch.randint(0,3,(n,3),generator=self.g).float()-1
        future=rollout(p1,v,actions)
        positions=torch.cat([p0[:,None],p1[:,None],future],1)
        amp=.7+.3*torch.rand(n,1,generator=self.g).expand(-1,5)
        images=self.render(positions.reshape(-1,2),amp.reshape(-1)).reshape(n,5,24,24)
        return images,actions,positions,v

def save_predictor(model, out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(out/'predictor.npz',**{k:v.detach().cpu().numpy() for k,v in model.state_dict().items()})

def load_predictor(path):
    model=ActionPredictor()
    with np.load(Path(path)/'predictor.npz',allow_pickle=False) as f:
        model.load_state_dict({k:torch.from_numpy(f[k].copy()) for k in f.files})
    return model.eval().requires_grad_(False)

def load_encoder(path='artifacts/pretrained'):
    return load_model(path).teacher.eval().requires_grad_(False)
