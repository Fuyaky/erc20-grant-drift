"""Etap 1.3-1.4: cluster-bootstrap CIs (resample distinct spenders, not grants)
and class-share-by-age curve. Pure computation, no RPC.
"""
import json
import random
from collections import defaultdict

random.seed(0)
grants = json.load(open("data/grants_scaled_classified.json"))
N = len(grants)


def cluster_bootstrap(rows, predicate, n_boot=2000):
    """Resample distinct spenders with replacement; each carries its grants.
    Returns (point, lo, hi) for the fraction satisfying predicate."""
    by_sp = defaultdict(list)
    for r in rows:
        by_sp[r["spender"]].append(r)
    spenders = list(by_sp)
    point = sum(1 for r in rows if predicate(r)) / max(1, len(rows))
    ests = []
    for _ in range(n_boot):
        num = den = 0
        for _ in range(len(spenders)):
            g = by_sp[random.choice(spenders)]
            den += len(g)
            num += sum(1 for r in g if predicate(r))
        ests.append(num / max(1, den))
    ests.sort()
    return point, ests[int(0.025 * n_boot)], ests[int(0.975 * n_boot)]


print("=== class shares with cluster-bootstrap 95% CI (54,641 grants) ===")
for cls in ["MUTATED", "EOA", "PROXY_STABLE"]:
    p, lo, hi = cluster_bootstrap(grants, lambda r, c=cls: r["cls"] == c)
    print(f"  {cls:12s} {100*p:5.2f}%  [{100*lo:4.2f}, {100*hi:4.2f}]")

# naive (grant-level) CI for contrast — shows how much narrower it wrongly is
import math
def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z*z/n
    c = p + z*z/(2*n); m = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))
    return ((c-m)/d, (c+m)/d)
for cls in ["MUTATED", "EOA"]:
    k = sum(1 for r in grants if r["cls"] == cls)
    lo, hi = wilson(k, N)
    print(f"  (naive Wilson {cls}: [{100*lo:.2f}, {100*hi:.2f}] — too narrow, "
          f"ignores spender clustering)")

print("\n=== class share by grant age (cluster-bootstrap CI) ===")
ages = ["0.25y", "0.5y", "1.0y", "1.5y", "2.0y"]
for age in ages:
    sub = [r for r in grants if r["age"] == age]
    pm, lm, hm = cluster_bootstrap(sub, lambda r: r["cls"] == "MUTATED", 1000)
    pe, le, he = cluster_bootstrap(sub, lambda r: r["cls"] == "EOA", 1000)
    print(f"  {age:6s} n={len(sub):5d}  MUTATED {100*pm:4.1f}% [{100*lm:.1f},{100*hm:.1f}]"
          f"   EOA {100*pe:4.1f}% [{100*le:.1f},{100*he:.1f}]")

print("\n=== unlimited-approval share by class ===")
for cls in ["LIVE", "MUTATED", "EOA"]:
    sub = [r for r in grants if r["cls"] == cls]
    unl = sum(1 for r in sub if r["unlimited"])
    print(f"  {cls:12s} {100*unl/len(sub):.1f}% unlimited")

# concentration: how many distinct spenders carry MUTATED / EOA
for cls in ["MUTATED", "EOA"]:
    sub = [r for r in grants if r["cls"] == cls]
    sp = defaultdict(int)
    for r in sub:
        sp[r["spender"]] += 1
    top = sorted(sp.values(), reverse=True)
    print(f"\n{cls}: {len(sub)} grants across {len(sp)} spenders; "
          f"top-1 spender = {100*top[0]/len(sub):.1f}%, "
          f"top-5 = {100*sum(top[:5])/len(sub):.1f}%")

json.dump({"n": N}, open("data/stats_meta.json", "w"))
