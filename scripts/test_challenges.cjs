const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const {C,pack,manifest}=require('./model_pack.cjs');
const X=require('../source/challenges.js');
const {languageUrl}=require('../source/navigation.js');
const today='2026-11-17';
const round={v:1,rules:C.RULES,model:manifest.modelId,kind:'round',seed:42,noise:3,actions:[-1,0,0]};
const daily={v:1,rules:C.RULES,model:manifest.modelId,kind:'daily',day:today,actions:[[0,0,0],[-1,0,1],[1,-1,0],[1,1,1],[-1,-1,-1]]};
const token=value=>Buffer.from(JSON.stringify(value)).toString('base64url');

test('friend links reproduce the exact scene and score across languages',()=>{
  for(const value of [round,{...round,kind:'hunt',noise:23,targetX:52},daily]){
    const encoded=X.encode(value),decoded=X.decode(encoded,manifest.modelId,today);
    assert.deepEqual(decoded,value);
    const expected=value.kind==='daily'?value.actions.map((a,i)=>C.outcome(C.roundScene(value.day,i),a)):[C.outcome(X.sceneFor(value),value.actions)];
    assert.deepEqual(X.replay(decoded),expected);
    if(value.kind!=='daily')assert.deepEqual(X.sceneFor(decoded),X.sceneFor(value));
    for(const lang of ['en','ru','zh']){
      const url=languageUrl('https://example.com/orbit/?challenge='+encoded+'#play','https://example.com/orbit/',lang);
      assert.deepEqual(X.decode(url.searchParams.get('challenge'),manifest.modelId,today),value);
    }
  }
});

test('untrusted challenge inputs cannot supply scores or invalid physics',()=>{
  for(const patch of [{score:9999},{actions:[-1,0,2]},{actions:[0,0]},{seed:-1},{seed:2**32},{seed:1.5},{noise:31},{noise:-1},{noise:.5},{targetX:7},{targetX:93},{targetX:NaN},{day:today},{v:2},{rules:'other'},{kind:'script'}]){
    assert.throws(()=>X.decode(token({...round,...patch}),manifest.modelId,today));
  }
  for(const patch of [{day:'2026-11-18'},{day:'2026-02-30'},{seed:42},{targetX:50},{actions:daily.actions.slice(1)},{actions:[...daily.actions,round.actions]}]){
    assert.throws(()=>X.decode(token({...daily,...patch}),manifest.modelId,today));
  }
  assert.throws(()=>X.decode(X.encode(round),'another-model',today),/model/);
  for(const bad of ['', 'a'.repeat(1801),'<>','e30','bm90LWpzb24'])assert.throws(()=>X.decode(bad,manifest.modelId,today));
});

test('a weakness requires a reachable human hit and an actual model miss',()=>{
  const cases=JSON.parse(fs.readFileSync('docs/assets/failures.json','utf8')).cases;
  const value={...round,kind:'hunt',seed:cases[0].seed,noise:Math.round(cases[0].noise*100)};
  const scene=X.sceneFor(value),ai=C.outcome(scene,C.rankPlans(pack,scene.frames,scene.goalFrame)[0].actions),human=C.oracle(scene);
  assert.equal(X.weakness(human,ai),true);
  assert.equal(X.weakness(ai,human),false);
  assert.equal(X.weakness(human,human),false);
  assert.equal(X.weakness(ai,ai),false);
  const impossible=[8,92].map(targetX=>X.sceneFor({...round,targetX})).find(s=>!C.oracle(s).hit);
  assert.ok(impossible);
  assert.ok(C.PLANS.every(a=>!C.outcome(impossible,a).hit));
});

function harness(){
  const nodes={};const node=id=>nodes[id]??={hidden:true,disabled:false,value:id==='noise'?'0.03':'',textContent:'',classList:{toggle(){}},setAttribute(){},scrollIntoView(){}};
  const ctx={C,pack,manifest,URL,Uint32Array,crypto:require('node:crypto').webcrypto,
    location:{href:'https://example.com/orbit/ru/'},history:{replaceState(a,b,url){ctx.location.href=String(url);}},
    params:new URLSearchParams(),navigationRoot:'https://example.com/orbit/',lang:'ru',today,day:today,
    mode:'daily',round:0,results:[],finished:false,revealed:false,scene:null,actions:[0,0,0],ranked:[],predicted:null,userOutcome:null,aiOutcome:null,anim:1,animationKey:0,
    $:node,txt(id,text){node(id).textContent=text;},T:(key,args)=>JSON.stringify({key,...args}),
    document:{querySelector:node},navigator:{},matchMedia:()=>({matches:true}),confirm:()=>false,
    renderStatus(){},renderResult(){},setLanguage(){},canSubmit:()=>true,clearFailure(){},newScene(){},switchMode(){},drawInputs(){},renderControls(){},renderInspection(){},draw(){},renderBoard(){},
    window:{OrbitChallenges:X,OrbitApp:{},addEventListener(){}}};
  vm.createContext(ctx);vm.runInContext(fs.readFileSync('source/play-ui.js','utf8'),ctx);ctx.newScene();return {ctx,node};
}

test('quick play, retry and friend replay keep daily results isolated',()=>{
  const {ctx,node}=harness();
  assert.equal(ctx.mode,'quick');assert.equal(ctx.scene.seed,42);
  assert.equal(ctx.canSubmit(),false);
  assert.throws(()=>ctx.challengePayload(),/unfinished/);
  ctx.actions=[-1,0,0];ctx.revealed=true;
  const value=ctx.challengePayload();assert.equal(value.kind,'round');
  const original=ctx.scene;ctx.resetAttempt(true);assert.equal(ctx.scene,original);assert.equal(ctx.revealed,false);
  assert.deepEqual(ctx.actions,[-1,0,0]);assert.equal(ctx.results.length,0);
  ctx.loadChallenge(X.encode(value));assert.equal(ctx.scene.seed,42);assert.equal(ctx.results.length,0);
  ctx.switchMode('daily');assert.equal(ctx.canSubmit(),true);assert.equal(ctx.window.OrbitApp.features.friend,null);
  ctx.results=[{you:100}];ctx.switchMode('hunt');assert.equal(ctx.mode,'daily');assert.equal(ctx.results.length,1);
  ctx.confirm=()=>true;ctx.switchMode('hunt');assert.equal(ctx.results.length,0);assert.equal(ctx.canSubmit(),false);
  node('hunt-noise').value='18';node('hunt-target').value='40';ctx.editHunt();
  assert.equal(ctx.scene.noise,.18);assert.equal(ctx.scene.goal[0],.4);
  ctx.revealed=true;const shared=ctx.challengePayload();ctx.loadChallenge(X.encode(shared));
  assert.equal(node('hunt-target').disabled,true);const fixed=ctx.scene;
  node('hunt-target').value='70';ctx.editHunt();assert.equal(ctx.scene,fixed);
});

test('old daily friend links replay but cannot enter the public leaderboard',()=>{
  const {ctx}=harness();
  ctx.loadChallenge(X.encode({...daily,day:'2026-10-01'}));
  assert.equal(ctx.mode,'daily');assert.equal(ctx.day,'2026-10-01');assert.equal(ctx.canSubmit(),false);
  ctx.loadChallenge(X.encode(daily));assert.equal(ctx.canSubmit(),true);
  ctx.finished=true;ctx.revealed=true;ctx.results=daily.actions.map(actions=>({actions,you:0}));
  assert.deepEqual(JSON.parse(JSON.stringify(ctx.challengePayload())),daily);
});
