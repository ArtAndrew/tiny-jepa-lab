const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const vm = require('node:vm');
const C = require('../game/orbit.js');
const { validateReplay, buildLeaderboard, fetchIssues, MARKER, modelId } = require('./leaderboard.cjs');
const now = new Date('2026-11-16T12:00:00Z');
const plain = () => ({ version:'orbit-1', model:modelId, day:'2026-11-16', actions:Array.from({length:5},()=>[0,0,0]) });
const body = replay => `${MARKER}\n\`\`\`json\n${JSON.stringify(replay)}\n\`\`\``;
const issue = (number, replay = plain(), extras = {}) => ({ number, body:body(replay), state:'open',
  user:{id:42,login:'player',type:'User'}, created_at:'2026-11-16T10:00:00Z', labels:[], ...extras });

test('valid replay recomputes five rounds using the browser rules', () => {
  const result = validateReplay(body(plain()), {now});
  const scores = plain().actions.map((actions,i) => C.outcome(C.roundScene('2026-11-16',i), actions).pointsScore);
  assert.deepEqual(result.roundScores, scores);
  // Recorded from a complete Safari run on this UTC day with five no-push plans.
  assert.deepEqual(result.roundScores, [745,129,979,994,876]);
  assert.equal(result.score,3723);
  assert.equal(result.score, scores.reduce((a,b)=>a+b,0));
  assert.ok(result.score>=0 && result.score<=5000);
});

test('rejects forged scores, foreign model, malformed actions and executable text', () => {
  const cases = [
    {...plain(),score:5000}, {...plain(),model:'other'}, {...plain(),version:'other'},
    {...plain(),actions:[[0,0,0]]}, {...plain(),actions:Array(5).fill([0,0,2])},
    {...plain(),actions:Array(5).fill([0,0,'1'])}, {...plain(),actions:Array(5).fill([0,0,null])},
    {...plain(),actions:Array(5).fill([0,0,0,0])}, {...plain(),actions:Array(5).fill([false,0,0])},
    {...plain(),actions:Array(5).fill([0.1,0,0])}, {...plain(),user:'forged-account'}, null, []
  ];
  for (const replay of cases) assert.throws(()=>validateReplay(body(replay),{now}));
  for (const invalid of ['', body(plain())+body(plain()), 'a'.repeat(10001), `${MARKER}\n\`\`\`json\nprocess.exit()\n\`\`\``]) {
    assert.throws(()=>validateReplay(invalid,{now}));
  }
});

test('validates dates and the 30-day UTC window', () => {
  for (const day of ['2026-02-30','2026-11-17','2026-10-16','tomorrow']) {
    assert.throws(()=>validateReplay(body({...plain(),day}),{now}));
  }
  assert.doesNotThrow(()=>validateReplay(body({...plain(),day:'2026-10-17'}),{now}));
  assert.throws(()=>validateReplay(body(plain()),{now,createdAt:'2026-11-15T23:59:59Z'}));
  assert.throws(()=>validateReplay(body(plain()),{now,createdAt:'2026-11-17T00:00:00Z'}));
  assert.throws(()=>validateReplay(body(plain()),{now,createdAt:'invalid'}));
});

test('keeps the best verified result per account/day with stable tie ordering', () => {
  const better = {...plain(),actions:Array.from({length:5},(_,i)=>C.oracle(C.roundScene('2026-11-16',i)).actions)};
  const {board, checks} = buildLeaderboard([issue(3),issue(2,better),issue(1,better)],now);
  assert.equal(board.entries.length,1);
  assert.equal(board.entries[0].issue,1);
  assert.equal(board.entries[0].user,'player');
  assert.equal(board.entries[0].score,validateReplay(body(better),{now}).score);
  assert.equal(checks.length,3);
});

