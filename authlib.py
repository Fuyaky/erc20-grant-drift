"""MW3/MW4: upgrade authority of every MUTATED proxy resolved AT THE GRANT BLOCK
(archival) and at the snapshot block, with an extended resolver for proxies whose
admin is not in the EIP-1967 slot; plus Safe thresholds and timelock delays."""
import json, os, sys, time
from collections import Counter, defaultdict
import rpccore
rpccore.ENDPOINTS[1] = ["https://rpc.mevblocker.io", "https://eth.drpc.org"]
from rpccore import batch, a

ADMIN = "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103"
BEACON = "0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50"
OWNER, PROVIDER, GETOWNER, DEFADMIN, ADMINF = "0x8da5cb5b", "0x0542975c", "0x893d20e8", "0x84ef8ffc", "0xf851a440"
THRESH, OWNERS, MINDELAY, DELAY, GETDELAY = "0xe75235b8", "0xa0e67e2b", "0xf27a0c92", "0x6a42b8f8", "0xcebc9a82"
SNAP = json.load(open("snapshot.json"))["block"]
grants = json.load(open("../data/grants_scaled_classified.json"))

def B(calls):
    out = {}
    for i in range(0, len(calls), 100):
        part = calls[i:i+100]
        for _ in range(6):
            try:
                r = batch(part); break
            except Exception as e:
                print("retry", str(e)[:80], flush=True); time.sleep(5)
        else:
            r = {}
        missing = [j for j in range(len(part)) if j not in r]
        if missing and len(missing) < len(part):   # retry stragglers once
            time.sleep(1)
            try:
                r2 = batch([part[j] for j in missing])
                for k, j in enumerate(missing):
                    if k in r2: r[j] = r2[k]
            except Exception: pass
        for j, v in r.items(): out[i+j] = v
        time.sleep(0.2)
    return out

def addr(v):
    return a(v) if v and v != "0x" and len(v) >= 66 and int(v[:66], 16) != 0 else None

def call(to, sel, blk): return ("eth_call", [{"to": to, "data": sel}, hex(blk)])

def resolve(pairs):
    p1 = []
    for s, b in pairs:
        p1 += [("eth_getStorageAt", [s, ADMIN, hex(b)]), ("eth_getStorageAt", [s, BEACON, hex(b)]),
               call(s, OWNER, b), call(s, PROVIDER, b), call(s, GETOWNER, b), call(s, DEFADMIN, b)]
    r1 = B(p1); K = 6
    st = {}
    for i, (s, b) in enumerate(pairs):
        o = i*K
        st[(s, b)] = dict(admin=addr(r1.get(o)), beacon=addr(r1.get(o+1)), own=addr(r1.get(o+2)),
                          prov=addr(r1.get(o+3)), gown=addr(r1.get(o+4)), dadm=addr(r1.get(o+5)))
    p2, idx = [], []
    for (s, b), d in st.items():
        for key in ("admin", "beacon", "prov"):
            if d[key]:
                idx.append(((s, b), key, "code")); p2.append(("eth_getCode", [d[key], hex(b)]))
                idx.append(((s, b), key, "owner")); p2.append(call(d[key], OWNER, b))
    r2 = B(p2)
    for i, (k, key, what) in enumerate(idx):
        st[k][f"{key}_{what}"] = r2.get(i)
    ctrl = {}
    for (s, b), d in st.items():
        c, path = None, None
        if d["admin"]:
            code = d.get("admin_code") or "0x"
            if code != "0x" and not code.startswith("0xef0100"):
                o = addr(d.get("admin_owner"))
                c, path = (o, "admin->owner") if o else (d["admin"], "admin(contract)")
            else:
                c, path = d["admin"], "admin(eoa)"
        elif d["beacon"]:
            c, path = (addr(d.get("beacon_owner")) or d["beacon"]), "beacon->owner"
        elif d["own"]:
            c, path = d["own"], "uups owner()"
        elif d["prov"] and addr(d.get("prov_owner")):
            c, path = addr(d.get("prov_owner")), "provider->owner"
        elif d["gown"]:
            c, path = d["gown"], "getOwner()"
        elif d["dadm"]:
            c, path = d["dadm"], "defaultAdmin()"
        ctrl[(s, b)] = (c, path)
    # classify controllers at the same block
    p3, idx = [], []
    for k, (c, path) in ctrl.items():
        if c:
            b = k[1]
            for sel in ("code", THRESH, MINDELAY, DELAY, GETDELAY):
                idx.append((k, sel))
                p3.append(("eth_getCode", [c, hex(b)]) if sel == "code" else call(c, sel, b))
    r3 = B(p3)
    det = defaultdict(dict)
    for i, (k, sel) in enumerate(idx):
        det[k][sel] = r3.get(i)
    out = {}
    for k, (c, path) in ctrl.items():
        if not c:
            out[k] = dict(controller=None, path="no-owner", label="UNKNOWN"); continue
        d = det[k]; code = d.get("code")
        if code is None:
            lab = "ERROR"
        elif code == "0x" or code.startswith("0xef0100"):
            lab = "EOA-CONTROLLED"
        elif d.get(THRESH) not in (None, "0x"):
            lab = "MULTISIG"
        elif any(d.get(x) not in (None, "0x") for x in (MINDELAY, DELAY, GETDELAY)):
            lab = "TIMELOCK"
        else:
            lab = "CONTRACT-OTHER"
        out[k] = dict(controller=c, path=path, label=lab, delegated7702=bool(code and code.startswith("0xef0100")))
    return out

