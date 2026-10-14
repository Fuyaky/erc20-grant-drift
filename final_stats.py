"""Revision statistics: reclassification (7702, deployed-after-grant, non-1967
proxies), standing/funded/exposed at snapshot, unlimited shares, authority at
grant vs now, governance parameters, EOA activity split, epoch/token tables."""
import json, random, math, statistics
from collections import Counter, defaultdict
random.seed(0)
g = json.load(open("../data/grants_scaled_classified.json"))
P = json.load(open("probes.json")); IN = json.load(open("impl_now.json"))
IG = json.load(open("../data/impl_at_grant.json"))
NS = json.load(open("nonstd.json")); S = json.load(open("snapshot.json"))
A2 = json.load(open("authority2.json")); A3 = json.load(open("authority3.json"))
import os
A4 = json.load(open("authority4.json")) if os.path.exists("authority4.json") else {"now": {}, "at_grant": {}}
PR = json.load(open("prices.json"))
PRICE = {"USDC": 1, "USDT": 1, "DAI": 1, "FRAX": PR["FRAX"], "WETH": PR["ETH"], "stETH": PR["STETH"],
         "WBTC": PR["BTC"], "LINK": PR["LINK"], "UNI": PR["UNI"], "AAVE": PR["AAVE"], "APE": PR["APE"], "PEPE": None}
DEC = {'USDC':6,'USDT':6,'DAI':18,'WETH':18,'WBTC':8,'LINK':18,'UNI':18,'AAVE':18,'FRAX':18,'stETH':18,'PEPE':18,'APE':18}
OUT = {}

def cls(r):
    s, b = r["spender"], r["block"]; p = P[s]
    if p["code_len"] == 0 or p["delegated7702"]:
        return "CODELESS"
    if "deploy_block" in p and b < p["deploy_block"]:
        return "DEPLOYED_LATER"
    k = f"{s}|{b}"
    if IN.get(s):                       # EIP-1967 proxy now
        was = IG.get(k)
        if was and was != IN[s]: return "MUTATED"
        return "PROXY_STABLE"
    if k in NS["at_grant"]:
        return "MUTATED" if NS["at_grant"][k] != NS["now"][s] else "PROXY_STABLE"
    return "NON_PROXY"

for r in g:
    r["c2"] = cls(r)
    r["unl"] = r["value"] >= 2**255 or (r["sym"] == "UNI" and r["value"] == 2**96 - 1)
    r["kind"] = ("1967" if IN.get(r["spender"]) else NS["kind"].get(r["spender"])) if r["c2"] in ("MUTATED", "PROXY_STABLE") else None
    r["allow"] = int(S["allow"][f"{r['token']}|{r['owner']}|{r['spender']}"])
    r["bal"] = int(S["bal"][f"{r['token']}|{r['owner']}"])
n = len(g)
CL = ["NON_PROXY", "PROXY_STABLE", "MUTATED", "CODELESS", "DEPLOYED_LATER"]
OUT["transition"] = Counter(f"{r['cls']}->{r['c2']}" for r in g)
print("transitions", OUT["transition"])

def cboot(rows, pred, nb=2000):
    by = defaultdict(list)
    for r in rows: by[r["spender"]].append(r)
    sp = list(by); est = []
    for _ in range(nb):
        num = den = 0
        for _ in range(len(sp)):
            q = by[random.choice(sp)]; den += len(q); num += sum(1 for r in q if pred(r))
        est.append(num / max(1, den))
    est.sort()
    return sum(1 for r in rows if pred(r)) / len(rows), est[int(.025*nb)], est[int(.975*nb)]

OUT["table1"] = {}
for c in CL:
    k = sum(r["c2"] == c for r in g)
    p, lo, hi = cboot(g, lambda r, c=c: r["c2"] == c) if c != "NON_PROXY" else (k/n, None, None)
    OUT["table1"][c] = dict(n=k, pct=100*p, lo=None if lo is None else 100*lo, hi=None if hi is None else 100*hi,
                            spenders=len({r["spender"] for r in g if r["c2"] == c}))
    print(c, OUT["table1"][c])
