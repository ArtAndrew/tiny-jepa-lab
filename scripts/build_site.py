#!/usr/bin/env python3
"""Prepare GitHub Pages from the supplied self-contained ORBIT release."""
from pathlib import Path
import hashlib
import html
import json
import re
import base64

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://artandrew.github.io/tiny-jepa-lab/"
REPO = "https://github.com/ArtAndrew/tiny-jepa-lab"
source = (ROOT / "source/ORBIT_JEPA_RU_EN_ZH.html").read_text()


def embedded(text, key):
    return json.loads(re.search(rf'<script id="{key}"[^>]*>(.*?)</script>', text, re.S)[1])


def replace_json(text, key, value):
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    return re.sub(rf'(<script id="{key}"[^>]*>).*?(</script>)',
                  lambda m: m[1] + payload + m[2], text, flags=re.S)


manifest = embedded(source, "orbit-manifest")
weights = base64.b64decode(re.search(r'<script id="orbit-bytes"[^>]*>(.*?)</script>', source, re.S)[1])
assert len(weights) == manifest["byteLength"]
assert hashlib.sha256(weights).hexdigest() == manifest["sha256"]

i18n = embedded(source, "orbit-i18n")
updates = {
    "en": {
        "offlineSubmit": "Online leaderboard is not connected in this release. Your scores stay on this device.",
        "boardEmpty": "The public leaderboard is not connected in this release.",
        "boardNotLive": "Play the daily challenge and view your scores under This device.",
        "boardRules": "Online replay submission is disabled. Local scores are not verified.",
        "previousLab": "Read the release report ↗",
    },
    "ru": {
        "offlineSubmit": "Общий рейтинг в этой публикации не подключён. Результаты сохраняются на этом устройстве.",
        "boardEmpty": "Общий рейтинг в этой публикации не подключён.",
        "boardNotLive": "Испытание дня работает. Твои результаты доступны во вкладке «Это устройство».",
        "boardRules": "Отправка повторов в общий рейтинг отключена. Локальные очки не проверены.",
        "previousLab": "Прочитать отчёт о релизе ↗",
    },
    "zh": {
        "offlineSubmit": "此发布版本尚未连接在线排行榜。成绩保存在本机。",
        "boardEmpty": "此发布版本尚未连接公开排行榜。",
        "boardNotLive": "每日挑战可正常游玩。请在“本机记录”中查看成绩。",
        "boardRules": "在线回放提交已禁用。本地成绩未经验证。",
        "previousLab": "阅读发布报告 ↗",
    },
}
for language, values in updates.items():
    i18n[language].update(values)

for language, route in [("en", ""), ("ru", "ru/"), ("zh", "zh/")]:
    text = source
    config = embedded(text, "orbit-config")
    config.update(lang=language, offline=False, live=False, published=True,
                  baseUrl=BASE, repo="ArtAndrew/tiny-jepa-lab",
                  assetPrefix="../assets/" if route else "assets/")
    text = replace_json(text, "orbit-config", config)
    text = replace_json(text, "orbit-i18n", i18n)
    text = re.sub(r'<html lang="[^"]+">', '<html lang="' + ("zh-Hans" if language == "zh" else language) + '">', text, count=1)
    title = html.escape(i18n[language]["pageTitle"], quote=True)
    description = html.escape(i18n[language]["description"], quote=True)
    text = re.sub(r'<title>.*?</title>', lambda _: '<title>' + title + '</title>', text, count=1)
    for attr, key, value in [("name", "description", description), ("property", "og:title", title),
                             ("property", "og:description", description), ("property", "og:url", BASE + route)]:
        text = re.sub(rf'<meta {attr}="{key}" content="[^"]*">',
                      lambda _, a=attr, k=key, v=value: f'<meta {a}="{k}" content="{v}">', text, count=1)
    text = re.sub(r'<link rel="canonical" href="[^"]*">',
                  lambda _: '<link rel="canonical" href="' + BASE + route + '">', text, count=1)
    # The source references social PNGs and an earlier lab that were not supplied.
    text = re.sub(r'<meta property="og:image" content="[^"]*">', '', text)
    text = text.replace('name="twitter:card" content="summary_large_image"', 'name="twitter:card" content="summary"')
    text = text.replace(BASE + 'predict/', REPO + '/blob/main/materials/ORBIT_RELEASE_REPORT_RU.md')
    # Sharing a public URL is independent of enabling a public replay backend.
    text = text.replace("if(cfg.live)s+='\\n'+shareLink();", "if(cfg.published)s+='\\n'+shareLink();")
    text = text.replace("cfg.live?new URL(cfg.baseUrl).host", "cfg.published?new URL(cfg.baseUrl).host")
    # Translate existing text-only labels before JavaScript boots.
    text = re.sub(r'(<([a-z0-9]+)\b[^>]*\bdata-t="([^"]+)"[^>]*>)([^<]*)(</\2>)',
                  lambda m: m[1] + html.escape(i18n[language].get(m[3], html.unescape(m[4]))) + m[5], text)
    destination = ROOT / "docs" / route / "index.html"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text)
    print(destination.relative_to(ROOT), len(text.encode()), "bytes")

(ROOT / "docs/.nojekyll").touch()
(ROOT / "docs/robots.txt").write_text("User-agent: *\nAllow: /\nSitemap: " + BASE + "sitemap.xml\n")
(ROOT / "docs/sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
    ''.join('<url><loc>' + BASE + route + '</loc></url>\n' for route in ["", "ru/", "zh/"]) + '</urlset>\n')
print("Original model verified:", manifest["modelId"], manifest["sha256"])
