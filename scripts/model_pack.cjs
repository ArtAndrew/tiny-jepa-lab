'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const C = require('../game/orbit.js');
const release = require('../source/model-release.json');
const directory = path.join(__dirname, '..', release.directory);
const manifest = JSON.parse(fs.readFileSync(path.join(directory, 'manifest.json'), 'utf8'));
const bytes = fs.readFileSync(path.join(directory, 'model.bin'));
if (manifest.modelId !== release.modelId || manifest.sha256 !== release.sha256 ||
    bytes.length !== manifest.byteLength || crypto.createHash('sha256').update(bytes).digest('hex') !== release.sha256)
  throw Error('Active model integrity mismatch');
const pack = C.unpack(manifest, bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength));
module.exports = {C, pack, manifest, bytes, release};
