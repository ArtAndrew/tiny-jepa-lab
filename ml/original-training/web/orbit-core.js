/* MIT — deterministic game rules, image renderer, and learned planner.
   Simulation is used for the game and the explicit oracle ONLY.
   rankPlans() accepts pixels, never simulator state or true future trajectories. */
(function(root){'use strict';
const E=typeof module!=='undefined'&&module.exports?require('./engine.js'):root.JepaEngine;
const RULES='orbit-1', MARGIN=.08, IMPULSE=.035, MAX_SPEED=.14, HIT=.06;
const CFG={size:24,sigma:.042},PLANS=[];
for(const a of [-1,0,1])for(const b of [-1,0,1])for(const c of [-1,0,1])PLANS.push([a,b,c]);
function validActions(a){return Array.isArray(a)&&a.length===3&&a.every(x=>Number.isInteger(x)&&[-1,0,1].includes(x));}
function tick(p,v){p=p.map((x,i)=>x+v[i]);v=v.slice();for(let i=0;i<2;i++){if(p[i]<MARGIN){p[i]=2*MARGIN-p[i];v[i]=-v[i];}else if(p[i]>1-MARGIN){p[i]=2*(1-MARGIN)-p[i];v[i]=-v[i];}}return {p,v};}
function simulate(p,v,actions){if(!validActions(actions))throw Error('Invalid actions');p=p.slice();v=v.slice();const points=[p.slice()],ends=[];for(const a of actions){v[0]=Math.max(-MAX_SPEED,Math.min(MAX_SPEED,v[0]+a*IMPULSE));for(let j=0;j<2;j++){({p,v}=tick(p,v));points.push(p.slice());}ends.push(p.slice());}return {points,ends,final:p};}
function frame(p,amplitude=1,noise=0,random=()=>0){return E.render(CFG,p,amplitude,noise,random);}
function scenario(seed,noise=.03){const r=E.rng(seed);const p0=[.16+.68*r(),.16+.68*r()];const v=[.02+.035*r(),.02+.035*r()].map(x=>x*(r()>.5?1:-1));const first=tick(p0,v);const chosen=PLANS[Math.floor(r()*27)];const dest=simulate(first.p,first.v,chosen).final;const goal=[Math.max(.08,Math.min(.92,dest[0]+(r()-.5)*.036)),dest[1]];const amplitude=.7+.3*r();const frames=[frame(p0,amplitude,noise,r),frame(first.p,amplitude,noise,r)];return {seed:seed>>>0,p0,p1:first.p,v:first.v,goal,frames,goalFrame:frame(goal),noise};}
function hash(s){let h=2166136261;for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619);}return h>>>0;}
function validDay(s){return typeof s==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&!Number.isNaN(Date.parse(s+'T00:00:00Z'))&&new Date(s+'T00:00:00Z').toISOString().slice(0,10)===s;}
function roundScene(day,i){if(!validDay(day)||!Number.isInteger(i)||i<0||i>4)throw Error('Invalid daily round');return scenario(hash(RULES+'|'+day+'|'+i));}
function error(a,b){return Math.hypot(a[0]-b[0],a[1]-b[1]);}
function score(d){return Math.max(0,Math.round(1000*(1-d/.5)));}
function outcome(scene,actions){const s=simulate(scene.p1,scene.v,actions),distance=error(s.final,scene.goal);return {...s,distance,pointsScore:score(distance),hit:distance<=HIT};}
function predictZ(pack,z,actions){if(!validActions(actions))throw Error('Invalid actions');const w=pack.action,mean=w.mean.data,scale=w.scale.data;const q=z.map(x=>x.map((v,i)=>(v-mean[i])/scale[i]));let x=q[0].concat(q[1],q[1].map((v,i)=>v-q[0][i]),actions);x=E.linear(x,w,'net.0').map(v=>Math.max(0,v));x=E.linear(x,w,'net.2').map(v=>Math.max(0,v));x=E.linear(x,w,'net.4');return [0,1,2].map(k=>q[1].map((v,i)=>(v+x[k*8+i])*scale[i]+mean[i]));}
function encodeContext(pack,frames){return frames.map(f=>E.encode(pack.weights,f,true));}
function predict(pack,frames,actions){const z=predictZ(pack,encodeContext(pack,frames),actions);return {z,xy:z.map(a=>E.decode(pack,a))};}
function rankPlans(pack,frames,goalFrame){const z=encodeContext(pack,frames),goal=E.encode(pack.weights,goalFrame,true),scale=pack.action.scale.data;return PLANS.map((actions,index)=>{const predicted=predictZ(pack,z,actions);const cost=predicted[2].reduce((s,v,i)=>s+((v-goal[i])/scale[i])**2,0)/8;return {index,actions:actions.slice(),cost,z:predicted,xy:predicted.map(a=>E.decode(pack,a))};}).sort((a,b)=>a.cost-b.cost||a.index-b.index);}
function oracle(scene){return PLANS.map((actions,index)=>({actions,index,...outcome(scene,actions)})).sort((a,b)=>a.distance-b.distance||a.index-b.index)[0];}
function unpack(manifest,bytes){const f=new Float32Array(bytes);const pack={};for(const group of ['weights','probe','action']){pack[group]={};for(const [k,s] of Object.entries(manifest[group]))pack[group][k]={shape:s.shape,data:f.subarray(s.offset/4,s.offset/4+s.length)};}return pack;}
const api={RULES,PLANS,CFG,HIT,IMPULSE,MAX_SPEED,validActions,tick,simulate,frame,scenario,hash,validDay,roundScene,error,score,outcome,predictZ,encodeContext,predict,rankPlans,oracle,unpack};
if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.OrbitCore=api;
})(typeof globalThis!=='undefined'?globalThis:this);
