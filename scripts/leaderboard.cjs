'use strict';
const C = require('../game/orbit.js');
const {manifest, release} = require('./model_pack.cjs');
const supportedModels = new Set([manifest.modelId, ...release.previousModels]);
const MARKER = '<!-- ORBIT_REPLAY -->';
const DAY_MS = 86400000;

function validateReplay(body, { now = new Date(), createdAt = now.toISOString() } = {}) {
  if (typeof body !== 'string' || Buffer.byteLength(body) > 10000) throw Error('invalid-body');
  if (body.split(MARKER).length !== 2) throw Error('missing-or-duplicate-replay');
  const block = body.match(/<!-- ORBIT_REPLAY -->\s*```json\s*([\s\S]*?)\s*```/);
  if (!block) throw Error('missing-json');
  let replay;
  try { replay = JSON.parse(block[1]); } catch { throw Error('invalid-json'); }
  if (!replay || Array.isArray(replay) || typeof replay !== 'object' ||
      Object.keys(replay).sort().join(',') !== 'actions,day,model,version') throw Error('invalid-fields');
  if (replay.version !== C.RULES) throw Error('unsupported-rules');
  if (!supportedModels.has(replay.model)) throw Error('unsupported-model');
  if (!C.validDay(replay.day)) throw Error('invalid-day');
  const today = now.toISOString().slice(0, 10);
  const age = Date.parse(today) - Date.parse(replay.day);
  if (age < 0 || age > 30 * DAY_MS) throw Error('day-outside-window');
  const created = new Date(createdAt);
  if (!Number.isFinite(created.getTime()) || created > now || created.toISOString().slice(0, 10) < replay.day) {
    throw Error('invalid-submission-date');
  }
  if (!Array.isArray(replay.actions) || replay.actions.length !== 5 || !replay.actions.every(C.validActions)) {
    throw Error('invalid-actions');
  }
  // Coordinates and claimed scores are never accepted from the browser.
  const rounds = replay.actions.map((actions, i) => C.outcome(C.roundScene(replay.day, i), actions));
  return {
    day: replay.day, model: replay.model, rules: C.RULES,
    score: rounds.reduce((total, round) => total + round.pointsScore, 0),
    hits: rounds.filter(round => round.hit).length,
    roundScores: rounds.map(round => round.pointsScore)
  };
}

function buildLeaderboard(issues, now = new Date()) {
  const best = new Map(), checks = [];
  for (const issue of issues) {
    if (issue.pull_request || issue.state !== 'open' || !Number.isSafeInteger(issue.number)) continue;
    const labels = (issue.labels || []).map(label => typeof label === 'string' ? label : label.name);
    if (labels.includes('orbit-exclude')) continue;
    if (typeof issue.body !== 'string' || !issue.body.includes(MARKER)) continue;
    try {
      if (!issue.user || issue.user.type !== 'User' || !Number.isSafeInteger(issue.user.id) ||
          !/^[a-z\d](?:[a-z\d-]{0,37}[a-z\d])?$/i.test(issue.user.login)) throw Error('invalid-account');
      const result = validateReplay(issue.body, { now, createdAt: issue.created_at });
      if (labels.includes('orbit-test')) {
        checks.push({ issue: issue.number, status: 'test-passed', score: result.score });
        continue;
      }
      const row = { ...result, user: issue.user.login, issue: issue.number };
      delete row.roundScores;
      const key = issue.user.id + '|' + result.day + '|' + result.model;
      const old = best.get(key);
      if (!old || row.score > old.score || (row.score === old.score && row.issue < old.issue)) best.set(key, row);
      checks.push({ issue: issue.number, status: 'accepted', score: result.score });
    } catch (error) {
      checks.push({ issue: issue.number, status: 'rejected', reason: error.message });
    }
  }
  const entries = [...best.values()].sort((a, b) => b.day.localeCompare(a.day) || b.score - a.score || a.issue - b.issue);
  return { board: { version: 1, updated: now.toISOString(), entries }, checks };
}

async function fetchIssues({ repository, token, request = fetch, now = new Date() }) {
  if (!/^[\w.-]+\/[\w.-]+$/.test(repository)) throw Error('Invalid repository');
  const since = new Date(now.getTime() - 31 * DAY_MS).toISOString();
  const issues = [];
  // Fail closed on API errors or an incomplete fetch: never deploy a partial ranking.
  for (let page = 1; page <= 100; page++) {
    const url = new URL(`https://api.github.com/repos/${repository}/issues`);
    for (const [key, value] of Object.entries({ state: 'open', sort: 'created', direction: 'asc', since, per_page: 100, page })) {
      url.searchParams.set(key, value);
    }
    const headers = { Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28' };
    if (token) headers.Authorization = `Bearer ${token}`;
    const response = await request(url, { headers, signal: AbortSignal.timeout(30000) });
    if (!response.ok) throw Error(`GitHub issues API returned HTTP ${response.status}`);
    const rows = await response.json();
    if (!Array.isArray(rows)) throw Error('Invalid GitHub issues response');
    issues.push(...rows);
    if (rows.length < 100) return issues;
  }
  throw Error('Too many submissions to fetch completely');
}

module.exports = { validateReplay, buildLeaderboard, fetchIssues, MARKER, modelId: manifest.modelId };
