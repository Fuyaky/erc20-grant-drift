"""Classify the scaled 54k-grant sample. Reuses spender_info cache; classifies
new spenders (code + EIP-1967 impl now), then impl@grant for proxies and
historical code for codeless spenders. Resumable.
"""
import json
import os
import time
from collections import defaultdict

from rpccore import IMPL_SLOT, a, batch, rpc

OUT = "data"
grants = json.load(open(f"{OUT}/grants_scaled.json"))
malicious = set(json.load(open(f"{OUT}/malicious.json")))
info = json.load(open(f"{OUT}/spender_info.json"))
dead_class = json.load(open(f"{OUT}/dead_class.json")) if os.path.exists(f"{OUT}/dead_class.json") else {}
impl_at_grant = {}
if os.path.exists(f"{OUT}/impl_at_grant.json"):
    for k, v in json.load(open(f"{OUT}/impl_at_grant.json")).items():
        sp, bl = k.split("|"); impl_at_grant[(sp, int(bl))] = v


def log(*x):
    print(f"[{time.strftime('%H:%M:%S')}]", *x, flush=True)


# 1. classify NEW spenders (code_len + impl now)
spenders = {r["spender"] for r in grants}
new = [s for s in spenders if s not in info]
log(f"new spenders to classify: {len(new)}")
for i in range(0, len(new), 100):
    part = new[i:i + 100]
    codes = batch([("eth_getCode", [x, "latest"]) for x in part])
    slots = batch([("eth_getStorageAt", [x, IMPL_SLOT, "latest"]) for x in part])
    for j, x in enumerate(part):
        code = codes.get(j, "0x")
        slot = slots.get(j, "0x" + "0" * 64)
        impl = a(slot) if slot and int(slot, 16) != 0 else None
        info[x] = {"code_len": (len(code) - 2) // 2 if code else 0, "impl": impl}
    if i % 500 == 0:
        json.dump(info, open(f"{OUT}/spender_info.json", "w"))
        log(f"  {i+len(part)}/{len(new)}")
json.dump(info, open(f"{OUT}/spender_info.json", "w"))

# 2. historical code for codeless spenders (EOA vs DESTRUCTED)
dead_first = defaultdict(lambda: 10 ** 12)
for r in grants:
    s = r["spender"]
    if info.get(s, {}).get("code_len", 1) == 0:
        dead_first[s] = min(dead_first[s], r["block"])
todo = [(s, b) for s, b in dead_first.items() if s not in dead_class]
log(f"codeless spenders needing historical code: {len(todo)}")
for i in range(0, len(todo), 80):
    part = todo[i:i + 80]
    codes = batch([("eth_getCode", [s, hex(b)]) for s, b in part])
    for j, (s, b) in enumerate(part):
        c = codes.get(j, "0x")
        dead_class[s] = "DESTRUCTED" if (c and c != "0x") else "EOA"
    json.dump(dead_class, open(f"{OUT}/dead_class.json", "w"))
json.dump(dead_class, open(f"{OUT}/dead_class.json", "w"))

# 3. impl@grant for proxy grants
pg = list({(r["spender"], r["block"]) for r in grants
           if info.get(r["spender"], {}).get("impl")})
pg = [(s, b) for s, b in pg if (s, b) not in impl_at_grant]
log(f"proxy grants needing impl@grant: {len(pg)}")
for i in range(0, len(pg), 80):
    part = pg[i:i + 80]
    res = batch([("eth_getStorageAt", [s, IMPL_SLOT, hex(b)]) for s, b in part])
    for j, (s, b) in enumerate(part):
        slot = res.get(j)
        impl_at_grant[(s, b)] = a(slot) if slot and int(slot, 16) != 0 else None
    if i % 800 == 0:
        json.dump({f"{s}|{b}": v for (s, b), v in impl_at_grant.items()},
                  open(f"{OUT}/impl_at_grant.json", "w"))
        log(f"  {i+len(part)}/{len(pg)}")
json.dump({f"{s}|{b}": v for (s, b), v in impl_at_grant.items()},
          open(f"{OUT}/impl_at_grant.json", "w"))


def classify(r):
    s = r["spender"]
    si = info.get(s, {})
    if si.get("code_len", 1) == 0:
        return dead_class.get(s, "EOA")
    if si.get("impl"):
        was = impl_at_grant.get((s, r["block"]))
        now = si.get("impl")
        if was and now and was != now:
            return "MUTATED"
        return "PROXY_STABLE"
    return "LIVE"


for r in grants:
    r["cls"] = classify(r)
    r["malicious"] = r["spender"] in malicious
    r["unlimited"] = r["value"] >= 2 ** 255
json.dump(grants, open(f"{OUT}/grants_scaled_classified.json", "w"))

from collections import Counter
print("\n=== scaled class distribution (54k) ===")
n = len(grants)
for c, k in Counter(r["cls"] for r in grants).most_common():
    print(f"  {c:12s} {k:6d}  ({100*k/n:.1f}%)")
print(f"\nmalicious grants: {sum(1 for r in grants if r['malicious'])}")
