import json, statistics
from collections import Counter
from authlib import B, call, SNAP, THRESH, OWNERS, MINDELAY, DELAY, GETDELAY
g = json.load(open("grants_revised.json"))
AN = {}
for f in ["authority2.json", "authority3.json", "authority4.json"]: AN.update(json.load(open(f))["now"])
mut = [r for r in g if r["c2"] == "MUTATED"]
ctrls = sorted({AN[r["spender"]]["controller"] for r in mut if r["auth_now"] in ("MULTISIG", "TIMELOCK")})
calls = []
for c in ctrls: calls += [call(c, THRESH, SNAP), call(c, OWNERS, SNAP), call(c, MINDELAY, SNAP), call(c, DELAY, SNAP), call(c, GETDELAY, SNAP)]
r = B(calls); gov = {}
for i, c in enumerate(ctrls):
    o = i*5; th, ow = r.get(o), r.get(o+1)
    dl = [int(r[o+j], 16) for j in (2, 3, 4) if r.get(o+j) not in (None, "0x") and len(r[o+j]) == 66]
    gov[c] = dict(threshold=int(th, 16) if th not in (None, "0x") and len(th) == 66 else None,
                  n_owners=int(ow[66:130], 16) if ow and len(ow) >= 130 else None, delay_s=max(dl) if dl else None)
json.dump(gov, open("gov.json", "w"), indent=1)
ms = [(gov[AN[r["spender"]]["controller"]], r) for r in mut if r["auth_now"] == "MULTISIG"]
tl = [(gov[AN[r["spender"]]["controller"]], r) for r in mut if r["auth_now"] == "TIMELOCK"]
print("multisig grants", len(ms), "thresholds", Counter((d["threshold"], d["n_owners"]) for d, _ in ms).most_common(8))
print("  th>=2", sum(bool(d["threshold"] and d["threshold"] >= 2) for d, _ in ms), "th>=3", sum(bool(d["threshold"] and d["threshold"] >= 3) for d, _ in ms), "th==1", sum(d["threshold"] == 1 for d, _ in ms))
print("timelock grants", len(tl), Counter(d["delay_s"] for d, _ in tl).most_common(10))
ds = [d["delay_s"] for d, _ in tl if d["delay_s"] is not None]
print("  median delay h", statistics.median(ds)/3600 if ds else None, ">=24h", sum(x >= 86400 for x in ds), ">=48h", sum(x >= 172800 for x in ds), "<1h", sum(x < 3600 for x in ds))
print("controllers", Counter((v["threshold"], v["n_owners"], v["delay_s"]) for v in gov.values()).most_common(12))
