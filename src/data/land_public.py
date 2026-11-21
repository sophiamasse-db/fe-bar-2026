"""Land PUBLIC source files, exactly as published, into the UC landing volume.

Sources (all public):
  * Exchange symbol directory (pipe-delimited)          -> public/security_master/
  * SEC ticker / CIK / exchange map (JSON)              -> public/sec_companies/
  * SEC XBRL frames: shares outstanding, public float   -> public/sec_facts/<concept>/<frame>.json
  * SEC submissions extract (SIC sector code) per CIK   -> public/sec_sic/sec_submissions_extract.jsonl

Idempotent: a file that already exists is skipped unless --overwrite.
SEC asks automated clients to identify themselves; we send a generic demo User-Agent and stay < 10 req/s.
"""
import argparse
import hashlib
import json
import os
import time

import requests

UA = {"User-Agent": "NextDAQ-FE-Bar-Demo admin@example.com", "Accept-Encoding": "gzip, deflate"}
SYMDIR_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
FRAME_URL = "https://data.sec.gov/api/xbrl/frames/{taxonomy}/{concept}/{unit}/{frame}.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"

SHARE_FRAMES = [f"CY{y}Q{q}I" for y in range(2021, 2027) for q in (1, 2, 3, 4)
                if (y, q) >= (2021, 2) and (y, q) <= (2026, 3)]
# fallback for dual-class filers, whose cover-page share counts are per class and absent from frames
WAVG_FRAMES = [f"CY{y}Q{q}" for y in range(2021, 2027) for q in (1, 2, 3, 4)
               if (y, q) >= (2021, 2) and (y, q) <= (2026, 2)]
FLOAT_FRAMES = [f"CY{y}Q{q}I" for y in range(2021, 2027) for q in (1, 2, 3, 4)
                if (y, q) >= (2021, 1) and (y, q) <= (2026, 2)]
MIN_FLOAT_USD = 300e6          # universe for the SIC lookup: public float >= $300M
EXCLUDED_CIKS = {1120193}      # the exchange operator itself is excluded from the demo universe
MISSING_SIC_PLANT = 10         # planted finding: SIC blanked for N filers (hash-selected, stable)

calls = 0


def get(url, session):
    global calls
    for attempt in range(5):
        time.sleep(0.13)
        calls += 1
        r = session.get(url, headers=UA, timeout=60)
        if r.status_code == 200:
            return r
        if r.status_code == 404:
            return None
        time.sleep(2 ** attempt)
    r.raise_for_status()


def write(path, content: bytes, overwrite: bool) -> bool:
    if os.path.exists(path) and not overwrite:
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="landing root, e.g. /Volumes/<cat>/<schema>/landing")
    ap.add_argument("--overwrite", action="store_true")
    a = ap.parse_args()
    pub = os.path.join(a.root, "public")
    s = requests.Session()
    summary = {"written": [], "skipped": 0}

    # 1. Symbol directory (raw text, minus the excluded issuer's row)
    p = os.path.join(pub, "security_master", "exchange_listed.txt")
    if not os.path.exists(p) or a.overwrite:
        txt = get(SYMDIR_URL, s).text
        lines = [ln for ln in txt.splitlines() if not ln.startswith("NDAQ|")]
        write(p, ("\n".join(lines) + "\n").encode(), True)
        summary["written"].append(p)
    else:
        summary["skipped"] += 1
    symdir = open(p).read().splitlines()
    hdr = symdir[0].split("|")
    rows = [dict(zip(hdr, ln.split("|"))) for ln in symdir[1:] if "|" in ln and not ln.startswith("File Creation")]
    listed = {r["Symbol"].strip() for r in rows if r.get("Test Issue") == "N" and r.get("ETF") == "N"}

    # 2. SEC ticker map
    p = os.path.join(pub, "sec_companies", "company_tickers_exchange.json")
    if a.overwrite or not os.path.exists(p):
        write(p, get(SEC_TICKERS_URL, s).content, True)
        summary["written"].append(p)
    tmap = json.load(open(p))
    fields = tmap["fields"]
    sec = [dict(zip(fields, r)) for r in tmap["data"]]
    cik_by_ticker = {r["ticker"]: int(r["cik"]) for r in sec if r["exchange"] == "Nasdaq" and r["ticker"] in listed}

    # 3. Frames
    latest_float = {}
    for taxonomy, concept, unit, frames in (("dei", "EntityCommonStockSharesOutstanding", "shares", SHARE_FRAMES),
                                            ("dei", "EntityPublicFloat", "USD", FLOAT_FRAMES),
                                            ("us-gaap", "WeightedAverageNumberOfSharesOutstandingBasic", "shares", WAVG_FRAMES)):
        for fr in frames:
            p = os.path.join(pub, "sec_facts", concept, f"{fr}.json")
            if a.overwrite or not os.path.exists(p):
                r = get(FRAME_URL.format(taxonomy=taxonomy, concept=concept, unit=unit, frame=fr), s)
                if r is None:
                    continue
                write(p, r.content, True)
                summary["written"].append(p)
            if concept == "EntityPublicFloat":
                for d in json.load(open(p))["data"]:
                    latest_float[d["cik"]] = d["val"]

    # 4. SIC for the candidate universe
    p = os.path.join(pub, "sec_sic", "sec_submissions_extract.jsonl")
    if a.overwrite or not os.path.exists(p):
        ciks = sorted({c for c in cik_by_ticker.values()
                       if latest_float.get(c, 0) >= MIN_FLOAT_USD and c not in EXCLUDED_CIKS})
        plant = set(sorted(ciks, key=lambda c: hashlib.md5(f"sic{c}".encode()).hexdigest())[:MISSING_SIC_PLANT])
        out = []
        for c in ciks:
            r = get(SUBMISSIONS_URL.format(cik=c), s)
            if r is None:
                continue
            d = r.json()
            out.append({"cik": d.get("cik"), "name": d.get("name"), "tickers": d.get("tickers"),
                        "exchanges": d.get("exchanges"), "sic": "" if c in plant else d.get("sic"),
                        "sicDescription": "" if c in plant else d.get("sicDescription"),
                        "fiscalYearEnd": d.get("fiscalYearEnd"), "entityType": d.get("entityType")})
        write(p, "\n".join(json.dumps(o) for o in out).encode() + b"\n", True)
        summary["written"].append(p)
        summary["sic_records"] = len(out)
        summary["sic_blank_planted"] = len(plant)
    else:
        summary["skipped"] += 1

    summary.update({"listed_symbols": len(listed), "nasdaq_ciks": len(cik_by_ticker),
                    "http_calls": calls, "files_written": len(summary["written"])})
    summary["written"] = summary["written"][:5]
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
