"""Train only the action predictor; the pretrained JEPA visual encoder stays frozen.
The optimization objective receives no coordinates, velocities, rewards or physics.
"""
from pathlib import Path
import argparse, json, time, platform, hashlib
import numpy as np
import torch
from planning.model import ActionWorld, ActionPredictor, load_encoder, save_predictor

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,default=Path('runs/action_jepa'))
    p.add_argument('--steps',type=int,default=5000)
    p.add_argument('--examples',type=int,default=65536)
    p.add_argument('--seed',type=int,default=31001)
    p.add_argument('--threads',type=int,default=2)
    p.add_argument('--encoder',type=Path,default=Path('artifacts/pretrained'))
    a=p.parse_args()
    if a.steps<1 or a.examples<256 or a.threads<1:p.error('Invalid training arguments')
    if (a.out/'predictor.npz').exists():p.error('Output already contains weights; choose a new --out')
    torch.set_num_threads(a.threads);torch.manual_seed(a.seed)
    encoder=load_encoder(a.encoder);world=ActionWorld(a.seed)
    t=time.monotonic();zs=[];acts=[]
    for i in range(0,a.examples,256):
        imgs,act,_,_=world.sample(min(256,a.examples-i))
        with torch.no_grad():zs.append(encoder(imgs.flatten(0,1)).reshape(-1,5,8))
        acts.append(act)
    z=torch.cat(zs);actions=torch.cat(acts)
    validation=ActionWorld(a.seed+1)
    im,va,_,_=validation.sample(2048)
    with torch.no_grad():vz=encoder(im.flatten(0,1)).reshape(-1,5,8)
    model=ActionPredictor()
    with torch.no_grad():
        model.mean.copy_(z.flatten(0,1).mean(0));model.scale.copy_(z.flatten(0,1).std(0).clamp_min(.01))
    opt=torch.optim.AdamW(model.parameters(),lr=.001,weight_decay=1e-4)
    schedule=torch.optim.lr_scheduler.CosineAnnealingLR(opt,a.steps,eta_min=.0001)
    history=[];best=float('inf');beststep=0
    print(f'Encoded {len(z)} independent trajectories in {time.monotonic()-t:.1f}s',flush=True)
    for step in range(1,a.steps+1):
        ids=torch.randint(len(z),(256,))
        pred=model(z[ids,:2],actions[ids])
        loss=((pred-z[ids,2:])/model.scale).square().mean()
        opt.zero_grad(set_to_none=True);loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),5.)
        opt.step();schedule.step()
        if step==1 or step%250==0 or step==a.steps:
            with torch.no_grad():vl=float(((model(vz[:,:2],va)-vz[:,2:])/model.scale).square().mean())
            row={'step':step,'train_loss':float(loss.detach()),'validation_loss':vl,'elapsed_seconds':time.monotonic()-t}
            history.append(row);print(json.dumps(row),flush=True)
            if vl<best:best=vl;beststep=step;save_predictor(model,a.out)
            (a.out/'history.json').write_text(json.dumps(history,indent=2))
    meta={'seed':a.seed,'examples':a.examples,'steps':a.steps,'selected_step':beststep,
          'validation_examples':2048,'validation_seed':a.seed+1,'selection':'minimum validation latent MSE',
          'elapsed_seconds':time.monotonic()-t,'torch':str(torch.__version__),'python':platform.python_version(),
          'device':'cpu','threads':a.threads,'encoder_sha256':hashlib.sha256((a.encoder/'model.npz').read_bytes()).hexdigest(),
          'predictor_parameters':sum(p.numel() for p in model.parameters()),
          'encoder_frozen':True,'coordinate_labels_used':False,
          'loss':'MSE of 3 predicted future embeddings, normalized by frozen feature std',
          'note':'Single training seed. Reuses v0.1 visual representation; this is not Meta V-JEPA.'}
    (a.out/'training.json').write_text(json.dumps(meta,indent=2))

if __name__=='__main__':main()
