'use strict';
// Generate the promotion fixture using the shipped neural weights and game rules.
const fs = require('node:fs');
const path = require('node:path');
const C = require('../game/orbit.js');
const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'source/ORBIT_JEPA_RU_EN_ZH.html'), 'utf8');
const manifest = JSON.parse(source.match(/<script id="orbit-manifest"[^>]*>(.*?)<\/script>/s)[1]);
const binary = Buffer.from(source.match(/<script id="orbit-bytes"[^>]*>(.*?)<\/script>/s)[1], 'base64');
const pack = C.unpack(manifest, binary.buffer.slice(binary.byteOffset, binary.byteOffset + binary.byteLength));
const day = '2026-11-16', round = 0;
const scene = C.roundScene(day, round), playerActions = [0, 0, 0];
const modelActions = C.rankPlans(pack, scene.frames, scene.goalFrame)[0].actions;
const player = C.outcome(scene, playerActions), model = C.outcome(scene, modelActions);
const result = {
  note: 'Illustrated replay of one selected round, not a benchmark or a screen recording.',
  day, round: round + 1, modelId: manifest.modelId,
  start: scene.p1, previous: scene.p0, goal: scene.goal, hitRadius: C.HIT,
  player: { actions: playerActions, path: player.points, score: player.pointsScore },
  model: { actions: modelActions, path: model.points, score: model.pointsScore }
};
fs.writeFileSync(path.join(root, 'promotion/demo-replay.json'), JSON.stringify(result, null, 2) + '\n');
console.log(JSON.stringify({day, round:round+1, player:result.player.actions, model:modelActions, scores:[player.pointsScore,model.pointsScore]}));
