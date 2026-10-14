"""MW4/MW5: per-spender probes.
 - code now (EIP-7702 delegation designator 0xef0100||addr detected), nonce now
 - code at the spender's earliest grant block (deployed-after-grant detection),
   and binary-searched deployment block for those
 - non-EIP-1967 upgradeability now: beacon slot, EIP-1822 PROXIABLE slot,
   legacy ZeppelinOS slot, Diamond facetAddresses(); EIP-1167 clone prefix."""
import json, os, time
from collections import defaultdict
import rpccore
rpccore.ENDPOINTS[1] = ["https://eth.drpc.org", "https://rpc.mevblocker.io"]
from rpccore import batch, rpc, a

grants = json.load(open("../data/grants_scaled_classified.json"))
SNAP = json.load(open("snapshot.json"))["block"] if os.path.exists("snapshot.json") else None
B = hex(SNAP) if SNAP else "latest"
first = defaultdict(lambda: 10**12)
for r in grants:
    first[r["spender"]] = min(first[r["spender"]], r["block"])
sp = sorted(first)
SLOTS = {"beacon": "0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50",
         "uups1822": "0xc5f16f0fcc639fa48a6947836d9850f504798523bf8c9a3a87d5876cf622bcf7",
         "zos": "0x7050c9e0f4ca769c69bd3a8ef740bc37934f8e2c036e5a723fd8ee048ed3f8c3"}
OUT = "probes.json"
P = json.load(open(OUT)) if os.path.exists(OUT) else {}

def B100(calls):
    for _ in range(5):
        try: return batch(calls)
        except Exception as e: print("retry", e, flush=True); time.sleep(4)
    return {}

todo = [s for s in sp if s not in P or P[s].get("code_at_first_grant") is None]
for i in range(0, len(todo), 14):
    part = todo[i:i+14]
    calls = []
    for s in part:
        calls += [("eth_getCode", [s, B]), ("eth_getTransactionCount", [s, B]),
                  ("eth_getCode", [s, hex(first[s])])]
        calls += [("eth_getStorageAt", [s, v, B]) for v in SLOTS.values()]
        calls += [("eth_call", [{"to": s, "data": "0x52ef6b2c"}, B])]
    res = B100(calls)
    k = 7
    for j, s in enumerate(part):
        o = j * k
        if o not in res or (o+1) not in res: continue
        code = res.get(o, "0x") or "0x"
        P[s] = {"code_len": (len(code)-2)//2,
                "delegated7702": code.startswith("0xef0100"),
                "delegate": ("0x"+code[8:48]) if code.startswith("0xef0100") else None,
                "clone1167": code.startswith("0x363d3d373d3d3d363d73"),
                "nonce": int(res.get(o+1, "0x0") or "0x0", 16),
                "code_at_first_grant": ((len(res[o+2])-2)//2) if (o+2) in res else None,
                "first_grant_block": first[s]}
        for n, kk in zip(SLOTS, range(3, 6)):
            v = res.get(o+kk)
            P[s][n] = a(v) if v and v != "0x" and int(v, 16) != 0 else None
        fa = res.get(o+6)
        P[s]["diamond"] = bool(fa and len(fa) > 130)
    json.dump(P, open(OUT, "w"))
    print(i+len(part), "/", len(todo), flush=True)

# deployment block for spenders with code now but none at first grant
need = [s for s, v in P.items() if v["code_len"] > 0 and not v["delegated7702"]
        and v["code_at_first_grant"] == 0 and "deploy_block" not in v]
print("deployed-after-first-grant spenders:", len(need), flush=True)
for s in need:
    lo, hi = P[s]["first_grant_block"], SNAP
    while hi - lo > 1:
        mid = (lo + hi) // 2
        try: c = rpc("eth_getCode", [s, hex(mid)])
        except Exception: time.sleep(2); continue
        if c and c != "0x": hi = mid
        else: lo = mid
    P[s]["deploy_block"] = hi
    json.dump(P, open(OUT, "w"))
print("done")
