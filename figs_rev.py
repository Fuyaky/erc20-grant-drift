"""Revised figures 1-4 (IEEE single column, print/grayscale-safe, TrueType)."""
import json, random
from collections import defaultdict, Counter
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
random.seed(0)
BLUE, ORANGE, PURPLE, GREEN, GREY, LGREY = "#2b5fa8", "#c25e00", "#7a3a99", "#3a7d44", "#8a8a8a", "#c9c9c9"
INK, MUTED = "#1a1a1a", "#5c5c5c"
plt.rcParams.update({"font.family": "serif", "font.serif": ["Liberation Serif", "DejaVu Serif"],
    "font.size": 8, "axes.labelsize": 8, "axes.titlesize": 8.5, "xtick.labelsize": 7, "ytick.labelsize": 7,
    "legend.fontsize": 7, "axes.edgecolor": MUTED, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#dddddd", "grid.linewidth": 0.5, "figure.dpi": 300,
    "savefig.bbox": "tight", "savefig.pad_inches": 0.02, "pdf.fonttype": 42, "ps.fonttype": 42})
W1 = 3.4
O = json.load(open("final_stats.json")); g = json.load(open("grants_revised.json"))
T = O["table1"]
# Fig 1
fig, ax = plt.subplots(figsize=(W1, 1.85))
cl = [("MUTATED", "Mutated", ORANGE, "///"), ("PROXY_STABLE", "Proxy-stable", BLUE, ""), ("CODELESS", "Code-less", PURPLE, "xxx")]
for i, (k, lab, col, h) in enumerate(cl):
    p, lo, hi = T[k]["pct"], T[k]["lo"], T[k]["hi"]
    ax.bar(i, p, color=col, width=0.6, edgecolor="white", hatch=h)
    ax.errorbar(i, p, yerr=[[p-lo], [hi-p]], color=INK, capsize=3, lw=1)
    ax.text(i+0.33, p, f"{p:.1f}%", ha="left", va="center", fontsize=7.5, color=INK, fontweight="bold")
ax.set_xticks(range(3)); ax.set_xticklabels([c[1] for c in cl]); ax.set_xlim(-0.5, 2.8)
ax.set_ylabel("share of grants (%)"); ax.set_ylim(0, 19)

fig.savefig("fig1_classes.pdf"); fig.savefig("fig1_classes.png"); plt.close(fig)
# Fig 2: authority at grant vs now
mut = [r for r in g if r["c2"] == "MUTATED"]
order = [("EOA-CONTROLLED", "single key"), ("MULTISIG", "multisig"), ("TIMELOCK", "timelock"),
         ("CONTRACT-OTHER", "other contract"), ("UNKNOWN", "unresolved")]
cg = Counter(r["auth_grant"] for r in mut); cn = Counter(r["auth_now"] for r in mut)
fig, ax = plt.subplots(figsize=(W1, 2.0)); hgt = 0.38
for i, (k, lab) in enumerate(order):
    vg, vn = 100*cg[k]/len(mut), 100*cn[k]/len(mut)
    ax.barh(i-hgt/2, vg, height=hgt, color=LGREY, edgecolor="white", label="at grant block" if i == 0 else None)
    ax.barh(i+hgt/2, vn, height=hgt, color=PURPLE if k == "EOA-CONTROLLED" else BLUE, edgecolor="white", hatch="xxx" if k == "EOA-CONTROLLED" else "",
            label="at snapshot" if i == 0 else None)
    ax.text(vg+0.6, i-hgt/2, f"{vg:.1f}%", va="center", fontsize=6.5, color=MUTED)
    ax.text(vn+0.6, i+hgt/2, f"{vn:.1f}%", va="center", fontsize=6.5, color=INK)
ax.set_yticks(range(len(order))); ax.set_yticklabels([l for _, l in order]); ax.invert_yaxis()
ax.set_xlabel(f"share of Mutated grants (%), n={len(mut):,}"); ax.set_xlim(0, 45)

from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=LGREY, label="at grant block"), Patch(color=BLUE, label="at snapshot")], loc="lower right", frameon=False)
fig.savefig("fig2_authority.pdf"); fig.savefig("fig2_authority.png"); plt.close(fig)
# Fig 3: unlimited share
U = O["unlimited"]; S = O["codeless_split"]
labs = ["Non-proxy", "Proxy-\nstable", "Mutated", "Code-less\n(all)", "high\nactivity", "low\nactivity", "dormant"]
vals = [U["NON_PROXY"], U["PROXY_STABLE"], U["MUTATED"], U["CODELESS"], S["operator(>=1000)"]["unl_pct"], S["low(10-999)"]["unl_pct"], S["dormant(<10)"]["unl_pct"]]
cols = [GREEN, BLUE, ORANGE, PURPLE, PURPLE, PURPLE, PURPLE]; alphas = [1, 1, 1, 1, .55, .55, .55]
fig, ax = plt.subplots(figsize=(W1, 1.85))
for i, (v, c, al) in enumerate(zip(vals, cols, alphas)):
    ax.bar(i, v, color=c, alpha=al, width=0.62, edgecolor="white", hatch="xxx" if i >= 3 else "")
    ax.text(i, v+2, f"{v:.0f}%", ha="center", fontsize=7, color=INK, fontweight="bold")
ax.axvline(3.5, color=MUTED, lw=0.6, ls=":")
ax.set_xticks(range(len(labs))); ax.set_xticklabels(labs, fontsize=6.3)
ax.set_ylabel("unlimited approvals (%)"); ax.set_ylim(0, 98)

fig.savefig("fig3_unlimited.pdf"); fig.savefig("fig3_unlimited.png"); plt.close(fig)
# Fig 4: TTL
A = json.load(open("ttl3_sample.json")); D = json.load(open("ttl3_danger.json"))
fig, ax = plt.subplots(figsize=(W1, 1.8))
xs = [r["ttl"] for r in A["ttl"]]
ax.plot(xs, [r["pct"] for r in A["ttl"]], "-o", color=BLUE, ms=3.5, lw=1.3, label=f"all drifted (sample, n={A['valid']})")
ax.plot(xs, [r["pct"] for r in D["ttl"]], "--s", color=PURPLE, ms=3.5, lw=1.3, label=f"single-key drifted (n={D['valid']})")
for r in A["ttl"]: ax.annotate(f"{r['pct']:.0f}", (r["ttl"], r["pct"]), textcoords="offset points", xytext=(-4, -3) if r["ttl"] == 7 else (4, -10), ha="right" if r["ttl"] == 7 else "left", fontsize=6, color=BLUE)
for r in D["ttl"]: ax.annotate(f"{r['pct']:.0f}", (r["ttl"], r["pct"]), textcoords="offset points", xytext=(3, 4), fontsize=6, color=PURPLE)
ax.set_xlabel("allowance TTL (days)"); ax.set_ylabel("lapsed before drift (%)")
ax.set_xticks([7, 30, 90, 180, 365]); ax.set_xticklabels(["7", "30", "90", "180", "365"]); ax.set_ylim(-8, 105); ax.set_xlim(-30, 390); ax.legend(frameon=False, loc="upper right")

fig.savefig("fig4_ttl.pdf"); fig.savefig("fig4_ttl.png"); plt.close(fig)
print("ok")
