"""Etap 1: scaled, multi-window sampling to defeat burst bias.

For each age epoch we sample FOUR dispersed windows (spread across ~30 days at
that age) instead of one contiguous block, over 12 tokens. This gives temporal
replication within each epoch so confidence intervals can be bootstrapped over
distinct spenders rather than assuming i.i.d. grants.
"""
import json
import os
import time

from rpccore import SIG_APPROVAL, TOKENS, a, get_logs, rpc

OUT = "data"
BLOCKS_PER_DAY = 7150
HEAD = int(rpc("eth_blockNumber", []), 16)
EPOCHS = {"0.25y": 0.25, "0.5y": 0.5, "1.0y": 1.0, "1.5y": 1.5, "2.0y": 2.0}
WINDOWS_PER_EPOCH = 4
WIN_BLOCKS = 300            # keep each window small; 4 windows × 12 tokens
SPREAD_DAYS = 30           # windows dispersed across 30 days at that age


def log(*x):
    print(f"[{time.strftime('%H:%M:%S')}]", *x, flush=True)


def collect():
    path = f"{OUT}/grants_scaled_raw.json"
    done = json.load(open(path)) if os.path.exists(path) else {}
    for label, years in EPOCHS.items():
        base_ago = int(years * 365 * BLOCKS_PER_DAY)
        for w in range(WINDOWS_PER_EPOCH):
            # disperse windows across SPREAD_DAYS
            offset = int((w / max(1, WINDOWS_PER_EPOCH - 1)) * SPREAD_DAYS
                         * BLOCKS_PER_DAY)
            start = HEAD - base_ago + offset
            for tok, (sym, dec) in TOKENS.items():
                key = f"{label}|{w}|{tok}"
                if key in done:
                    continue
                try:
                    logs = get_logs(tok, [SIG_APPROVAL], start,
                                    start + WIN_BLOCKS, chunk=WIN_BLOCKS)
                except Exception as exc:
                    log(f"  {key}: fail {str(exc)[:40]}")
                    continue
                rows = []
                for l in logs:
                    if len(l["topics"]) < 3:
                        continue
                    rows.append({"token": tok, "sym": sym, "window": w,
                                 "owner": a(l["topics"][1]),
                                 "spender": a(l["topics"][2]),
                                 "value": int(l["data"], 16),
                                 "block": int(l["blockNumber"], 16),
                                 "age": label})
                done[key] = rows
            json.dump(done, open(path, "w"))
            log(f"  {label} window {w}: "
                f"{sum(len(v) for k,v in done.items() if k.startswith(label))} "
                f"grants so far")
    return done


if __name__ == "__main__":
    done = collect()
    allrows = [r for rows in done.values() for r in rows]
    json.dump(allrows, open(f"{OUT}/grants_scaled.json", "w"))
    log(f"TOTAL scaled grants: {len(allrows)}")
    from collections import Counter
    print("by epoch:", dict(Counter(r["age"] for r in allrows)))
    print("distinct spenders:", len({r["spender"] for r in allrows}))
    print("distinct owners:", len({r["owner"] for r in allrows}))
