const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const {languageUrl}=require('../source/navigation.js');
const {C,pack,manifest}=require('./model_pack.cjs');
const failures=JSON.parse(fs.readFileSync(path.join(__dirname,'../docs/assets/failures.json'),'utf8'));

test('language switching uses real routes and preserves game/share parameters',()=>{
  for(const root of ['https://artandrew.github.io/tiny-jepa-lab/','http://localhost:8765/']){
    const current=root+'ru/?lang=ru&day=2026-11-16&m=model&example=noise#play';
    for(const lang of ['zh','en','ru']){
      const url=languageUrl(current,root,lang);
      assert.equal(url.pathname,new URL(root).pathname+(lang==='en'?'':lang+'/'));
      assert.equal(url.searchParams.get('example'),'noise');
      assert.equal(url.searchParams.get('day'),'2026-11-16');
      assert.equal(url.searchParams.get('m'),'model');
      assert.equal(url.searchParams.has('lang'),false);
      assert.equal(url.hash,'#play');
    }
  }
});

test('published failure examples match actual model choices and real outcomes',()=>{
  assert.equal(failures.modelId,manifest.modelId);
  assert.equal(new Set(failures.cases.map(x=>x.seed)).size,3);
  for(const item of failures.cases){
    const scene=C.scenario(item.seed,item.noise),best=C.rankPlans(pack,scene.frames,scene.goalFrame)[0];
    const outcome=C.outcome(scene,best.actions);
    assert.deepEqual(item.actions,best.actions);
    assert.deepEqual(item.predicted,best.xy);
    assert.deepEqual(item.actual,outcome.points);
    assert.equal(item.actualDistance,outcome.distance);
    assert.equal(outcome.hit,false);
    assert.equal(C.oracle(scene).hit,true);
    if(item.id==='optimistic')assert.ok(item.predictedDistance<C.HIT);
    if(item.id==='noise'){
      const clean=C.scenario(item.seed,.03);
      assert.equal(C.outcome(clean,C.rankPlans(pack,clean.frames,clean.goalFrame)[0].actions).hit,true);
      assert.deepEqual(clean.goal,scene.goal);
      assert.deepEqual(clean.p1,scene.p1);
    }
  }
});

test('opening examples respects daily-progress cancellation and cannot add a daily score',()=>{
  const nodes={};const node=id=>nodes[id]??=(id==='orbit-failures'?{textContent:JSON.stringify(failures)}:{hidden:true,scrollIntoView(){}});
  const context={URL,C,pack,location:{href:'https://example.com/ru/'},history:{replaceState(a,b,url){context.location.href=String(url);}},
    $:node,txt(){},T:k=>k,mode:'daily',results:[{you:123}],ranked:[],actions:[],scene:null,predicted:null,
    switchMode(){if(context.allow)context.mode='lab';},newScene(){context.results=[];},
    drawInputs(){},renderControls(){},renderStatus(){},renderInspection(){},draw(){},
    matchMedia:()=>({matches:true})};
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../source/failures-ui.js'),'utf8'),context);
  vm.runInContext('renderFailures=()=>{}',context);
  context.openFailure('optimistic',false);
  assert.equal(context.mode,'daily');assert.equal(context.results.length,1);
  context.allow=true;context.openFailure('optimistic',false);
  assert.equal(context.mode,'lab');assert.equal(context.results.length,0);
  assert.equal(context.scene.seed,failures.cases[0].seed);
  assert.deepEqual(context.actions,failures.cases[0].actions);
  assert.ok(context.predicted);assert.equal(new URL(context.location.href).searchParams.get('example'),'optimistic');
});
