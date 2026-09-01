#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rebuild_rationals.py — ricalcola in place i rational di aghc_report.json usando le funzioni
di build_report.py, senza rifare il fetch dei dati.

Serve quando si cambia solo il testo dei rational (es. separazione Meta / TikTok) su un mese
già chiuso: i numeri restano quelli del report, cambia solo la narrazione.

Uso: python3 rebuild_rationals.py --workspace .
"""
import argparse, json, os, sys

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--workspace", default=".")
    a = ap.parse_args(); ws = a.workspace
    sys.path.insert(0, ws)
    from build_report import rational, rational_tt

    P = os.path.join(ws, "aghc_report.json")
    rep = json.load(open(P, encoding="utf-8"))

    def g(blk, ch, k):
        v = ((blk.get(k) or {}).get(ch) or {})
        return v.get("cur") or 0, v.get("prev") or 0

    changed = 0
    for c in rep["clients"]:
        M = c.get("meta") or {}
        if M.get("available"):
            # rational() somma ig+fb: si ricostruiscono i due lati dai blocchi del report.
            # La spesa è disponibile solo aggregata: la si mette tutta su "ig" (la somma è identica).
            cur = {}; prev = {}
            for side in ("ig", "fb"):
                rc, rp = g(M, side, "reach"); ec, ep = g(M, side, "engagement"); kc, kp = g(M, side, "clicks")
                ic, ip = g(M, side, "impressions")
                cur[side] = {"reach": rc, "impr": ic, "eng": ec, "clk": kc, "spend": 0.0}
                prev[side] = {"reach": rp, "impr": ip, "eng": ep, "clk": kp, "spend": 0.0}
            b = M.get("budget") or {}
            cur["ig"]["spend"] = b.get("cur") or 0.0
            prev["ig"]["spend"] = b.get("prev") or 0.0
            new_m = rational(cur, prev)
        else:
            new_m = ""
        new_t = rational_tt(c.get("tiktok"))
        if c.get("rational") != new_m or c.get("rational_tiktok") != new_t: changed += 1
        c["rational"] = new_m
        c["rational_tiktok"] = new_t

    json.dump(rep, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("rational aggiornati: %d/%d clienti" % (changed, len(rep["clients"])))

if __name__ == "__main__":
    main()
