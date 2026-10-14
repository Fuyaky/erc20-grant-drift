"""Figure 4: TTL counterfactual curve. IEEE single-column, print-safe.
Same style as figures.py; embeds TrueType (pdf.fonttype 42) for IEEE PDF eXpress.
Plots the fraction of drifted-trust (mutated) grants a T-day allowance expiry
would have retired before the implementation changed (data/ttl.json).
"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BLUE, INK, MUTED = "#2b5fa8", "#1a1a1a", "#5c5c5c"
plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Nimbus Roman", "DejaVu Serif"],
    "font.size": 8, "axes.labelsize": 8, "axes.titlesize": 8.5,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7,
    "axes.edgecolor": MUTED, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#dddddd", "grid.linewidth": 0.5,
    "figure.dpi": 300, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
    "pdf.fonttype": 42, "ps.fonttype": 42})
W1 = 3.4

d = json.load(open("data/ttl.json"))
xs = [r["ttl"] for r in d["ttl"]]
ys = [r["neutralized_pct"] for r in d["ttl"]]

fig, ax = plt.subplots(figsize=(W1, 1.8))
ax.plot(xs, ys, "-o", color=BLUE, markersize=4, linewidth=1.4)
for x, y in zip(xs, ys):
    ax.annotate(f"{y:.0f}%", (x, y), textcoords="offset points",
                xytext=(4, 5), fontsize=6.5, color=INK)
ax.set_xlabel("allowance TTL (days)")
ax.set_ylabel("drifted grants neutralized (%)")
ax.set_title("An allowance TTL retires drift before it happens")
ax.set_xticks(xs)
ax.set_ylim(-4, 105)
fig.savefig("fig4_ttl.png")
fig.savefig("fig4_ttl.pdf")
print("wrote fig4_ttl.pdf / .png")
