#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rebuild_demo_shared.py — ricalcola il blocco demografico Meta dei soli clienti che
condividono un ad account, separandoli per keyword di campagna.

Serve per rigenerare un mese già chiuso senza rifare l'intero pull: legge un dump
`[{account_id, campaign, dim, label, reach}]` e riscrive `meta` dei clienti interessati
dentro aghc_demographics_monthly.json (il blocco `tiktok` resta intatto).

Uso: python3 rebuild_demo_shared.py --workspace . --month 2026-08 --dump demo_campaign_2026-08.json
"""
import argparse, json, os, sys

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--month", required=True)
    ap.add_argument("--dump", required=True)
    a = ap.parse_args()
    ws = a.workspace
    sys.path.insert(0, ws)
    from build_demographics import META_ACCT, sel, age_sorted, gender_norm, region_it

    rows = json.load(open(a.dump, encoding="utf-8"))
    # store[dim][account] = [(label, valore, campagna)] — stessa forma di by_acct()
    store = {"age": {}, "gender": {}, "region": {}}
    for r in rows:
        d = r.get("dim")
        if d not in store: continue
        store[d].setdefault(str(r["account_id"]), []).append(
            (r.get("label"), float(r.get("reach") or 0), str(r.get("campaign") or "")))

    # solo gli account presenti nel dump, e solo se davvero condivisi
    targets = []
    for acct, entries in META_ACCT.items():
        if acct not in store["age"] and acct not in store["region"]: continue
        if len(entries) < 2: continue
        for name, kw in entries: targets.append((name, acct, kw))

    P = os.path.join(ws, "aghc_demographics_monthly.json")
    doc = json.load(open(P, encoding="utf-8"))
    month = doc["by_month"].setdefault(a.month, {})

    for name, acct, kw in targets:
        blk = month.setdefault(name, {"meta": None, "tiktok": None})
        blk["meta"] = {
            "age": age_sorted(sel(store["age"], acct, kw)),
            "gender": gender_norm(sel(store["gender"], acct, kw)),
            "geo": region_it(sel(store["region"], acct, kw)),
        }
        geo = ", ".join("%s %.1f%%" % (x["label"], x["pct"]) for x in blk["meta"]["geo"])
        print("%-24s kw=%-14s geo: %s" % (name, kw, geo))

    json.dump(doc, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print("\naggiornati %d clienti in %s (%s)" % (len(targets), os.path.basename(P), a.month))

if __name__ == "__main__":
    main()
