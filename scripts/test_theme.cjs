const assert = require('node:assert/strict');
const { test } = require('node:test');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const vm = require('node:vm');
const source = readFileSync(resolve(__dirname, '../source/theme.js'), 'utf8');

function browser({ dark = false, saved = null, storageBlocked = false, legacyMedia = false } = {}) {
  const listeners = {}, documentListeners = {}, selectListeners = {};
  const storage = new Map([['unrelated-game-score', '123']]);
  if (saved !== null) storage.set('orbit-theme', saved);
  let ready = false, redraws = 0, mediaChange;
  const root = { dataset: {}, style: {} }, meta = {}, select = { value: '' };
  select.addEventListener = (type, callback) => { selectListeners[type] = callback; };
  const media = { matches: dark };
  const subscribe = (...args) => { mediaChange = args.at(-1); };
  if (legacyMedia) media.addListener = subscribe;
  else media.addEventListener = subscribe;
  const window = {
    matchMedia: () => media,
    addEventListener: (type, callback) => { listeners[type] = callback; },
    dispatchEvent: event => { if (event.type === 'orbit-theme-change') redraws++; }
  };
  const localStorage = {
    getItem: key => { if (storageBlocked) throw Error('Storage denied'); return storage.get(key) ?? null; },
    setItem: (key, value) => { if (storageBlocked) throw Error('Storage denied'); storage.set(key, value); }
  };
  const document = {
    documentElement: root,
    querySelector: () => meta,
    getElementById: () => ready ? select : null,
    addEventListener: (type, callback) => { documentListeners[type] = callback; }
  };
  vm.runInNewContext(source, { window, document, localStorage, Event: class { constructor(type) { this.type = type; } } });
  return {
    root, meta, select, storage, window,
    get redraws() { return redraws; },
    ready() { ready = true; documentListeners.DOMContentLoaded(); },
    choose(value) { select.value = value; selectListeners.change(); },
    system(dark) { media.matches = dark; mediaChange(); },
    storageEvent(key, newValue) { listeners.storage({ key, newValue }); }
  };
}

test('first paint uses system appearance; Auto follows later system changes', () => {
  const b = browser({ dark: true });
  assert.equal(b.root.dataset.theme, 'dark');
  assert.equal(b.root.dataset.themePreference, 'auto');
  b.ready();
  assert.equal(b.select.value, 'auto');
  b.system(false);
  assert.equal(b.root.dataset.theme, 'light');
  assert.equal(b.root.style.colorScheme, 'light');
  assert.equal(b.meta.content, '#f5f7fb');
  assert.equal(b.redraws, 2);
});

test('manual choice persists, ignores system changes and leaves scores intact', () => {
  const b = browser(); b.ready(); b.choose('dark');
  const redraws = b.redraws;
  b.system(true); b.system(false);
  assert.equal(b.root.dataset.theme, 'dark');
  assert.equal(b.redraws, redraws);
  assert.equal(b.storage.get('orbit-theme'), 'dark');
  assert.equal(b.storage.get('unrelated-game-score'), '123');
  const reloaded = browser({ saved: b.storage.get('orbit-theme') });
  assert.equal(reloaded.root.dataset.theme, 'dark');
  b.choose('auto');
  assert.equal(b.root.dataset.theme, 'light');
  b.system(true);
  assert.equal(b.root.dataset.theme, 'dark');
});

test('unavailable storage still allows switching; corrupt preference falls back to Auto', () => {
  const b = browser({ storageBlocked: true }); b.ready(); b.choose('dark');
  assert.equal(b.root.dataset.theme, 'dark');
  assert.equal(browser({ saved: 'invalid', dark: true }).root.dataset.theme, 'dark');
});

test('other tabs sync the choice; clearing storage restores Auto', () => {
  const b = browser(); b.ready();
  b.storageEvent('orbit-theme', 'dark');
  assert.equal(b.select.value, 'dark');
  b.storageEvent('unrelated-game-score', '999');
  assert.equal(b.root.dataset.theme, 'dark');
  b.storageEvent(null, null);
  assert.equal(b.select.value, 'auto');
  assert.equal(b.root.dataset.theme, 'light');
});

test('older media listeners work; canvas colors follow the active palette', () => {
  const b = browser({ dark: true, legacyMedia: true });
  assert.equal(b.window.OrbitTheme.color('#77e6cd'), '#77e6cd');
  b.system(false);
  assert.equal(b.window.OrbitTheme.color('#77e6cd'), '#087b69');
});

test('generated pages have valid scripts and unchanged model/physics code', () => {
  const root = resolve(__dirname, '..');
  const original = readFileSync(resolve(root, 'source/ORBIT_JEPA_RU_EN_ZH.html'), 'utf8');
  const scripts = html => Array.from(html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/g));
  const originalExecutable = scripts(original).filter(s => !s[1].includes('type='));
  for (const route of ['', 'ru/', 'zh/']) {
    const html = readFileSync(resolve(root, 'docs', route, 'index.html'), 'utf8');
    const executable = scripts(html).filter(s => !s[1].includes('type='));
    for (const s of executable) new vm.Script(s[2]);
    // The added theme controller precedes the original engine and orbit core.
    assert.equal(executable[1][2], originalExecutable[0][2]);
    assert.equal(executable[2][2], originalExecutable[1][2]);
    const bytes = text => text.match(/<script id="orbit-bytes"[^>]*>(.*?)<\/script>/s)[1];
    assert.equal(bytes(html), bytes(original));
    assert.ok(html.includes("addEventListener('orbit-theme-change',draw)"));
    const ids = Array.from(html.matchAll(/\bid="([^"]+)"/g), m => m[1]);
    assert.equal(new Set(ids).size, ids.length);
    assert.equal((html.match(/id="theme-select"/g) || []).length, 1);
    const i18n = JSON.parse(html.match(/<script id="orbit-i18n"[^>]*>(.*?)<\/script>/s)[1]);
    for (const [, key] of html.matchAll(/\bdata-t="([^"]+)"/g)) {
      for (const lang of ['en', 'ru', 'zh']) assert.ok(i18n[lang][key], `${lang}: ${key}`);
    }
  }
});
