#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""backfill_client.py — aggiunge a un aghc_report.json già generato l'entry di un cliente
che non era ancora in aghc_report_lib.CLIENTS quando il report è stato prodotto.

Serve quando una struttura entra in gestione a mese iniziato: la si aggiunge a CLIENTS
(così i mesi successivi la includono da sole) e con questo script la si recupera nel mese
corrente senza rigenerare gli altri clienti, che sono già stati pubblicati.

Replica esattamente la logica di build_report.py per il blocco Meta, confronto MoM.
Nessun TikTok: se la struttura ne ha uno, va generata con build_report.py.

Uso: python3 backfill_client.py --workspace . --client "Livata" \
        --month-label "Agosto 2026" --prev-label "Luglio 2026"
"""
import argparse, json, os, sys

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--client", required=True)
    ap.add_argument("--month-label", required=True)
    ap.add_argument("--prev-label", required=True)
    a = ap.parse_args(); ws = a.workspace
    sys.path.insert(0, ws)
    from aghc_report_lib import CLIENTS, load_raw, bucket, dpct, cell
    from build_report import rational

    row = [c for c in CLIENTS if c[0] == a.client]
    if not row: sys.exit("cliente '%s' non presente in aghc_report_lib.CLIENTS" % a.client)
    name, acct, camp, ttid = row[0]

    ma = load_raw(ws, "rep_meta_acct_cur.json"); ca = load_raw(ws, "rep_meta_camp_cur.json")
    mp = load_raw(ws, "rep_meta_acct_prev.json"); cp = load_raw(ws, "rep_meta_camp_prev.json")
    cur = bucket(ca if camp else ma, acct, camp)
    prev = bucket(cp if camp else mp, acct, camp)

    active = (cur["ig"]["spend"] + cur["fb"]["spend"] + cur["ig"]["impr"] + cur["fb"]["impr"]) > 0
    if not active: sys.exit("nessun dato di erogazione per %s nel mese corrente" % name)

    def tbl(k): return {"ig": cell(cur["ig"][k], prev["ig"][k]), "fb": cell(cur["fb"][k], prev["fb"][k])}
    tsc = cur["ig"]["spend"] + cur["fb"]["spend"]; tsp = prev["ig"]["spend"] + prev["fb"]["spend"]
    e = {
        "name": name, "comparison_used": "mom",
        "meta_period_label": "%s vs %s" % (a.month_label, a.prev_label),
        "tt_period_label": "%s vs %s" % (a.month_label, a.prev_label),
        "meta": {"available": True, "reach": tbl("reach"), "impressions": tbl("impr"),
                 "engagement": tbl("eng"), "clicks": tbl("clk"),
                 "budget": {"cur": round(tsc, 2), "prev": round(tsp, 2), "delta": dpct(tsc, tsp)}},
    }
    e["rational"] = rational(cur, prev)
    e["rational_tiktok"] = ""

    P = os.path.join(ws, "aghc_report.json")
    rep = json.load(open(P, encoding="utf-8"))
    rep["clients"] = [c for c in rep["clients"] if c["name"] != name] + [e]
    json.dump(rep, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print("%s aggiunto: spesa %.2f € (prec. %.2f €), reach IG %s / FB %s" % (
        name, tsc, tsp, e["meta"]["reach"]["ig"]["cur"], e["meta"]["reach"]["fb"]["cur"]))
    print("clienti ora in aghc_report.json: %d" % len(rep["clients"]))

if __name__ == "__main__":
    main()
