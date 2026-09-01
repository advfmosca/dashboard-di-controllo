#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""apply_profile_visits.py — applica a un aghc_report.json già generato la sostituzione
dei click alla destinazione con le visite al profilo, sugli account TikTok i cui annunci
non hanno link di destinazione (click strutturalmente a zero).

build_report.py fa già questo dal prossimo run: questo script serve a riallineare un mese
già chiuso senza rifare il fetch dei dati Meta.

Uso: python3 apply_profile_visits.py --workspace .
"""
import argparse, json, os, sys

# advertiser_id TikTok per cliente (stesso mapping di build_demographics.TT_ACCT)
TT_ACCT = {
    "Hotel Della Piana": "7504967007843319824",
    "Hotel Lunetta": "7498330316248203280",
    "Marcella Royal Hotel": "7499093699838607377",
    "Mare Hotel": "7498679494010667009",
    "Villa Ermellina": "7612666695502118929",
    "Villa Giada": "7626418949391351815",
}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--workspace", default=".")
    a = ap.parse_args(); ws = a.workspace
    sys.path.insert(0, ws)
    from build_report import dpct

    pv = json.load(open(os.path.join(ws, "raw", "aghc_report_tt_profile_visits.json"), encoding="utf-8"))
    P = os.path.join(ws, "aghc_report.json")
    rep = json.load(open(P, encoding="utf-8"))

    n_sub = 0
    for c in rep["clients"]:
        tt = c.get("tiktok") or {}
        if not tt.get("available"): continue
        clk = tt.get("clicks") or {}
        if (clk.get("cur") or 0) or (clk.get("prev") or 0): continue   # ci sono click veri
        rec = pv.get(TT_ACCT.get(c["name"], ""), {})
        if rec.get("cur") is None: continue
        cur, prev = int(rec.get("cur") or 0), int(rec.get("prev") or 0)
        if not cur: continue
        tt["clicks"] = {"cur": cur, "prev": prev, "delta": dpct(cur, prev)}
        tt["clicks_source"] = "profile_visits"
        n_sub += 1
        print("%-24s click 0 -> visite al profilo: %s (prec. %s, %s)" % (
            c["name"], cur, prev, ("%+d%%" % dpct(cur, prev)) if dpct(cur, prev) is not None else "n/d"))

    json.dump(rep, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\nsostituzioni applicate: %d" % n_sub)

if __name__ == "__main__":
    main()
