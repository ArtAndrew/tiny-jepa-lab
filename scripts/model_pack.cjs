'use strict';
const fs = require('node:fs');
const path = require('node:path');
const C = require('../game/orbit.js');
const source = fs.readFileSync(path.join(__dirname, '../source/ORBIT_JEPA_RU_EN_ZH.html'), 'utf8');
const manifest = JSON.parse(source.match(/<script id="orbit-manifest"[^>]*>(.*?)<\/script>/s)[1]);
const bytes = Buffer.from(source.match(/<script id="orbit-bytes"[^>]*>(.*?)<\/script>/s)[1], 'base64');
const pack = C.unpack(manifest, bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength));
module.exports = {C, pack, manifest};
