// JSON in/out reference bridge for independent Python/JavaScript parity checks.
const fs = require('node:fs');
const {C, pack} = require('./model_pack.cjs');
const cases = JSON.parse(fs.readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(cases.map(({seed, noise}) => {
  const scene = C.scenario(seed, noise), ranked = C.rankPlans(pack, scene.frames, scene.goalFrame);
  return {scene, encoded: C.encodeContext(pack, scene.frames), ranked,
    futures: C.PLANS.map(actions => C.simulate(scene.p1, scene.v, actions).ends)};
})));
