"""Validate and copy a generated standalone demo for GitHub Pages."""

import argparse
import hashlib
import json
import re
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("source", type=Path, help="Generated ai-talent-network.html")
args = parser.parse_args()
payload = args.source.read_bytes()
html = payload.decode("utf-8")
match = re.search(r'<script type="application/json" id="data">(.*?)</script>', html, re.S)
if not match:
    parser.error("Source is missing the embedded talent dataset")
data = json.loads(match.group(1))
if not isinstance(data.get("people"), list) or not data["people"]:
    parser.error("Source dataset has no people records")
for anchor in ("roster", "shortlist", "method"):
    if f'id="{anchor}"' not in html:
        parser.error(f"Source is missing the {anchor} section")
destination = Path(__file__).resolve().parent / "index.html"
destination.write_bytes(payload)
print(json.dumps({
    "records": len(data["people"]),
    "generated": data.get("generated"),
    "sha256": hashlib.sha256(payload).hexdigest(),
}, ensure_ascii=False))
