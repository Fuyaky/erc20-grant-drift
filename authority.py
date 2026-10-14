"""Fix (both auditor and reviewer #1 ask): resolve the REAL upgrade authority of
every MUTATED proxy, not just the EIP-1967 admin slot.

Upgrade authority can live in several places:
  - EIP-1967 admin slot  -> often an OZ ProxyAdmin (itself Ownable) or an address
  - UUPS (EIP-1822)       -> authority is owner()/access-control in the IMPL
  - beacon proxy          -> authority is the beacon's owner()

We resolve each to a final controller and label it:
  EOA-CONTROLLED : final controller is a code-less EOA (single key can upgrade)
  MULTISIG/TIMELOCK: controller is a Safe / timelock / governance contract
  CONTRACT-OTHER : controller is some other contract (unresolved governance)
  UNKNOWN        : could not resolve (no owner()/admin found)
"""
import json
import time

from eth_utils import keccak, to_hex

from rpccore import a, batch, rpc

ADMIN_SLOT = "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103"
BEACON_SLOT = "0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50"
SEL_OWNER = "0x8da5cb5b"       # owner()
SEL_ADMIN = "0xf851a440"       # admin()  (some ProxyAdmin)
grants = json.load(open("data/grants_scaled_classified.json"))
info = json.load(open("data/spender_info.json"))
code_cache = {}


def log(*x):
    print(f"[{time.strftime('%H:%M:%S')}]", *x, flush=True)


def get_code_kind(addrs):
    """address -> 'eoa' | 'contract', cached."""
    todo = [x for x in addrs if x and x not in code_cache]
    for i in range(0, len(todo), 100):
        part = todo[i:i + 100]
        codes = batch([("eth_getCode", [x, "latest"]) for x in part])
        for j, x in enumerate(part):
            c = codes.get(j, "0x")
            code_cache[x] = "contract" if (c and c != "0x") else "eoa"
    return {x: code_cache.get(x) for x in addrs}


def call_addr(target, selector):
    try:
        r = rpc("eth_call", [{"to": target, "data": selector}, "latest"])
        if r and len(r) >= 66 and int(r, 16) != 0:
            return a(r)
    except Exception:
        pass
    return None


def read_slot_addr(target, slot):
    try:
        r = rpc("eth_getStorageAt", [target, slot, "latest"])
        if r and int(r, 16) != 0:
            return a(r)
    except Exception:
        pass
    return None


# heuristic: is a contract a Safe/timelock/governance?
def gov_kind(addr):
    # Gnosis Safe: getThreshold() 0xe75235b8 ; Timelock: getMinDelay() 0xf27a0c92
    for sel, label in [("0xe75235b8", "multisig"), ("0xf27a0c92", "timelock"),
                       ("0x6a42b8f8", "timelock")]:
        try:
            r = rpc("eth_call", [{"to": addr, "data": sel}, "latest"])
            if r and r != "0x":
                return label
        except Exception:
            pass
    return "contract-other"


mut_spenders = sorted({r["spender"] for r in grants if r["cls"] == "MUTATED"})
log(f"MUTATED spenders: {len(mut_spenders)}")

authority = {}
for i, s in enumerate(mut_spenders):
    admin = read_slot_addr(s, ADMIN_SLOT)
    beacon = read_slot_addr(s, BEACON_SLOT)
    controller = None
    path = None
    if admin:
        # admin may be a ProxyAdmin contract (Ownable) or a direct address
        kinds = get_code_kind([admin])
        if kinds[admin] == "contract":
            owner = call_addr(admin, SEL_OWNER)
            if owner:
                controller, path = owner, "admin->owner"
            else:
                controller, path = admin, "admin(contract)"
        else:
            controller, path = admin, "admin(eoa)"
    elif beacon:
        owner = call_addr(beacon, SEL_OWNER)
        controller, path = (owner or beacon), "beacon->owner"
    else:
        # UUPS: authority in implementation -> owner() on the proxy itself
        owner = call_addr(s, SEL_OWNER)
        if owner:
            controller, path = owner, "uups owner()"
        else:
            controller, path = None, "no-owner"
    authority[s] = {"controller": controller, "path": path}
    if i % 25 == 0:
        log(f"  {i+1}/{len(mut_spenders)}")

# classify controllers
controllers = [v["controller"] for v in authority.values() if v["controller"]]
kinds = get_code_kind(controllers)
label = {}
for s, v in authority.items():
    c = v["controller"]
    if not c:
        label[s] = "UNKNOWN"
    elif kinds.get(c) == "eoa":
        label[s] = "EOA-CONTROLLED"
    else:
        label[s] = gov_kind(c).upper()

for r in grants:
    if r["cls"] == "MUTATED":
        r["upgrade_authority"] = label.get(r["spender"])
json.dump(grants, open("data/grants_scaled_classified.json", "w"))
json.dump({s: {**authority[s], "label": label[s]} for s in mut_spenders},
          open("data/authority.json", "w"))

from collections import Counter
mut = [r for r in grants if r["cls"] == "MUTATED"]
N = len(grants)
print("\n=== REAL upgrade authority of MUTATED proxies (by grant) ===")
for k, n in Counter(r["upgrade_authority"] for r in mut).most_common():
    print(f"  {k:16s} {n:5d} grants ({100*n/len(mut):.1f}% of MUTATED, "
          f"{100*n/N:.2f}% of all)")
print("\n=== by distinct spender ===")
for k, n in Counter(label.values()).most_common():
    print(f"  {k:16s} {n:4d} spenders")

danger = [r for r in mut if r["upgrade_authority"] == "EOA-CONTROLLED"]
print(f"\nDANGEROUS (single-EOA-key upgradeable, live allowance): "
      f"{len(danger)} grants = {100*len(danger)/N:.2f}% of all grants, "
      f"{100*len(danger)/len(mut):.1f}% of MUTATED")
