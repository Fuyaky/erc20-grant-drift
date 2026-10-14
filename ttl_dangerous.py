"""TTL counterfactual on the SECURITY-RELEVANT dangerous subset.

The dangerous subset is the set of MUTATED grants whose real upgrade authority
resolved to a single code-less key (EOA-CONTROLLED in authority.json) -- the
Furucombo-shaped class. These are the grants where a malicious upgrade needs
only one key, so they are the ones a TTL is meant to protect.

For each such grant and each candidate TTL T, we read the EIP-1967
implementation slot at block(grant + T days). If it still equals impl@grant, the
implementation had NOT yet changed at T -- an allowance expiring at T would have
auto-retired the grant BEFORE its trust basis drifted. The reported percentage
is the fraction of dangerous drifted grants neutralized by a T-day expiry.

Every EOA-CONTROLLED MUTATED grant is a confirmed drift by construction
(classification already established impl@grant != impl@now), so valid == 298 and
no sub-sampling is applied. Reproduces data/ttl_dangerous.json.
"""
import json
import time

import rpccore
rpccore.ENDPOINTS[1] = ["https://eth.drpc.org", "https://rpc.mevblocker.io"]
from rpccore import IMPL_SLOT, a, batch, rpc

grants = json.load(open("data/grants_scaled_classified.json"))
authority = json.load(open("data/authority.json"))
IMPLG = {}
for k, v in json.load(open("data/impl_at_grant.json")).items():
    sp, bl = k.split("|")
    IMPLG[(sp, int(bl))] = v

BPD = 7160  # blocks per day
TTLS = [7, 30, 90, 180, 365]
HEAD = int(rpc("eth_blockNumber", []), 16)


def log(*x):
    print(f"[{time.strftime('%H:%M:%S')}]", *x, flush=True)


def label(sp):
    v = authority.get(sp)
    return (v.get("label") if isinstance(v, dict) else v) if v else None


# the dangerous subset: MUTATED grants whose upgrade authority is a single key
danger = [r for r in grants
          if r["cls"] == "MUTATED"
          and label(r["spender"]) == "EOA-CONTROLLED"
          and (r["spender"], r["block"]) in IMPLG]
log(f"dangerous (EOA-CONTROLLED MUTATED) grants: {len(danger)}")

# build the (grant_idx, ttl, block) archival read list
reads, meta = [], []
for gi, r in enumerate(danger):
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
        log(f"  {i + len(part)}/{len(reads)} reads")

per = {}
for k, (gi, tag) in enumerate(meta):
    per.setdefault(gi, {})[tag] = vals.get(k)

neutral = {T: 0 for T in TTLS}
valid = 0
for gi, r in enumerate(danger):
    ig = IMPLG.get((r["spender"], r["block"]))  # impl@grant; != impl@now by construction
    if ig is None:
        continue
    valid += 1
    d = per.get(gi, {})
    for T in TTLS:
        if d.get(T) == ig:            # impl unchanged at grant+T -> expiry beat the drift
            neutral[T] += 1

print("\n=== TTL counterfactual on the dangerous (single-key) subset ===")
out = []
for T in TTLS:
    pct = round(100 * neutral[T] / valid, 1) if valid else 0.0
    print(f"  TTL={T:3d}d  retires {pct:5.1f}% of dangerous drifted grants "
          f"before the implementation changed")
    out.append({"ttl": T, "pct": pct})

json.dump({"valid": valid, "ttl": out}, open("data/ttl_dangerous.json", "w"))
print(f"\nvalid={valid}; saved data/ttl_dangerous.json")
