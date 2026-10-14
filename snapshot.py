"""MW1: current allowance(owner,spender) and balanceOf(owner) for every sampled
grant relation, at one fixed snapshot block. Passive eth_call only. Resumable."""
import json, os, sys, time
from rpccore import batch, rpc

OUT = "snapshot.json"
grants = json.load(open("../data/grants_scaled_classified.json"))
pairs = sorted({(r["token"], r["owner"], r["spender"]) for r in grants})
tos = sorted({(r["token"], r["owner"]) for r in grants})
st = json.load(open(OUT)) if os.path.exists(OUT) else {}
if "block" not in st:
    st = {"block": int(rpc("eth_blockNumber", []), 16) - 12, "allow": {}, "bal": {}}
B = hex(st["block"])
pad = lambda x: x[2:].rjust(64, "0")

def run(items, key, mk, store):
    todo = [x for x in items if "|".join(x) not in store]
    print(key, "todo", len(todo), flush=True)
    for i in range(0, len(todo), 100):
        part = todo[i:i+100]
        for attempt in range(4):
            try:
                res = batch([("eth_call", [mk(x), B]) for x in part])
                break
            except Exception as e:
                print("retry", e, flush=True); time.sleep(5)
        else:
            continue
        for j, x in enumerate(part):
            v = res.get(j)
            if v is not None:
                store["|".join(x)] = str(int(v, 16)) if v not in ("0x", "") else "0"
        if (i // 100) % 20 == 0:
            json.dump(st, open(OUT, "w")); print(key, i+len(part), flush=True)
        time.sleep(0.15)
    json.dump(st, open(OUT, "w"))

run(pairs, "allow", lambda x: {"to": x[0], "data": "0xdd62ed3e" + pad(x[1]) + pad(x[2])}, st["allow"])
run(tos, "bal", lambda x: {"to": x[0], "data": "0x70a08231" + pad(x[1])}, st["bal"])
print("done", st["block"], len(st["allow"]), len(st["bal"]))
