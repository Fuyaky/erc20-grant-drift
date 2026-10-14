import json
import rpccore
rpccore.ENDPOINTS[1] = ["https://eth.drpc.org", "https://rpc.mevblocker.io"]
from rpccore import batch
SNAP = json.load(open("snapshot.json"))["block"]
F = {"ETH": "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419", "BTC": "0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c",
     "LINK": "0x2c1d072e956AFFC0D435Cb7AC38EF18d24d9127c", "UNI": "0x553303d460EE0afB37EdFf9bE42922D8FF63220e",
     "AAVE": "0x547a514d5e3769680Ce22B2361c10Ea13619e8a9", "APE": "0xD10aBbC76679a20055E167BB80A24ac851b37056",
     "STETH": "0xCfE54B5cD566aB89272946F602D76Ea879CAb4a8", "FRAX": "0xB9E1E3A9feFf48998E45Fa90847ed4D467E8BcfD"}
calls = []
for k, f in F.items():
    calls += [("eth_call", [{"to": f, "data": "0x7284e416"}, hex(SNAP)]), ("eth_call", [{"to": f, "data": "0xfeaf968c"}, hex(SNAP)]), ("eth_call", [{"to": f, "data": "0x313ce567"}, hex(SNAP)])]
r = batch(calls)
out = {}
for i, k in enumerate(F):
    d = r.get(3*i); ans = r.get(3*i+1); dec = r.get(3*i+2)
    desc = bytes.fromhex(d[2:])[64:].rstrip(b"\0").decode(errors="ignore") if d and len(d) > 2 else None
    price = int(ans[66:130], 16) / 10**int(dec, 16) if ans and len(ans) > 130 else None
    print(k, desc, price)
    out[k] = price
json.dump(out, open("prices.json", "w"))
