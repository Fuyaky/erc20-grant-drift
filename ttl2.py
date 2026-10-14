"""TTL counterfactual, cheap batched version.

For each MUTATED grant and each candidate TTL T, read the EIP-1967 impl slot at
block(grant + T days). If it still equals impl@grant, the implementation had NOT
yet changed at T -- so an allowance expiring at T would have auto-retired the
grant BEFORE its trust basis drifted. Fraction of drifted grants neutralized by
T = fraction where impl@(grant+T) == impl@grant.
Batched: 5 reads/grant, no bisection.
"""
import json
import random
import time

import rpccore
rpccore.ENDPOINTS[1] = ["https://eth.drpc.org", "https://rpc.mevblocker.io"]
from rpccore import IMPL_SLOT, a, batch, rpc

random.seed(0)
grants = json.load(open("data/grants_scaled_classified.json"))
info = json.load(open("data/spender_info.json"))
IMPLG = {}
for k, v in json.load(open("data/impl_at_grant.json")).items():
    sp, bl = k.split("|"); IMPLG[(sp, int(bl))] = v
BPD = 7160  # blocks per day
TTLS = [7, 30, 90, 180, 365]
HEAD = int(rpc("eth_blockNumber", []), 16)


def log(*x):
    print(f"[{time.strftime('%H:%M:%S')}]", *x, flush=True)


mut = [r for r in grants if r["cls"] == "MUTATED"]
mut = [r for r in mut if (r["spender"], r["block"]) in IMPLG]
sample = random.sample(mut, min(400, len(mut)))
log(f"MUTATED {len(mut)}, sampling {len(sample)}")

# build (grant_idx, ttl, block) read list
reads = []
meta = []
for gi, r in enumerate(sample):
    for T in TTLS:
        b = min(r["block"] + T * BPD, HEAD)
        reads.append((r["spender"], b))
        meta.append((gi, T))

vals = {}
for i in range(0, len(reads), 90):
    part = reads[i:i + 90]
    res = batch([("eth_getStorageAt", [s, IMPL_SLOT, hex(b)]) for s, b in part])
    for j in range(len(part)):
        slot = res.get(j)
        vals[i + j] = a(slot) if slot and int(slot, 16) != 0 else None
    if (i // 90) % 5 == 0:
        log(f"  {i+len(part)}/{len(reads)} reads")

# assemble per grant
per = {}
for k, (gi, tag) in enumerate(meta):
    per.setdefault(gi, {})[tag] = vals.get(k)

# a grant counts only if it genuinely drifted (impl@grant != impl@now)
neutral = {T: 0 for T in TTLS}
valid = 0
for gi, r in enumerate(sample):
    d = per.get(gi, {})
    ig = IMPLG.get((r["spender"], r["block"]))
    now = info.get(r["spender"], {}).get("impl")
    if ig is None or now is None or ig == now:
        continue  # not a confirmed drift with readable archival state
    valid += 1
    for T in TTLS:
        if d.get(T) == ig:      # impl unchanged at grant+T -> expiry beat the drift
            neutral[T] += 1

log(f"confirmed-drift grants with archival reads: {valid}")
print("\n=== TTL counterfactual: % of drifted-trust grants neutralized ===")
res = []
for T in TTLS:
    pct = 100 * neutral[T] / valid if valid else 0
    print(f"  TTL={T:3d}d  neutralizes {pct:5.1f}% of drifted grants "
          f"(expiry preceded the implementation change)")
    res.append({"ttl": T, "neutralized_pct": round(pct, 1)})

# re-approval cost proxy
rv = json.load(open("data/realized_verified.json"))
used = sum(1 for v in rv.values() if v.get("verified_drain"))
print(f"\nre-approval cost: only {used}/{len(rv)} scanned grants were exercised "
      f"at all; a TTL forces re-approval on the actively-used minority.")
json.dump({"valid": valid, "ttl": res}, open("data/ttl.json", "w"))
print("saved data/ttl.json")
