"""Shared RPC + decoding helpers for the orphaned-approvals study."""
import json
import time
import urllib.request

from eth_utils import keccak, to_hex

UA = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 research"}

ENDPOINTS = {
    1: ["https://ethereum-rpc.publicnode.com", "https://eth.drpc.org",
        "https://rpc.mevblocker.io"],
}

SIG_APPROVAL = to_hex(keccak(text="Approval(address,address,uint256)"))
# EIP-1967 implementation slot
IMPL_SLOT = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
# EIP-1967 Upgraded(address) event
SIG_UPGRADED = to_hex(keccak(text="Upgraded(address)"))
UNLIMITED = 2 ** 255   # threshold: any value at/above this is "unlimited-like"


def a(topic):
    return "0x" + topic[-40:].lower()


def rpc(method, params, chain=1, timeout=60):
    last = None
    for url in ENDPOINTS[chain]:
        for _ in range(3):
            try:
                body = json.dumps({"jsonrpc": "2.0", "id": 1,
                                   "method": method, "params": params}).encode()
                req = urllib.request.Request(url, data=body, headers=UA)
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    j = json.loads(r.read())
                if "error" in j:
                    last = j["error"]
                    break
                return j["result"]
            except Exception as exc:
                last = exc
                time.sleep(1.0)
    raise RuntimeError(f"rpc {method} failed: {str(last)[:120]}")


def batch(calls, chain=1, timeout=90):
    """calls: list of (method, params). Returns dict id->result (missing on error)."""
    payload = [{"jsonrpc": "2.0", "id": i, "method": m, "params": p}
               for i, (m, p) in enumerate(calls)]
    last = None
    for url in ENDPOINTS[chain]:
        for _ in range(3):
            try:
                req = urllib.request.Request(
                    url, data=json.dumps(payload).encode(), headers=UA)
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    res = json.loads(r.read())
                if not isinstance(res, list):
                    last = res
                    break
                return {it["id"]: it["result"] for it in res if "result" in it}
            except Exception as exc:
                last = exc
                time.sleep(1.2)
    raise RuntimeError(f"batch failed: {str(last)[:120]}")


def get_logs(address, topics, frm, to, chunk, chain=1):
    out, lo = [], frm
    while lo <= to:
        hi = min(lo + chunk - 1, to)
        try:
            out.extend(rpc("eth_getLogs", [{
                "fromBlock": hex(lo), "toBlock": hex(hi),
                "address": address, "topics": topics}], chain))
            lo = hi + 1
        except Exception as exc:
            if chunk <= 32:
                print(f"    skip {lo}-{hi}: {str(exc)[:60]}")
                lo = hi + 1
                continue
            chunk //= 2
    return out


# Major ERC-20s by approval volume (address -> (symbol, decimals))
TOKENS = {
    "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": ("USDC", 6),
    "0xdac17f958d2ee523a2206206994597c13d831ec7": ("USDT", 6),
    "0x6b175474e89094c44da98b954eedeac495271d0f": ("DAI", 18),
    "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": ("WETH", 18),
    "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599": ("WBTC", 8),
    "0x514910771af9ca656af840dff83e8264ecf986ca": ("LINK", 18),
    "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984": ("UNI", 18),
    "0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9": ("AAVE", 18),
    "0x853d955acef822db058eb8505911ed77f175b99e": ("FRAX", 18),
    "0xae7ab96520de3a18e5e111b5eaab095312d7fe84": ("stETH", 18),
    "0x6982508145454ce325ddbe47a25d4ec3d2311933": ("PEPE", 18),
    "0x4d224452801aced8b2f0aebe155379bb5d594381": ("APE", 18),
}
