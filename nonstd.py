"""MW4: non-EIP-1967 upgradeable spenders previously counted as plain contracts.
Beacon: beacon(slot)->implementation() at grant block vs snapshot.
Diamond (EIP-2535): hash of facets() at grant block vs snapshot.
Legacy ZeppelinOS slot: impl at grant block vs snapshot."""
import json, hashlib, time
import rpccore
rpccore.ENDPOINTS[1] = ["https://rpc.mevblocker.io", "https://eth.drpc.org"]
from rpccore import batch, a
SNAP = json.load(open("snapshot.json"))["block"]
P = json.load(open("probes.json"))
g = json.load(open("../data/grants_scaled_classified.json"))
BEACON = "0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50"
ZOS = "0x7050c9e0f4ca769c69bd3a8ef740bc37934f8e2c036e5a723fd8ee048ed3f8c3"
def kind(s):
    v = P[s]
    if v["diamond"]: return "diamond"
    if v["beacon"]: return "beacon"
    if v["zos"]: return "zos"
    return None
pairs = sorted({(r["spender"], r["block"]) for r in g if r["cls"] in ("LIVE", "PROXY_STABLE") and kind(r["spender"])})
sps = sorted({s for s, _ in pairs})
print("pairs", len(pairs), "spenders", len(sps), flush=True)
def B(calls):
    out = {}
    for i in range(0, len(calls), 80):
        part = calls[i:i+80]
        for _ in range(6):
            try: r = batch(part); break
            except Exception as e: print("retry", str(e)[:60], flush=True); time.sleep(5)
        else: r = {}
        for j, v in r.items(): out[i+j] = v
        time.sleep(0.2)
    return out
def state(items):  # items: (s, blk)
    c1 = []
    for s, b in items:
        k = kind(s)
        if k == "diamond": c1.append(("eth_call", [{"to": s, "data": "0x7a0ed627"}, hex(b)]))
        elif k == "beacon": c1.append(("eth_getStorageAt", [s, BEACON, hex(b)]))
        else: c1.append(("eth_getStorageAt", [s, ZOS, hex(b)]))
    r1 = B(c1)
    st, c2, idx = {}, [], []
    for i, (s, b) in enumerate(items):
        v = r1.get(i); k = kind(s)
        if v is None: st[(s, b)] = None; continue
        if k == "diamond": st[(s, b)] = hashlib.sha256(v.encode()).hexdigest()[:16] if v != "0x" else "empty"
        elif k == "zos": st[(s, b)] = a(v) if v != "0x" and int(v, 16) else "none"
        else:
            bc = a(v) if v != "0x" and int(v, 16) else None
            if bc: idx.append((s, b)); c2.append(("eth_call", [{"to": bc, "data": "0x5c60da1b"}, hex(b)]))
            else: st[(s, b)] = "nobeacon"
    r2 = B(c2)
    for i, k in enumerate(idx):
        v = r2.get(i); st[k] = a(v) if v and len(v) >= 66 else None
    return st
now = state([(s, SNAP) for s in sps]); print("now ok", flush=True)
atg = state(pairs); print("atg ok", flush=True)
json.dump({"now": {s: now[(s, SNAP)] for s in sps},
           "at_grant": {f"{s}|{b}": v for (s, b), v in atg.items()},
           "kind": {s: kind(s) for s in sps}}, open("nonstd.json", "w"))
print("saved")
