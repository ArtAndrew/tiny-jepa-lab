/* Apply before first paint; theme changes never reset the game. */
(() => {
  'use strict';
  const key = 'orbit-theme';
  const valid = value => ['auto', 'light', 'dark'].includes(value) ? value : 'auto';
  const system = window.matchMedia('(prefers-color-scheme: dark)');
  let preference = 'auto';
  try { preference = valid(localStorage.getItem(key)); } catch {}
  const lightColors = {
    '#101726':'#f7f9fd', '#0a101b':'#edf2f8', '#32294725':'#ddd2fa55', '#0b111d00':'#ffffff00',
    '#24304466':'#c7d2e366', '#45516a':'#a0adc2', '#8291ab':'#63748d',
    '#b6a0ff13':'#7046ce13', '#b6a0ff9c':'#7046cebb', '#b6a0ff55':'#7046ce77',
    '#b6a0ff':'#7046ce', '#c8b7ff':'#5e35b1', '#8b9bb4':'#6a7991', '#57677d':'#8996aa',
    '#77e6cd':'#087b69', '#b5c1d2':'#4d5e76', '#c9b7ff':'#5e35b1',
    '#0b101c':'#f6f8fc', '#312346':'#e8def7', '#4b3d67':'#b5a3d2',
    '#a5b0c3':'#52627b', '#edf0f8':'#202c42', '#637188':'#637188',
    '#b2bed1':'#52627b', '#2b3548':'#cdd6e4', '#9ba8bd':'#52627b'
  };
  function apply() {
    const resolved = preference === 'auto' ? (system.matches ? 'dark' : 'light') : preference;
    const root = document.documentElement;
    root.dataset.theme = resolved;
    root.dataset.themePreference = preference;
    root.style.colorScheme = resolved;
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = resolved === 'dark' ? '#090d17' : '#f5f7fb';
    const select = document.getElementById('theme-select');
    if (select) select.value = preference;
    window.dispatchEvent(new Event('orbit-theme-change'));
  }
  function set(value) {
    preference = valid(value);
    try { localStorage.setItem(key, preference); } catch {}
    apply();
  }
  window.OrbitTheme = {
    set,
    color: color => document.documentElement.dataset.theme === 'light' ? (lightColors[color] || color) : color
  };
  apply();
  const onSystemChange = () => { if (preference === 'auto') apply(); };
  if (system.addEventListener) system.addEventListener('change', onSystemChange);
  else system.addListener(onSystemChange);
  window.addEventListener('storage', event => {
    if (event.key === key || event.key === null) {
      preference = valid(event.newValue);
      apply();
    }
  });
  document.addEventListener('DOMContentLoaded', () => {
    const select = document.getElementById('theme-select');
    select.value = preference;
    select.addEventListener('change', () => set(select.value));
  });
})();
