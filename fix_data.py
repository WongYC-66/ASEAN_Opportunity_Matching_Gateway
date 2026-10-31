import json
from pathlib import Path

startups = json.loads(Path("backend/app/data/startups.json").read_text())
for s in startups:
    if s.get('fundingSought') is not None and s.get('fundingCurrency') is None:
        s['fundingCurrency'] = 'USD'
    if s.get('fundingSought') is None and s.get('fundingCurrency') is not None:
        s['fundingCurrency'] = None
Path("backend/app/data/startups.json").write_text(json.dumps(startups, indent=2))
print('fixed')
