'use strict';
const fs=require('node:fs');
const path=require('node:path');
const {C,pack,manifest}=require('./model_pack.cjs');
function inspect(seed,noise){
  const scene=C.scenario(seed,noise), best=C.rankPlans(pack,scene.frames,scene.goalFrame)[0];
  const actual=C.outcome(scene,best.actions), predictedDistance=C.error(best.xy[2],scene.goal);
  return {scene,best,actual,predictedDistance};
}
function save(kind,result){
  const {scene,best,actual,predictedDistance}=result;
  return {id:kind,seed:scene.seed,noise:scene.noise,actions:best.actions,goal:scene.goal,start:scene.p1,
    predicted:best.xy,actual:actual.points,actualDistance:actual.distance,predictedDistance,
    oracleActions:C.oracle(scene).actions,oracleDistance:C.oracle(scene).distance};
}
const chosen={};
for(let i=0;i<1500 && Object.keys(chosen).length<3;i++){
  const seed=C.hash('orbit-failures-v04|'+i), normal=inspect(seed,.03);
  if(!chosen.optimistic && normal.predictedDistance<C.HIT && normal.actual.distance>.12)
    chosen.optimistic=save('optimistic',normal);
  const p=normal.actual.points;
  const bounce=p.slice(1,-1).some((point,j)=>[0,1].some(axis=>(point[axis]-p[j][axis])*(p[j+2][axis]-point[axis])<0));
  if(!chosen.bounce && bounce && normal.actual.distance>.1 && seed!==chosen.optimistic?.seed)chosen.bounce=save('bounce',normal);
  if(!chosen.noise && normal.actual.hit){
    const noisy=inspect(seed,.2);
    if(noisy.actual.distance>.15){chosen.noise=save('noise',noisy);chosen.noise.cleanDistance=normal.actual.distance;}
  }
}
if(Object.keys(chosen).length!==3)throw Error('Could not find the documented failure categories');
const output={modelId:manifest.modelId,selection:'First matching cases in orbit-failures-v04|i, i=0..1499; bounce excludes the optimistic case. Selected illustrations, not a representative benchmark.',cases:['optimistic','bounce','noise'].map(id=>chosen[id])};
fs.mkdirSync(path.join(__dirname,'../docs/assets'),{recursive:true});
fs.writeFileSync(path.join(__dirname,'../docs/assets/failures.json'),JSON.stringify(output,null,2)+'\n');
console.log(JSON.stringify(output.cases.map(c=>({id:c.id,seed:c.seed,actualDistance:c.actualDistance,predictedDistance:c.predictedDistance}))));
