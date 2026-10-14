import json, time
import rpccore
rpccore.ENDPOINTS[1] = ["https://eth.drpc.org", "https://rpc.mevblocker.io"]
from rpccore import batch, a, IMPL_SLOT
SNAP = json.load(open("snapshot.json"))["block"]
P = json.load(open("probes.json"))
sp = sorted(P); out = {}
for i in range(0, len(sp), 80):
    part = sp[i:i+80]
    for _ in range(6):
        try: r = batch([("eth_getStorageAt", [s, IMPL_SLOT, hex(SNAP)]) for s in part]); break
        except Exception as e: time.sleep(5)
    for j, s in enumerate(part):
        v = r.get(j)
        out[s] = (a(v) if v != "0x" and int(v, 16) else None) if v is not None else "ERR"
    time.sleep(0.2)
json.dump(out, open("impl_now.json", "w")); print("done", sum(v == "ERR" for v in out.values()))
