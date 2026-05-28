"""One-off: export COUNTRY_CODES from serp_scraper.COUNTRY_DATA to JSON."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
text = (ROOT / "app" / "scrapers" / "serp_scraper.py").read_text(encoding="utf-8")
idx = text.rfind("COUNTRY_DATA = {")
chunk = text[idx:]
end = chunk.find("\n}\n\n_STRIP_WORDS")
chunk = chunk[: end + 2]
codes = {}
for m in re.finditer(r'"gl": "([a-z]{2})", "location": "([^"]+)"', chunk):
    gl, loc = m.group(1).upper(), m.group(2)
    if loc not in codes:
        codes[loc] = gl
out = ROOT / "app" / "services" / "country_codes.json"
out.write_text(json.dumps(dict(sorted(codes.items())), indent=2), encoding="utf-8")
print(f"Wrote {len(codes)} countries to {out}")
