"""Run once after cloning: moves files into data/ and revision/ and decompresses the .gz files."""
import gzip, os, shutil
DATA = "authority.json grants_scaled_classified.json.gz impl_at_grant.json.gz realized_verified.json spender_info.json stats_meta.json ttl.json ttl_dangerous.json".split()
REV = "auth_missing.json authlib.py authority2.json.gz authority2.py authority3.json.gz authority3.py authority4.json authority4.py fig1_classes.pdf fig2_authority.pdf fig3_unlimited.pdf fig4_ttl.pdf figs_rev.py final_stats.json final_stats.py gov.json gov.py grants_revised.json.gz impl_now.json impl_now.py nonstd.json nonstd.py prices.json prices.py probes.json.gz probes.py snapshot.json.gz snapshot.py table_by_epoch.csv table_by_token.csv ttl3.py ttl3_danger.json ttl3_sample.json".split()
moves = [(f, "data") for f in DATA] + [(f, "revision") for f in REV]
_ = [os.makedirs(d, exist_ok=True) for d in ("data", "revision")]
_ = [shutil.move(f, os.path.join(d, f)) for f, d in moves if os.path.exists(f)]
gz = [os.path.join(d, f) for f, d in moves if f.endswith(".gz") and os.path.exists(os.path.join(d, f))]
_ = [open(p[:-3], "wb").write(gzip.open(p).read()) for p in gz]
_ = [os.remove(p) for p in gz]
print("layout ready: data/ and revision/ created, .gz files decompressed")
