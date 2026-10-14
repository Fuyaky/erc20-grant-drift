"""Authority (at grant block and at snapshot) for non-EIP-1967 proxies whose
code changed after the grant (Diamond facets / beacon / legacy slot)."""
import json
from authlib import resolve, SNAP, grants
N = json.load(open("nonstd.json"))
mutg = [r for r in grants if f"{r['spender']}|{r['block']}" in N["at_grant"]
        and N["at_grant"][f"{r['spender']}|{r['block']}"] != N["now"][r["spender"]]]
pairs = sorted({(r["spender"], r["block"]) for r in mutg})
sp = sorted({s for s, _ in pairs})
print("pairs", len(pairs), "spenders", len(sp), flush=True)
now = resolve([(s, SNAP) for s in sp]); print("now", flush=True)
atg = resolve(pairs)
json.dump(dict(now={s: v for (s, _), v in now.items()}, at_grant={f"{s}|{b}": v for (s, b), v in atg.items()}),
          open("authority3.json", "w"))
print("saved")
