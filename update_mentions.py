import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

BRAND        = "Selectra"
MAX_ARTICLES = 50
JSON_FILE    = Path("mentions.json")

EXCLUDE_KEYWORDS = [
    "selectra.info", "selectra.net", "myselectra.com", "selectra.com",
    "selectra.es", "selectra.pt", "selectra.be"
]

# Médias connus et leur tier pour le score
MEDIA_TIERS = {
    # Presse grand tirage
    "le monde": ("presse", "big"), "le figaro": ("presse", "big"),
    "le parisien": ("presse", "big"), "ouest france": ("presse", "big"),
    "les echos": ("presse", "good"), "la croix": ("presse", "good"),
    "la provence": ("presse", "good"),
    "challenges": ("presse", "medium"), "l'express": ("presse", "medium"),
    "le point": ("presse", "medium"),
    # TV
    "tf1": ("tv", "tf1"), "france 2": ("tv", "f2"),
    "france 3": ("tv", "f3"), "m6": ("tv", "f3"), "bfmtv": ("tv", "f3"),
    "bfm": ("tv", "f3"), "france 5": ("tv", "f5"), "arte": ("tv", "f5"),
    "cnews": ("tv", "f5"), "lci": ("tv", "nrj12"),
    "france info tv": ("tv", "nrj12"),
    # Radio
    "france inter": ("radio", "r1"), "rtl": ("radio", "r1"),
    "france info": ("radio", "r2"), "nrj": ("radio", "r2"),
    "rmc": ("radio", "r2"), "europe 1": ("radio", "r2"),
    "france bleu": ("radio", "r4"),
}

SCORE_TABLE = {
    "presse": {"big": (250,125), "good": (200,100), "medium": (150,75), "other": (100,50)},
    "tv":     {"tf1": (1000,500), "f2": (800,400), "f3": (550,275), "f5": (350,175), "nrj12": (200,100), "other": (150,75)},
    "radio":  {"r1": (400,200), "r2": (300,150), "r3": (200,100), "r4": (100,50)},
    "social": {"other": (120,36)},
    "forum":  {"other": (60,18)},
}

def get_media_info(source):
    src = source.lower()
    for key, (mtype, tier) in MEDIA_TIERS.items():
        if key in src:
            return mtype, tier
    return "presse", "other"

def compute_score(source, is_dedicated=False):
    mtype, tier = get_media_info(source)
    table = SCORE_TABLE.get(mtype, SCORE_TABLE["presse"])
    scores = table.get(tier, table.get("other", (100, 50)))
    return scores[0] if is_dedicated else scores[1], mtype

def fetch_rss():
    query = urllib.parse.quote(f'"{BRAND}"')
    url   = f"https://news.google.com/rss/search?q={query}&hl=fr&gl=FR&ceid=FR:fr"
    req   = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        root = ET.fromstring(resp.read())

    cutoff = datetime.now() - timedelta(days=30)
    articles = []

    for item in root.findall(".//item")[:MAX_ARTICLES]:
        title  = item.findtext("title",   "").strip()
        link   = item.findtext("link",    "").strip()
        pub    = item.findtext("pubDate", "").strip()
        source = item.findtext("source",  "Source inconnue").strip()

        # Filtrer domaines Selectra sur titre et source
        combined = (title + source).lower()
        if any(kw in combined for kw in EXCLUDE_KEYWORDS):
            continue

        # Parser la date
        try:
            dt = datetime.strptime(pub, "%a, %d %b %Y %H:%M:%S %Z")
            if dt < cutoff:
                continue
            date_str = dt.strftime("%d/%m/%Y")
        except Exception:
            date_str = datetime.now().strftime("%d/%m/%Y")

        score, mtype = compute_score(source)

        if title and link:
            articles.append({
                "id":       f"rss-{abs(hash(link))}",
                "titre":    title,
                "source":   source,
                "date":     date_str,
                "url":      link,
                "type":     mtype,
                "tonalite": "neutre",
                "score":    score,
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
    print(f"OK - {added} ajoutee(s) sur {len(new_articles)} articles recuperes")

if __name__ == "__main__":
    main()
