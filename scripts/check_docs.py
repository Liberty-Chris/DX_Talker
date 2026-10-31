"""Check repository links and the help manifest without network or optional packages."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
errors = []
links = 0
for path in ROOT.rglob("*.md"):
    if any(part in {".venv", "build", "dist"} for part in path.parts):
        continue
    for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
        if "://" in target or target.startswith("#"):
            continue
        links += 1
        if not (path.parent / target.split("#")[0]).exists():
            errors.append(f"{path.relative_to(ROOT)}: missing {target}")
manifest = json.loads((ROOT / "docs/help/manifest.json").read_text(encoding="utf-8"))
ids = [page["id"] for page in manifest["pages"]]
if len(ids) != len(set(ids)):
    errors.append("Duplicate help IDs")
for page in manifest["pages"]:
    if not (ROOT / "docs/help" / page["path"]).is_file():
        errors.append(f"Missing help topic {page['path']}")
if errors:
    raise SystemExit("\n".join(errors))
print(f"Checked {links} relative links and {len(ids)} help topics")
