import json
from authlib import resolve, SNAP
miss = [tuple(x) for x in json.load(open("auth_missing.json"))]
sp = sorted({s for s, _ in miss})
print("pairs", len(miss), "spenders", len(sp), flush=True)
now = resolve([(s, SNAP) for s in sp]); atg = resolve(miss)
json.dump(dict(now={s: v for (s, _), v in now.items()}, at_grant={f"{s}|{b}": v for (s, b), v in atg.items()}), open("authority4.json", "w"))
print("saved")
