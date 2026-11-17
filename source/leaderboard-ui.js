let boardLoading = false, boardError = false, boardFetchedAt = 0;
function boardRow(rank,name,a,b,cls='',status=false){const row=el('div','board-row '+cls);row.append(el('span','rank',rank),el('span','',name),el('span','metric',a));const last=el('span',status?'pill'+(tab==='local'?' local':''):'secondary-metric',b);row.append(last);return row;}
function renderBoard() {
  const host = $('board-content'); host.replaceChildren();
  document.querySelectorAll('[data-board]').forEach(button => {
    button.classList.toggle('active', button.dataset.board === tab);
    button.setAttribute('aria-pressed', String(button.dataset.board === tab));
  });
  $('clear-local').hidden = tab !== 'local';
  $('refresh-board').hidden = tab !== 'players';
  $('refresh-board').disabled = boardLoading;
  if (tab === 'models') {
    host.append(boardRow('#',T('model'),T('success'),T('error'),'header-row'));
    const names={oracle:'modelOracle',model:'modelJEPA',no_push:'modelCoast',random:'modelRandom',shuffled_actions:'modelShuffled'};
    Object.keys(names).sort((a,b)=>benchmark[b].hit_rate.mean-benchmark[a].hit_rate.mean).forEach((k,i)=>{
      host.append(boardRow(String(i+1).padStart(2,'0'),T(names[k]),(100*benchmark[k].hit_rate.mean).toLocaleString(lang==='zh'?'zh-CN':lang,{minimumFractionDigits:2,maximumFractionDigits:2})+'%',benchmark[k].goal_distance_px.mean.toFixed(2)+' px',k==='model'?'highlight':''));
    });
    txt('board-note',T('benchmarkNote')); return;
  }
  const rows = (tab === 'local' ? localScores().filter(row => row.day === day) :
    (board.entries || []).filter(row => row.day === day && row.model === manifest?.modelId && row.rules === C.RULES))
    .sort((a,b)=>b.score-a.score || (a.issue || 0)-(b.issue || 0));
  if (!rows.length) host.append(el('div','empty',T(tab==='local'?'localEmpty':boardLoading?'boardLoading':boardError&&!board.updated?'boardError':'boardEmpty')));
  else {
    host.append(boardRow('#',T('player'),T('scoreLabel'),T('status'),'header-row'));
    rows.slice(0,20).forEach((entry,i) => {
      const row = boardRow(String(i+1).padStart(2,'0'),tab==='local'?T('you'):entry.user,String(entry.score),T(tab==='local'?'local':'verified'),'',true);
      if (tab === 'players' && Number.isSafeInteger(entry.issue) && entry.issue > 0) {
        const link = el('a','replay-link',entry.user);
        link.href = 'https://github.com/' + cfg.repo + '/issues/' + entry.issue;
        link.target = '_blank'; link.rel = 'noopener noreferrer';
        row.children[1].replaceChildren(link);
      }
      host.append(row);
    });
  }
  const snapshot = board.updated ? new Date(board.updated).toLocaleString(lang==='zh'?'zh-CN':lang) : '—';
  txt('board-note', tab==='players' ? (boardError?T('boardError')+' ':'') + T('boardRules') + ' ' + T('snapshot') + ': ' + snapshot : T(storageAvailable?'replaySaved':'sessionOnly'));
}
async function loadLeaderboard() {
  if (boardLoading || !cfg.live || cfg.offline) return;
  boardLoading = true; renderBoard();
  try {
    const response = await fetch(cfg.assetPrefix+'leaderboard.json?t='+Date.now(), { cache:'no-store', signal:AbortSignal.timeout(15000) });
    if (!response.ok) throw Error('Leaderboard unavailable');
    const data = await response.json();
    if (data.version!==1 || !Array.isArray(data.entries) || (data.updated!==null && !Number.isFinite(Date.parse(data.updated)))) throw Error('Invalid leaderboard');
    data.entries = data.entries.filter(row => C.validDay(row.day) && typeof row.user==='string' &&
      /^[a-z\d](?:[a-z\d-]{0,37}[a-z\d])?$/i.test(row.user) && Number.isInteger(row.score) && row.score>=0 && row.score<=5000 &&
      Number.isSafeInteger(row.issue) && row.issue>0);
    board = data; boardError = false; boardFetchedAt = Date.now();
  } catch { boardError = true; }
  finally { boardLoading = false; renderBoard(); }
}
