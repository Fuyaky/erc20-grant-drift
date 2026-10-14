"""TTL counterfactual over the revised MUTATED set (EIP-1967, Diamond, beacon,
legacy slot). For grant g and TTL T, read the proxy state at block(g)+T days;
if it still equals the state at the grant, an allowance expiring at T would have
lapsed before the code changed. Random sample of 400 (seed 0) + optional subset."""
import json, random, sys, time, hashlib
import rpccore
rpccore.ENDPOINTS[1] = ["https://rpc.mevblocker.io", "https://eth.drpc.org"]
from rpccore import batch, a, IMPL_SLOT
random.seed(0)
BPD, TTLS = 7160, [7, 30, 90, 180, 365]
SNAP = json.load(open("snapshot.json"))["block"]
P = json.load(open("probes.json")); IN = json.load(open("impl_now.json"))
IG = json.load(open("../data/impl_at_grant.json")); NS = json.load(open("nonstd.json"))
BEACON = "0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50"
ZOS = "0x7050c9e0f4ca769c69bd3a8ef740bc37934f8e2c036e5a723fd8ee048ed3f8c3"
mode = sys.argv[1] if len(sys.argv) > 1 else "sample"
g = json.load(open("grants_revised.json"))
mut = [r for r in g if r["c2"] == "MUTATED"]
if mode == "sample":
    rows = random.sample(mut, 400)
else:
    rows = [r for r in mut if "EOA-CONTROLLED" in (r["auth_now"], r["auth_grant"])]
print(mode, len(rows), flush=True)
def B(calls):
    out = {}
    for i in range(0, len(calls), 80):
        part = calls[i:i+80]
        for _ in range(6):
            try: r = batch(part); break
            except Exception as e: time.sleep(5)
        else: r = {}
        for j, v in r.items(): out[i+j] = v
        time.sleep(0.2)
    return out
def ref(r):
    k = f"{r['spender']}|{r['block']}"
    return IG.get(k) if r["kind"] == "1967" else NS["at_grant"].get(k)
items = []
for gi, r in enumerate(rows):
    for T in TTLS:
        items.append((gi, T, r["spender"], r["kind"], min(r["block"] + T*BPD, SNAP)))
c1 = []
for gi, T, s, k, b in items:
    if k == "1967": c1.append(("eth_getStorageAt", [s, IMPL_SLOT, hex(b)]))
    elif k == "diamond": c1.append(("eth_call", [{"to": s, "data": "0x7a0ed627"}, hex(b)]))
    elif k == "beacon": c1.append(("eth_getStorageAt", [s, BEACON, hex(b)]))
    else: c1.append(("eth_getStorageAt", [s, ZOS, hex(b)]))
r1 = B(c1); c2, idx = [], []
val = {}
for i, (gi, T, s, k, b) in enumerate(items):
    v = r1.get(i)
    if v is None: val[i] = None; continue
    if k == "1967": val[i] = a(v) if v != "0x" and int(v, 16) else None
    elif k == "diamond": val[i] = hashlib.sha256(v.encode()).hexdigest()[:16] if v != "0x" else "empty"
    elif k == "zos": val[i] = a(v) if v != "0x" and int(v, 16) else "none"
    else:
        bc = a(v) if v != "0x" and int(v, 16) else None
        if bc: idx.append(i); c2.append(("eth_call", [{"to": bc, "data": "0x5c60da1b"}, hex(b)]))
        else: val[i] = "nobeacon"
r2 = B(c2)
for j, i in enumerate(idx):
    v = r2.get(j); val[i] = a(v) if v and len(v) >= 66 else None
per = {}
for i, (gi, T, s, k, b) in enumerate(items):
    per.setdefault(gi, {})[T] = val.get(i)
res, valid = [], 0
ok = [gi for gi in per if all(per[gi][T] is not None for T in TTLS) and ref(rows[gi]) is not None]
for T in TTLS:
    neut = sum(1 for gi in ok if per[gi][T] == ref(rows[gi]))
    res.append({"ttl": T, "pct": round(100*neut/len(ok), 1)})
out = {"valid": len(ok), "ttl": res, "by_kind": dict(__import__("collections").Counter(rows[gi]["kind"] for gi in ok))}
json.dump(out, open(f"ttl3_{mode}.json", "w")); print(out)
