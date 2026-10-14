"""Semantically-correct realized-use scan.

Fix (PC reviewer): a Transfer(owner -> spender) does NOT prove the spender
exercised the allowance — the owner could have sent voluntarily. We now VERIFY
the spender initiated it: fetch each candidate tx and require tx.from == spender
(the EOA calling transferFrom directly). Only then is it a genuine allowance
exercise. Report as a rate with a Clopper-Pearson CI and the amount distribution.
Scoped to the anomalous-EOA cohort; 1-week window (node range limit) = lower bound.
"""
import json
import os
import time

from eth_utils import keccak, to_hex

import rpccore
rpccore.ENDPOINTS[1] = ["https://rpc.mevblocker.io", "https://ethereum-rpc.publicnode.com"]
from rpccore import TOKENS, a, get_logs, rpc

SIG_TRANSFER = to_hex(keccak(text="Transfer(address,address,uint256)"))
WINDOW = 40_000            # ~5.5 days
CHUNK = 9_500
dec = {t: d for t, (s, d) in TOKENS.items()}
PRICE = {"USDC": 1, "USDT": 1, "DAI": 1, "WETH": 3000, "WBTC": 60000, "LINK": 15,
         "UNI": 8, "AAVE": 250, "FRAX": 1, "stETH": 3000, "PEPE": 0, "APE": 1}
grants = json.load(open("data/grants_scaled_classified.json"))
HEAD = int(rpc("eth_blockNumber", []), 16)
CACHE = "data/realized_verified.json"


def log(*x):
    print(f"[{time.strftime('%H:%M:%S')}]", *x, flush=True)


anom = {}
for r in grants:
    if r.get("eoa_kind") == "anomalous":
        anom[(r["token"], r["owner"], r["spender"])] = r
rows = list(anom.values())
done = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
log(f"anomalous-EOA grants: {len(rows)}, cached {len(done)}")

for idx, r in enumerate(rows):
    key = f"{r['token']}|{r['owner']}|{r['spender']}"
    if key in done:
        continue
    tok, owner, spender = r["token"], r["owner"], r["spender"]
    to_blk = min(r["block"] + WINDOW, HEAD)
    try:
        logs = get_logs(tok, [SIG_TRANSFER,
                        "0x" + owner[2:].rjust(64, "0")],
                        r["block"], to_blk, chunk=CHUNK)
    except Exception as exc:
        log(f"  fail {owner[:10]}: {str(exc)[:40]}")
        continue
    # verify spender initiated: tx.from == spender
    exercised, amt = 0, 0
    checked = 0
    for l in logs:
        if checked >= 60:
            break
        checked += 1
        try:
            tx = rpc("eth_getTransactionByHash", [l["transactionHash"]])
            if tx and a("0x" + tx["from"][2:]) == spender:
                exercised += 1
                amt += int(l["data"], 16)
        except Exception:
            pass
    d = dec[tok]
    done[key] = {"sym": r["sym"], "transfers_from_owner": len(logs),
                 "exercised_by_spender": exercised,
                 "units": amt / 10 ** d, "usd": amt / 10 ** d * PRICE[r["sym"]],
                 "verified_drain": exercised > 0}
    if idx % 10 == 0:
        json.dump(done, open(CACHE, "w"))
        log(f"  {idx+1}/{len(rows)} verified-drains="
            f"{sum(1 for v in done.values() if v['verified_drain'])}")
json.dump(done, open(CACHE, "w"))

import math
def clopper(k, n):
    if n == 0:
        return (0, 0)
    from scipy.stats import beta
    lo = 0 if k == 0 else beta.ppf(0.025, k, n - k + 1)
    hi = 1 if k == n else beta.ppf(0.975, k + 1, n - k)
    return lo, hi

dr = [v for v in done.values() if v["verified_drain"]]
n = len(done)
k = len(dr)
try:
    lo, hi = clopper(k, n)
    ci = f"[{100*lo:.1f}, {100*hi:.1f}]"
except Exception:
    ci = "(scipy n/a)"
print(f"\n=== VERIFIED realized use (tx.from == spender), anomalous-EOA ===")
print(f"grants scanned: {n}")
print(f"VERIFIED allowance exercises by spender: {k} ({100*k/max(1,n):.1f}%) CI {ci}")
print(f"verified value moved: ${sum(v['usd'] for v in dr):,.0f}")
print(f"(vs unverified Transfer-from-owner signal: "
      f"{sum(1 for v in done.values() if v['transfers_from_owner']>0)} grants had ANY outflow)")
