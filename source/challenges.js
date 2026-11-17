/* MIT. Portable challenges contain inputs and actions, never trusted scores. */
(function(root){'use strict';
const C=typeof module!=='undefined'&&module.exports?require('../game/orbit.js'):root.OrbitCore;
function validate(value,model,today=new Date().toISOString().slice(0,10)){
  if(!value||typeof value!=='object'||Array.isArray(value))throw Error('invalid');
  const allowed=['v','rules','model','kind','day','seed','noise','targetX','actions'];
  if(Object.keys(value).some(k=>!allowed.includes(k))||value.v!==1||value.rules!==C.RULES)throw Error('invalid');
  if(typeof value.model!=='string'||value.model!==model)throw Error('model');
  if(!['round','hunt','daily'].includes(value.kind))throw Error('invalid');
  const out={v:1,rules:C.RULES,model,kind:value.kind};
  if(value.kind==='daily'){
    if(!C.validDay(value.day)||value.day>today||['seed','noise','targetX'].some(k=>k in value))throw Error('invalid');
    if(!Array.isArray(value.actions)||value.actions.length!==5||!value.actions.every(C.validActions))throw Error('invalid');
    out.day=value.day;out.actions=value.actions.map(a=>a.slice());
  }else{
    if('day' in value||!Number.isInteger(value.seed)||value.seed<0||value.seed>0xffffffff||!Number.isInteger(value.noise)||value.noise<0||value.noise>30||!C.validActions(value.actions))throw Error('invalid');
    Object.assign(out,{seed:value.seed,noise:value.noise,actions:value.actions.slice()});
    if('targetX' in value){if(!Number.isInteger(value.targetX)||value.targetX<8||value.targetX>92)throw Error('invalid');out.targetX=value.targetX;}
  }
  return out;
}
function encode(value){
  const text=JSON.stringify(validate(value,value.model));
  return (typeof Buffer!=='undefined'?Buffer.from(text).toString('base64'):btoa(text)).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
}
function decode(token,model,today){
  if(typeof token!=='string'||token.length>1800||!token.length||!/^[A-Za-z0-9_-]+$/.test(token))throw Error('invalid');
  let value;try{const b=token.replace(/-/g,'+').replace(/_/g,'/');value=JSON.parse(typeof Buffer!=='undefined'?Buffer.from(b,'base64').toString('utf8'):atob(b));}catch{throw Error('invalid');}
  return validate(value,model,today);
}
function sceneFor(value){
  const s=C.scenario(value.seed,value.noise/100);
  if(value.targetX!==undefined){s.goal=[value.targetX/100,s.goal[1]];s.goalFrame=C.frame(s.goal);s.targetX=value.targetX;}
  return s;
}
function replay(value){
  return value.kind==='daily'?value.actions.map((a,i)=>C.outcome(C.roundScene(value.day,i),a)):[C.outcome(sceneFor(value),value.actions)];
}
function weakness(player,ai){return player.hit&&!ai.hit;}
const api={validate,encode,decode,sceneFor,replay,weakness};
if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.OrbitChallenges=api;
})(typeof globalThis!=='undefined'?globalThis:this);
