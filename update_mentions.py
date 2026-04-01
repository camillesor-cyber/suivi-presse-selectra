"""
Met à jour mentions.json avec les nouveaux articles Google News RSS.
Tourne via GitHub Actions chaque matin a 8h.
Aucune dependance externe, aucune cle API.
"""

import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

BRAND        = "Selectra"
MAX_ARTICLES = 20
JSON_FILE    = Path("mentions.json")

def fetch_rss():
    query = urllib.parse.quote(f'"{BRAND}"')
    url   = f"https://news.google.com/rss/search?q={query}&hl=fr&gl=FR&ceid=FR:fr"
    req   = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        root = ET.fromstring(resp.read())

    articles = []
    for item in root.findall(".//item")[:MAX_ARTICLES]:
        title  = item.findtext("title",   "").strip()
        link   = item.findtext("link",    "").strip()
        pub    = item.findtext("pubDate", "").strip()
        source = item.findtext("source",  "Source inconnue").strip()

        try:
            dt       = datetime.strptime(pub, "%a, %d %b %Y %H:%M:%S %Z")
            date_str = dt.strftime("%d/%m/%Y")
        except Exception:
            date_str = datetime.now().strftime("%d/%m/%Y")

        if title and link:
            articles.append({
                "id":       f"rss-{abs(hash(link))}",
                "titre":    title,
                "source":   source,
                "date":     date_str,
                "url":      link,
                "type":     "presse",
                "tonalite": "neutre",
                "score":    5,
                "ajout":    "auto"
            })
    return articles

def main():
    existing = json.loads(JSON_FILE.read_text(encoding="utf-8")) if JSON_FILE.exists() else []
    existing_ids  = {m["id"]  for m in existing}
    existing_urls = {m["url"] for m in existing}

    new_articles = fetch_rss()
    added = 0
    for a in new_articles:
        if a["id"] not in existing_ids and a["url"] not in existing_urls:
            existing.insert(0, a)
            added += 1

    def sort_key(m):
        try:
            d, mo, y = m["date"].split("/")
            return f"{y}{mo}{d}"
        except Exception:
            return "00000000"

    existing = sorted(existing, key=sort_key, reverse=True)[:500]
    JSON_FILE.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK - {added} nouvelle(s) mention(s) ajoutee(s) sur {len(new_articles)} articles RSS")

if __name__ == "__main__":
    main()
