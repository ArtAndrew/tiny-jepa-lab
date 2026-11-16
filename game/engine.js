/* Actual inference from trained weights. No network access, libraries or physics
   in the predictor. The simulator is separate and only makes input/ground truth. */
(function(root) {
'use strict';
function linear(x, state, name) {
  const w=state[name+'.weight'], b=state[name+'.bias'].data;
  const rows=w.shape[0], cols=w.shape[1], out=new Array(rows);
  if(x.length!==cols) throw Error('Layer shape mismatch: '+name);
  for(let i=0;i<rows;i++){let v=b[i], k=i*cols; for(let j=0;j<cols;j++) v+=w.data[k+j]*x[j]; out[i]=v;}
  return out;
}
function relu(x){return x.map(v=>Math.max(0,v));}
function encode(weights, image, teacher=false) {
  const prefix=(teacher?'teacher':'encoder')+'.net.';
  let z=relu(linear(image,weights,prefix+'1'));
  z=relu(linear(z,weights,prefix+'3'));
  return linear(z,weights,prefix+'5');
}
function predict(pack, context, h) {
  if(context.length!==2 || !Number.isInteger(h) || h<1 || h>pack.config.max_horizon)
    throw Error('Expected two context frames and a valid integer horizon');
  const z0=encode(pack.weights,context[0]), z1=encode(pack.weights,context[1]);
  const hot=Array(pack.config.max_horizon).fill(0); hot[h-1]=1;
  const inp=z0.concat(z1,z1.map((v,i)=>v-z0[i]),hot);
  let p=relu(linear(inp,pack.weights,'predictor.0'));
  p=relu(linear(p,pack.weights,'predictor.2'));
  p=linear(p,pack.weights,'predictor.4');
  return p.map((v,i)=>v+z1[i]);
}
function decode(pack,z) {
  const s=pack.probe;
  let x=z.map((v,i)=>(v-s.mean.data[i])/s.scale.data[i]);
  x=relu(linear(x,s,'net.0')); x=relu(linear(x,s,'net.2'));
  return linear(x,s,'net.4').map(v=>1/(1+Math.exp(-v)));
}
function reflect(x,margin){const w=1-2*margin; const r=((x-margin)%(2*w)+2*w)%(2*w);return margin+w-Math.abs(r-w);}
function rng(seed){let a=seed>>>0;return ()=>{a=(a+0x6D2B79F5)|0;let t=Math.imul(a^(a>>>15),1|a);t^=t+Math.imul(t^(t>>>7),61|t);return ((t^(t>>>14))>>>0)/4294967296;};}
function render(cfg,xy,amplitude,noise,random){
  const out=[];for(let y=0;y<cfg.size;y++)for(let x=0;x<cfg.size;x++){
    const d=(x/(cfg.size-1)-xy[0])**2+(y/(cfg.size-1)-xy[1])**2;
    out.push(Math.min(1,amplitude*Math.exp(-d/(2*cfg.sigma**2))+noise*random()));
  }return out;
}
function sample(cfg,seed,h,noise,speed){
  const random=rng(seed),p=[0,0].map(()=>cfg.margin+(1-2*cfg.margin)*random());
  const v=[0,0].map(()=>(cfg.min_speed+(cfg.max_speed-cfg.min_speed)*random())*speed);
  for(let i=0;i<2;i++)v[i]*=random()>.5?1:-1;
  const positions=[0,1,1+h].map(t=>p.map((x,i)=>reflect(x+v[i]*t,cfg.margin)));
  const amplitude=.7+.3*random();
  const frames=positions.map(pos=>render(cfg,pos,amplitude,noise,random));
  return {context:frames.slice(0,2),future:frames[2],positions,p,v,amplitude};
}
function centroid(frame,size){let sum=0,x=0,y=0;for(let i=0;i<frame.length;i++){const m=Math.max(0,frame[i]-.2);sum+=m;x+=(i%size)/(size-1)*m;y+=Math.floor(i/size)/(size-1)*m;}return [x/Math.max(sum,1e-8),y/Math.max(sum,1e-8)];}
function distance(a,b,size){return Math.hypot(a[0]-b[0],a[1]-b[1])*(size-1);}
const api={linear,encode,predict,decode,reflect,rng,render,sample,centroid,distance};
if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.JepaEngine=api;
})(typeof globalThis!=='undefined'?globalThis:this);
