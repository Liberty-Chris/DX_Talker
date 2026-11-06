"""Stable builds require owner-approved, hash-pinned legal text. Does not provide legal advice."""
import hashlib,json
from pathlib import Path

def check(root):
    folder=Path(root)/'docs/legal'
    record=json.loads((folder/'approved.json').read_text())
    if record.get('owner_approved') is not True:raise ValueError('Stable legal texts need explicit owner approval')
    for name in ('TERMS.txt','PRIVACY.txt'):
        raw=(folder/name).read_bytes()
        if not raw.strip() or hashlib.sha256(raw).hexdigest()!=record.get('sha256',{}).get(name):raise ValueError('Stable legal text is missing or changed: '+name)
if __name__=='__main__':check(Path(__file__).resolve().parent.parent)
