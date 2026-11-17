/* One-round play, reproducible friend replays, and editable weakness experiments. */
const X=window.OrbitChallenges;
let friendChallenge=null,friendScores=[],pendingRound=null;
const baseStatus=renderStatus,baseResult=renderResult,baseLanguage=setLanguage,baseCanSubmit=canSubmit;
mode=params.has('day')?'daily':params.has('example')?'lab':params.get('mode')==='hunt'?'hunt':'quick';
pendingRound=mode==='quick'?{seed:42,noise:3}:null;
function playUrl(){return new URL(location.href);}
function clearChallenge(){
  friendChallenge=null;friendScores=[];
  const u=playUrl();u.searchParams.delete('challenge');history.replaceState(null,'',u);
  $('challenge-error').hidden=true;
}
function hideShare(){$('share-panel').hidden=true;$('challenge-url').value='';txt('share-status','');}
function resetAttempt(keepActions=false){
  animationKey++;if(!keepActions)actions=[0,0,0];revealed=false;finished=false;
  predicted=null;userOutcome=null;aiOutcome=null;anim=1;hideShare();
  ranked=pack?C.rankPlans(pack,scene.frames,scene.goalFrame):[];
  drawInputs();renderControls();renderStatus();renderInspection();draw();
}
newScene=function(){
  clearFailure();hideShare();
  if(mode==='daily')scene=C.roundScene(day,round);
  else{
    const options=pendingRound||{seed:crypto.getRandomValues(new Uint32Array(1))[0],noise:mode==='quick'?3:Math.round(Number($('noise').value)*100)};
    scene=X.sceneFor(options);pendingRound=null;
  }
  resetAttempt();
};
switchMode=function(nextMode){
  if(!['quick','daily','hunt','lab'].includes(nextMode)||(nextMode===mode&&!friendChallenge))return;
  if(mode==='daily'&&!finished&&results.length&&!confirm(T('leaveConfirm')))return;
  clearChallenge();pendingRound=null;mode=nextMode;round=0;results=[];finished=false;
  const u=playUrl();u.searchParams.delete('day');u.searchParams.delete('m');u.searchParams.delete('rules');
  if(mode==='hunt')u.searchParams.set('mode','hunt');else u.searchParams.delete('mode');
  history.replaceState(null,'',u);day=today;
  if(mode==='quick')pendingRound={seed:42,noise:3};
  if(mode==='hunt')$('noise').value='0.03';
  renderResult();newScene();
};
function renderPlay(){
  for(const value of ['quick','daily','hunt','lab']){
    $(value).classList.toggle('active',mode===value);$(value).setAttribute('aria-pressed',String(mode===value));
  }
  const single=mode!=='daily';
  $('hunt-controls').hidden=mode!=='hunt';
  $('new-world').hidden=!single;$('new-world').disabled=!pack;
  if(single)txt('new-world',T(mode==='hunt'?'huntNewWorld':'quickNewWorld'));
  document.querySelector('.running-total').hidden=single;
  if(mode==='quick'||mode==='hunt'){
    txt('date',T(mode));txt('round',T('singleRound'));txt('mode-hint',T(mode+'Hint'));
    txt('scene-caption',T(mode));txt('plan-note',T(revealed?'locked':'keyboard'));
  }
  $('friend-banner').hidden=!friendChallenge;
  if(friendChallenge){
    const score=friendScores.reduce((s,r)=>s+r.pointsScore,0);
    txt('friend-summary',T(friendChallenge.kind==='daily'?'friendDailySummary':'friendSummary',{score}));
  }
  $('round-tools').hidden=!single||!revealed;
  $('quick-to-daily').hidden=mode!=='quick';
  $('play-feedback').hidden=!single||!revealed;
  if(single&&revealed){
    const difference=userOutcome.pointsScore-aiOutcome.pointsScore;
    const won=X.weakness(userOutcome,aiOutcome);
    txt('play-verdict',T(mode==='hunt'?(won?'huntSuccess':'huntTryAgain'):(difference>0?'quickWin':difference<0?'quickLose':'quickTie')));
    txt('play-explanation',T(mode==='hunt'?(won?'huntFound':'huntGoal'):'quickExplanation'));
  }
  $('friend-round').hidden=!friendChallenge||!revealed;
  if(friendChallenge&&revealed){
    const score=friendScores[friendChallenge.kind==='daily'?round:0].pointsScore;
    txt('friend-round',T('friendRound',{score,you:userOutcome.pointsScore}));
  }
  $('friend-final').hidden=!friendChallenge||!finished||mode!=='daily';
  if(friendChallenge&&finished&&mode==='daily'){
    const score=friendScores.reduce((s,r)=>s+r.pointsScore,0),you=results.reduce((s,r)=>s+r.you,0);
    txt('friend-final',T(you>score?'friendWin':you<score?'friendLose':'friendTie',{score,you}));
  }
  if(mode==='hunt'&&scene){
    $('hunt-noise').value=Math.round(scene.noise*100);$('hunt-target').value=scene.targetX??Math.round(scene.goal[0]*100);
    txt('hunt-noise-value',Math.round(scene.noise*100)+'%');txt('hunt-target-value',Math.round(scene.goal[0]*100)+'%');
    $('hunt-noise').disabled=$('hunt-target').disabled=!!friendChallenge||!pack;
    txt('hunt-feasible',T(friendChallenge?'huntLocked':C.oracle(scene).hit?'huntReachable':'huntUnreachable'));
  }
}
renderStatus=function(){baseStatus();renderPlay();};
renderResult=function(){baseResult();renderPlay();};
setLanguage=function(next){baseLanguage(next);renderPlay();};
canSubmit=function(){return baseCanSubmit()&&mode==='daily'&&C.validDay(day)&&day<=today&&Date.parse(today)-Date.parse(day)<=30*86400000;};
function challengePayload(){
  const value={v:1,rules:C.RULES,model:manifest.modelId,kind:mode==='daily'?'daily':mode==='hunt'?'hunt':'round'};
  if(mode==='daily'){
    if(!finished||results.length!==5)throw Error('unfinished');
    value.day=day;value.actions=results.map(r=>r.actions.slice());
  }else{
    if(!revealed)throw Error('unfinished');
    Object.assign(value,{seed:scene.seed,noise:Math.round(scene.noise*100),actions:actions.slice()});
    if(scene.targetX!==undefined)value.targetX=scene.targetX;
  }
  return X.validate(value,manifest.modelId,today);
}
shareLink=function(){
  // Pin the current preview/public origin; the action payload has no identity or trusted score.
  const u=new URL(lang==='en'?'':lang+'/',navigationRoot);
  u.searchParams.set('challenge',X.encode(challengePayload()));u.hash='play';return u.href;
};
function showChallenge(){
  if(!pack||!revealed)return;
  try{$('challenge-url').value=shareLink();}catch{return;}
  $('share-panel').hidden=false;txt('share-status','');$('send-challenge').hidden=typeof navigator.share!=='function';
  $('share-panel').scrollIntoView({block:'center',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
}
async function copyChallenge(){
  try{await navigator.clipboard.writeText($('challenge-url').value);txt('share-status',T('copySuccess'));}
  catch{$('challenge-url').focus();$('challenge-url').select();txt('share-status',T('copyFallback'));}
}
function editHunt(){
  if(mode!=='hunt'||friendChallenge||!pack||!scene)return;
  scene=X.sceneFor({seed:scene.seed,noise:Number($('hunt-noise').value),targetX:Number($('hunt-target').value)});
  resetAttempt(true);
}
function loadChallenge(token){
  try{
    const value=X.decode(token,manifest.modelId,today);
    friendScores=X.replay(value);friendChallenge=value;mode=value.kind==='daily'?'daily':value.kind==='hunt'?'hunt':'quick';
    round=0;results=[];finished=false;if(mode==='daily')day=value.day;else pendingRound=value;
    newScene();renderResult();renderBoard();
    $('play').scrollIntoView({block:'start'});
  }catch(error){txt('challenge-error',T(error.message==='model'?'modelChallenge':'invalidChallenge'));$('challenge-error').hidden=false;}
}
for(const value of ['quick','daily','hunt','lab'])$(value).onclick=()=>switchMode(value);
$('new-world').onclick=()=>{clearChallenge();pendingRound=null;newScene();};
$('retry-round').onclick=()=>resetAttempt(true);
$('quick-to-daily').onclick=()=>switchMode('daily');
$('hunt-noise').oninput=editHunt;$('hunt-target').oninput=editHunt;
$('challenge-round').onclick=$('share').onclick=showChallenge;
$('copy-challenge').onclick=copyChallenge;
$('send-challenge').onclick=async()=>{try{await navigator.share({title:'ORBIT',text:T('shareHeading'),url:$('challenge-url').value});}catch(e){if(e.name!=='AbortError')txt('share-status',T('copyFallback'));}};
$('close-share').onclick=hideShare;
$('leave-challenge').onclick=()=>{if(mode==='daily'&&!finished&&results.length&&!confirm(T('leaveConfirm')))return;clearChallenge();mode='quick';round=0;results=[];finished=false;pendingRound={seed:42,noise:3};renderResult();newScene();};
window.addEventListener('orbit-ready',()=>{if(params.has('challenge'))loadChallenge(params.get('challenge'));});
window.OrbitApp.features={challengePayload,loadChallenge,editHunt,resetAttempt,get friend(){return friendChallenge;}};
Object.assign(window.OrbitApp,{setLanguage,switchMode});