test('closed, excluded, bot and PR submissions cannot enter; smoke checks never add fake scores', () => {
  const {board,checks}=buildLeaderboard([
    issue(1,plain(),{state:'closed'}),issue(2,plain(),{labels:[{name:'orbit-exclude'}]}),
    issue(3,plain(),{pull_request:{}}),issue(4,plain(),{user:{id:8,login:'test-bot',type:'Bot'}}),
    issue(5,plain(),{labels:[{name:'orbit-test'}]}), issue(6,plain(),{body:'normal bug report'}),
    issue(7,plain(),{user:{id:9,login:'<script>',type:'User'}})
  ],now);
  assert.equal(board.entries.length,0);
  assert.equal(checks.find(c=>c.issue===5).status,'test-passed');
  assert.equal(checks.filter(c=>c.status==='rejected').length,2);
});

test('fetches every page and does not accept a partial API failure', async () => {
  let calls=0;
  const request=async(url,options)=>{
    assert.equal(url.hostname,'api.github.com');
    assert.equal(url.searchParams.get('state'),'open');
    assert.equal(options.headers.Authorization,'Bearer test-token');
    calls++;
    return {ok:true,json:async()=>calls===1?Array(100).fill(issue(1)):[issue(101)]};
  };
  const rows=await fetchIssues({repository:'ArtAndrew/tiny-jepa-lab',token:'test-token',request,now});
  assert.equal(calls,2); assert.equal(rows.length,101);
  await assert.rejects(()=>fetchIssues({repository:'ArtAndrew/tiny-jepa-lab',request:async()=>({ok:false,status:403}),now}),/HTTP 403/);
  await assert.rejects(()=>fetchIssues({repository:'https://evil.example',request,now}));
});

test('shared scorer is extracted unchanged from the archived browser source', () => {
  const root=resolve(__dirname,'..');
  const source=readFileSync(resolve(root,'source/ORBIT_JEPA_RU_EN_ZH.html'),'utf8');
  const executable=Array.from(source.matchAll(/<script\b([^>]*)>(.*?)<\/script>/gs)).filter(s=>!s[1].includes('type='));
  assert.equal(readFileSync(resolve(root,'game/engine.js'),'utf8'),executable[0][2]);
  assert.equal(readFileSync(resolve(root,'game/orbit.js'),'utf8'),executable[1][2]);
});

test('public table loads verified rows, uses safe links and retains the snapshot on failure', async () => {
  function element(tag,cls,text){return {tag,cls,text,children:[],append(...children){this.children.push(...children);},replaceChildren(...children){this.children=children;}};}
  const nodes=Object.fromEntries(['board-content','clear-local','refresh-board','board-note'].map(id=>[id,element('div')]));
  const verified={day:'2026-11-16',model:modelId,rules:'orbit-1',user:'player',score:1234,issue:12};
  let failure=false;
  const context={
    board:{version:1,updated:null,entries:[]},tab:'players',day:'2026-11-16',manifest:{modelId},
    cfg:{live:true,offline:false,assetPrefix:'../assets/',repo:'ArtAndrew/tiny-jepa-lab'},lang:'ru',C,
    document:{querySelectorAll:()=>[]},$:id=>nodes[id],el:element,T:key=>key,
    txt:(id,text)=>{nodes[id].text=text;},localScores:()=>[],storageAvailable:true,AbortSignal,
    fetch:async()=>failure?{ok:false}:{ok:true,json:async()=>({version:1,updated:now.toISOString(),entries:[verified,{...verified,user:'<script>'}]})}
  };
  vm.createContext(context);
  vm.runInContext(readFileSync(resolve(__dirname,'../source/leaderboard-ui.js'),'utf8'),context);
  await context.loadLeaderboard();
  assert.equal(context.board.entries.length,1);
  assert.equal(nodes['board-content'].children[1].children[1].children[0].href,'https://github.com/ArtAndrew/tiny-jepa-lab/issues/12');
  assert.equal(nodes['refresh-board'].disabled,false);
  failure=true; await context.loadLeaderboard();
  assert.equal(context.board.entries.length,1);
  assert.match(nodes['board-note'].text,/boardError/);
});
