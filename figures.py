"""Paper figures. IEEE single-column, print/grayscale-safe.
Palette validated (all 6 checks PASS): #2b5fa8 #c25e00 #7a3a99 #3a7d44.
"""
import json
import random
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

random.seed(0)
BLUE, ORANGE, PURPLE, GREEN = "#2b5fa8", "#c25e00", "#7a3a99", "#3a7d44"
INK, MUTED = "#1a1a1a", "#5c5c5c"
plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Nimbus Roman", "DejaVu Serif"],
    "font.size": 8, "axes.labelsize": 8, "axes.titlesize": 8.5,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7,
    "axes.edgecolor": MUTED, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#dddddd", "grid.linewidth": 0.5,
    "figure.dpi": 300, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
    "pdf.fonttype": 42, "ps.fonttype": 42})  # embed TrueType, not Type 3 (IEEE PDF eXpress)
W1 = 3.4

grants = json.load(open("data/grants_scaled_classified.json"))


def cboot(rows, pred, nb=300):
    by = defaultdict(list)
    for r in rows:
        by[r["spender"]].append(r)
    sp = list(by)
    est = []
    for _ in range(nb):
        num = den = 0
        for _ in range(len(sp)):
            g = by[random.choice(sp)]
            den += len(g); num += sum(1 for r in g if pred(r))
        est.append(num / max(1, den))
    est.sort()
    p = sum(1 for r in rows if pred(r)) / len(rows)
    return p, est[int(.025*nb)], est[int(.975*nb)]


# ---- Fig 1: class distribution with cluster-bootstrap CI ----
fig, ax = plt.subplots(figsize=(W1, 1.9))
classes = [("MUTATED", ORANGE, "///"), ("PROXY_STABLE", BLUE, ""),
           ("EOA", PURPLE, "xxx")]
xs, ys, los, his = [], [], [], []
for i, (c, col, h) in enumerate(classes):
    p, lo, hi = cboot(grants, lambda r, c=c: r["cls"] == c)
    b = ax.bar(i, 100*p, color=col, width=0.6, edgecolor="white", hatch=h)
    ax.errorbar(i, 100*p, yerr=[[100*(p-lo)], [100*(hi-p)]], color=INK,
                capsize=3, lw=1)
    ax.text(i, 100*hi + 0.4, f"{100*p:.1f}%", ha="center", fontsize=7.5,
            color=INK, fontweight="bold")
ax.set_xticks(range(3))
ax.set_xticklabels([c[0].replace("_", "\n") for c in classes])
ax.set_ylabel("share of grants (%)")
ax.set_title("Spender trust-state (n=54,641), 95% cluster CI", pad=4)
ax.grid(axis="x", visible=False)
ax.set_ylim(0, 12)
fig.savefig("fig1_classes.png"); fig.savefig("fig1_classes.pdf")
plt.close(fig)

# ---- Fig 2: MUTATED upgrade authority (dangerous subclass) ----
from collections import Counter
mut=[r for r in grants if r["cls"]=="MUTATED"]
order=[("EOA-CONTROLLED",PURPLE,"xxx"),("MULTISIG",BLUE,""),
       ("TIMELOCK",GREEN,"..."),("CONTRACT-OTHER","#8a8a8a","///"),
       ("UNKNOWN","#c9c9c9","")]
cnt=Counter(r.get("upgrade_authority") for r in mut)
fig,ax=plt.subplots(figsize=(W1,2.0))
labels=[k for k,_,_ in order]; vals=[100*cnt.get(k,0)/len(mut) for k in labels]
cols=[c for _,c,_ in order]; hs=[h for _,_,h in order]
bars=ax.barh(range(len(labels)),vals,color=cols,edgecolor="white",height=0.62)
for b,h in zip(bars,hs): b.set_hatch(h)
for i,v in enumerate(vals): ax.text(v+0.7,i,f"{v:.1f}%",va="center",fontsize=7,color=INK)
ax.set_yticks(range(len(labels)))
ax.set_yticklabels(["EOA (single key)","multisig","timelock","other contract","unresolved"])
ax.invert_yaxis()
ax.set_xlabel("share of MUTATED grants (%)")
ax.set_title("Who can upgrade the code behind a live allowance", pad=4)
ax.grid(axis="y",visible=False); ax.set_xlim(0,55)
fig.savefig("fig2_authority.png"); fig.savefig("fig2_authority.pdf")
plt.close(fig)

# ---- Fig 3: unlimited-approval share by class ----
fig, ax = plt.subplots(figsize=(W1, 1.8))
cs = ["LIVE", "MUTATED", "EOA"]
cols = [GREEN, ORANGE, PURPLE]
vals = []
for c in cs:
    sub = [r for r in grants if r["cls"] == c]
    vals.append(100*sum(1 for r in sub if r["unlimited"])/len(sub))
bars = ax.bar(cs, vals, color=cols, width=0.6, edgecolor="white")
for b in bars:
    b.set_hatch(["", "///", "xxx"][bars.index(b)] if hasattr(bars, "index") else "")
for i, v in enumerate(vals):
    ax.text(i, v+1.5, f"{v:.0f}%", ha="center", fontsize=7.5, color=INK,
            fontweight="bold")
ax.set_ylabel("unlimited approvals (%)")
ax.set_title("Codeless (EOA) spenders skew to unlimited", pad=4)
ax.grid(axis="x", visible=False)
ax.set_ylim(0, 80)
fig.savefig("fig3_unlimited.png"); fig.savefig("fig3_unlimited.pdf")
plt.close(fig)

print("wrote fig1, fig2(authority), fig3")
