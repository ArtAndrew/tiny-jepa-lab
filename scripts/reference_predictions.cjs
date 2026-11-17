// JSON in/out reference bridge for independent Python/JavaScript parity checks.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const C = require('../game/orbit.js');
let pack;
if (process.argv[2] === '--legacy') {
  const source = fs.readFileSync(path.join(__dirname, '../source/ORBIT_JEPA_RU_EN_ZH.html'), 'utf8');
  const manifest = JSON.parse(source.match(/<script id="orbit-manifest"[^>]*>(.*?)<\/script>/s)[1]);
  const bytes = Buffer.from(source.match(/<script id="orbit-bytes"[^>]*>(.*?)<\/script>/s)[1], 'base64');
  pack = C.unpack(manifest, bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength));
} else if (process.argv[2]) {
  // Custom bundles never read the historical HTML or its weights.
  const manifest = JSON.parse(fs.readFileSync(path.join(process.argv[2], 'manifest.json'), 'utf8'));
  const bytes = fs.readFileSync(path.join(process.argv[2], 'model.bin'));
  if (bytes.length !== manifest.byteLength || crypto.createHash('sha256').update(bytes).digest('hex') !== manifest.sha256)
    throw Error('Model bundle integrity mismatch');
  pack = C.unpack(manifest, bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength));
} else {
  pack = require('./model_pack.cjs').pack;
}
const cases = JSON.parse(fs.readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(cases.map(({seed, noise}) => {
  const scene = C.scenario(seed, noise), ranked = C.rankPlans(pack, scene.frames, scene.goalFrame);
  return {scene, encoded: C.encodeContext(pack, scene.frames), ranked,
    futures: C.PLANS.map(actions => C.simulate(scene.p1, scene.v, actions).ends)};
})));