mut = [r for r in g if r["c2"] == "MUTATED"]
OUT["mut_by_kind"] = Counter(r["kind"] for r in mut)
OUT["stable_by_kind"] = Counter(r["kind"] for r in g if r["c2"] == "PROXY_STABLE")
OUT["codeless_7702"] = dict(spenders=sum(1 for s, v in P.items() if v["delegated7702"]),
                           grants=sum(1 for r in g if P[r["spender"]]["delegated7702"]))
OUT["deployed_later"] = sum(r["c2"] == "DEPLOYED_LATER" for r in g)
OUT["clones"] = dict(spenders=sum(v["clone1167"] for v in P.values()), grants=sum(P[r["spender"]]["clone1167"] for r in g))
# 1967 drift since collection
OUT["drift_since_collection"] = sum(1 for r in g if r["cls"] == "PROXY_STABLE" and r["c2"] == "MUTATED")
print("mut by kind", OUT["mut_by_kind"], "7702", OUT["codeless_7702"], "deployed later", OUT["deployed_later"])

# ---------- standing / funded / exposed (pair level, latest sampled grant per pair) ----------
last = {}
for r in sorted(g, key=lambda r: r["block"]):
    last[(r["token"], r["owner"], r["spender"])] = r
OUT["self_pairs"] = sum(1 for k in last if k[1] == k[2])
pairs = [r for k, r in last.items() if k[1] != k[2]]   # drop self-approvals (owner == spender)
def usd(r):
    pr = PRICE[r["sym"]]
    return None if pr is None else min(r["allow"], r["bal"]) / 10**DEC[r["sym"]] * pr
OUT["standing"] = {}
for c in CL + ["ALL"]:
    rows = [r for r in g if c == "ALL" or r["c2"] == c]
    pr = [r for r in pairs if c == "ALL" or r["c2"] == c]
    st = [r for r in pr if r["allow"] > 0]; fu = [r for r in st if r["bal"] > 0]
    ex = [usd(r) for r in fu if usd(r) is not None]
    OUT["standing"][c] = dict(grants=len(rows), pairs=len(pr), standing_pairs=len(st), funded_pairs=len(fu),
        standing_pct=100*len(st)/max(1, len(pr)), funded_pct=100*len(fu)/max(1, len(pr)),
        unl_standing_pct=100*sum(1 for r in st if r["allow"] >= 2**200 or (r["sym"]=="UNI" and r["allow"]>=2**95))/max(1, len(pr)),
        exposed_usd=sum(ex), median_exposed=statistics.median(ex) if ex else 0,
        grant_standing_pct=100*sum(1 for r in rows if r["allow"] > 0)/max(1, len(rows)))
    print(c, {k: (round(v, 1) if isinstance(v, float) else v) for k, v in OUT["standing"][c].items()})
# owner-level de-duplicated exposure: per (token, owner) min(bal, max standing allowance)
tow = defaultdict(lambda: [0, 0, None])
for r in pairs:
    if r["allow"] > 0:
        t = tow[(r["token"], r["owner"])]; t[0] = max(t[0], r["allow"]); t[1] = r["bal"]; t[2] = r["sym"]
tot = sum(min(a, b)/10**DEC[s]*PRICE[s] for a, b, s in tow.values() if PRICE[s])
OUT["exposed_total_dedup_usd"] = tot
print("dedup exposed total", round(tot))
# top concentration of exposure
OUT["exposed_top_spenders"] = Counter()
for r in pairs:
    if r["allow"] > 0 and r["bal"] > 0 and usd(r): OUT["exposed_top_spenders"][r["spender"]] += usd(r)
OUT["exposed_top_spenders"] = OUT["exposed_top_spenders"].most_common(10)
ex = sorted([usd(r) for r in pairs if r["allow"] > 0 and r["bal"] > 0 and usd(r)], reverse=True)
OUT["exposure_dist"] = dict(n=len(ex), total=sum(ex), top1=ex[0], top10=sum(ex[:10]), ge1k=sum(x >= 1000 for x in ex), ge100k=sum(x >= 1e5 for x in ex), median=statistics.median(ex))
print("exposure dist", OUT["exposure_dist"])

# ---------- unlimited share by class ----------
OUT["unlimited"] = {c: 100*sum(r["unl"] for r in g if r["c2"] == c)/max(1, sum(r["c2"] == c for r in g)) for c in CL}
print("unlimited", {k: round(v, 1) for k, v in OUT["unlimited"].items()})

