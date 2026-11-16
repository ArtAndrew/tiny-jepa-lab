'use strict';
const { mkdirSync, writeFileSync, appendFileSync } = require('node:fs');
const { resolve } = require('node:path');
const { buildLeaderboard, fetchIssues } = require('./leaderboard.cjs');

(async () => {
  const repository = process.env.GITHUB_REPOSITORY || 'ArtAndrew/tiny-jepa-lab';
  const issues = await fetchIssues({ repository, token: process.env.GITHUB_TOKEN });
  const { board, checks } = buildLeaderboard(issues);
  const folder = resolve(__dirname, '../docs/assets');
  mkdirSync(folder, { recursive: true });
  writeFileSync(resolve(folder, 'leaderboard.json'), JSON.stringify(board) + '\n');
  // Statuses reveal only generated reason codes, never issue text or credentials.
  const summary = `## Leaderboard verification\n\n${board.entries.length} ranked results.\n\n` +
    checks.map(check => `- Issue #${check.issue}: ${check.status}${check.score !== undefined ? ` (${check.score} points)` : ''}${check.reason ? ` — ${check.reason}` : ''}`).join('\n') + '\n';
  if (process.env.GITHUB_STEP_SUMMARY) appendFileSync(process.env.GITHUB_STEP_SUMMARY, summary);
  console.log(summary);
})().catch(error => { console.error(error.message); process.exitCode = 1; });