# ---------- codeless activity split (nonce at snapshot) ----------
def act(s):
    nn = P[s]["nonce"]
    return "dormant(<10)" if nn < 10 else "low(10-999)" if nn < 1000 else "operator(>=1000)"
cg = [r for r in g if r["c2"] == "CODELESS"]
OUT["codeless_split"] = {}
for k in ["operator(>=1000)", "low(10-999)", "dormant(<10)"]:
    rows = [r for r in cg if act(r["spender"]) == k]
    pr = [r for r in pairs if r["c2"] == "CODELESS" and act(r["spender"]) == k]
    fu = [r for r in pr if r["allow"] > 0 and r["bal"] > 0]
    OUT["codeless_split"][k] = dict(grants=len(rows), spenders=len({r["spender"] for r in rows}),
        unl_pct=100*sum(r["unl"] for r in rows)/max(1, len(rows)),
        funded_pairs=len(fu), exposed_usd=sum(usd(r) or 0 for r in fu))
    print(k, OUT["codeless_split"][k])
top = Counter(r["spender"] for r in cg)
OUT["codeless_top1_pct"] = 100*top.most_common(1)[0][1]/len(cg)
OUT["codeless_top10_pct"] = 100*sum(v for _, v in top.most_common(10))/len(cg)

# ---------- authority now vs at grant ----------
_AN = {**A2["now"], **A3["now"], **A4["now"]}; _AG = {**A2["at_grant"], **A3["at_grant"], **A4["at_grant"]}
miss = sorted({(r["spender"], r["block"]) for r in mut if r["spender"] not in _AN or f"{r['spender']}|{r['block']}" not in _AG})
json.dump(miss, open("auth_missing.json", "w")); print("authority missing pairs", len(miss))
AN = {**A2["now"], **A3["now"], **A4["now"]}; AG = {**A2["at_grant"], **A3["at_grant"], **A4["at_grant"]}
for r in mut:
    r["auth_now"] = AN[r["spender"]]["label"]; r["auth_grant"] = AG[f"{r['spender']}|{r['block']}"]["label"]
OUT["auth_now"] = Counter(r["auth_now"] for r in mut); OUT["auth_grant"] = Counter(r["auth_grant"] for r in mut)
OUT["auth_cross"] = Counter(f"{r['auth_grant']}->{r['auth_now']}" for r in mut)
OUT["auth_paths_now"] = Counter(AN[r["spender"]]["path"] for r in mut)
OUT["auth_spenders_now"] = Counter(AN[s]["label"] for s in {r["spender"] for r in mut})
OUT["single_key_either"] = sum(1 for r in mut if "EOA-CONTROLLED" in (r["auth_now"], r["auth_grant"]))
print("auth now", OUT["auth_now"]); print("auth grant", OUT["auth_grant"]); print("cross", OUT["auth_cross"])
print("paths", OUT["auth_paths_now"]); print("spenders", OUT["auth_spenders_now"])
OUT["gov"] = A2["gov"]
json.dump(OUT, open("final_stats.json", "w"), indent=1, default=str)
# per-grant derived labels for the artifact
json.dump([{k: r[k] for k in ("token","sym","owner","spender","block","age","value","cls","c2","unl","kind","allow","bal")}
           | {"auth_now": r.get("auth_now"), "auth_grant": r.get("auth_grant")} for r in g],
          open("grants_revised.json", "w"), default=str)

# ---------- epoch / token tables ----------
print("\nEPOCH")
for a in ["0.25y","0.5y","1.0y","1.5y","2.0y"]:
    s = [r for r in g if r["age"] == a]; c = Counter(r["c2"] for r in s)
    print(a, len(s), len({r['spender'] for r in s}), *["%.1f" % (100*c[k]/len(s)) for k in ["MUTATED","PROXY_STABLE","CODELESS"]],
          "standing %.1f" % (100*sum(r['allow']>0 for r in s)/len(s)))
print("TOKEN")
for t, _ in Counter(r["sym"] for r in g).most_common():
    s = [r for r in g if r["sym"] == t]; c = Counter(r["c2"] for r in s)
    print(t, len(s), *["%.1f" % (100*c[k]/len(s)) for k in ["MUTATED","PROXY_STABLE","CODELESS"]], "unl %.1f" % (100*sum(r['unl'] for r in s)/len(s)))
