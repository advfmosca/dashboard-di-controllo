#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_budget.py - Modulo budget AGHC (anchor = BUDGET OPERATIVO MENSILE / run-rate).

Mandato Francesco 2026-08-08: il "programmato" si ancora al budget operativo mensile
reale (stile PED), non al tetto annuale delle strategie. La ricalibrazione riporta i
mesi successivi sull'annuale OPERATIVO tenendo conto dello speso ad oggi.

Modello per struttura:
- annual_strategy   = tetto approvato in strategy (aghc_roster.json) — solo riferimento.
- operating_monthly = stima del budget mensile operativo = media degli ultimi <=3 mesi
                      CHIUSI con spesa (fallback: media mesi attivi; poi 0). Override
                      possibile in aghc_budget_ops.json {"operating_monthly": {name: val}}.
- operating_annual  = operating_monthly * 12  (target realistico dell'anno).
- monthly_real[12]  = speso reale (mesi chiusi bloccati).
- monthly_plan[12]  = reale nei mesi chiusi + operating_monthly nei mesi rimanenti (baseline).
- monthly_recal[12] = reale nei mesi chiusi + forward ricalibrato nei mesi rimanenti, dove
                      forward = (operating_annual - ytd_real) / mesi_rimanenti  (>=0),
                      così l'anno chiude sull'operating_annual recuperando over/under.
- pace vs pro-rata operativo (operating_monthly * mesi_chiusi), proiezione a fine anno.

Input:  aghc_roster.json, aghc_actuals_monthly.json, [aghc_budget_ops.json]
Output: aghc_budget.json
Uso:    python3 build_budget.py --as-of-month 2026-07 --workspace .
"""
import argparse, json, os
from datetime import datetime

MESI = ["Gen","Feb","Mar","Apr","Mag","Giu","Lug","Ago","Set","Ott","Nov","Dic"]

def load(ws, p, req=True):
    fp = os.path.join(ws, p)
    if not os.path.exists(fp):
        if req: raise SystemExit(p + " mancante")
        return None
    return json.load(open(fp, encoding="utf-8"))

def r2(x): return round(float(x) + 0.0, 2)

def est_operating_monthly(real, as_of):
    """Media ultimi <=3 mesi CHIUSI con spesa > 0."""
    closed = real[:as_of]
    tail = closed[-3:] if len(closed) >= 3 else closed
    nz = [v for v in tail if v and v > 0]
    if nz:
        return sum(nz) / len(nz)
    nz_all = [v for v in closed if v and v > 0]
    return (sum(nz_all) / len(nz_all)) if nz_all else 0.0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--as-of-month", required=True, help="YYYY-MM ultimo mese CHIUSO")
    ap.add_argument("--pace-tol", type=float, default=10.0)
    args = ap.parse_args()
    ws = args.workspace

    roster = {s["name"]: s for s in load(ws, "aghc_roster.json")["structures"]}
    actuals = {s["name"]: s for s in load(ws, "aghc_actuals_monthly.json")["structures"]}
    ops_cfg = (load(ws, "aghc_budget_ops.json", req=False) or {}).get("operating_monthly", {})

    ay, am = map(int, args.as_of_month.split("-"))
    as_of = am
    rem = list(range(as_of, 12))  # mesi da pianificare (0-based)

    out = {"schema_version": 2, "year": ay, "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
           "anchor": "operating_monthly",
           "as_of_month": args.as_of_month, "as_of_label": MESI[as_of-1] + " " + str(ay),
           "method": ("Programmato ancorato al budget operativo mensile (run-rate, media ultimi 3 mesi chiusi o override). "
                      "Annuale strategia = solo tetto di riferimento. Ricalibrazione: i mesi rimanenti chiudono sull'annuale operativo recuperando over/under."),
           "structures": [], "totals": {}}

    T = {"strategy":0.0,"op_annual":0.0,"ytd":0.0,"proj":0.0,
         "m_real":[0.0]*12,"m_plan":[0.0]*12,"m_recal":[0.0]*12,"q_plan":[0,0,0,0],"q_real":[0,0,0,0]}

    for name, s in roster.items():
        strat = float(s["budget_annuale"])
        a = actuals.get(name, {})
        real = [float(x or 0) for x in (list(a.get("monthly", {}).get("total", [])) + [0.0]*12)[:12]]
        ytd = sum(real[:as_of])

        op_m = float(ops_cfg[name]) if name in ops_cfg else est_operating_monthly(real, as_of)
        op_annual = op_m * 12.0

        # baseline plan: reale nei chiusi + operating nei rimanenti
        plan = list(real)
        for i in rem: plan[i] = r2(op_m)
        # recal: reale nei chiusi + forward per chiudere su op_annual
        residual = op_annual - ytd
        fwd = max(residual / len(rem), 0.0) if rem else 0.0
        recal = list(real)
        for i in rem: recal[i] = r2(fwd)
        if rem:
            drift = r2(op_annual - (ytd + sum(recal[i] for i in rem)))
            recal[rem[-1]] = r2(max(recal[rem[-1]] + drift, 0.0))

        prorata_op = op_m * as_of
        pace_delta = ytd - prorata_op
        pace_pct = (pace_delta / prorata_op * 100.0) if prorata_op else None
        proj = ytd / as_of * 12.0 if as_of else 0.0

        if op_m == 0:
            status = "inactive"
        elif pace_pct is None:
            status = "na"
        elif pace_pct > args.pace_tol:
            status = "over"
        elif pace_pct < -args.pace_tol:
            status = "under"
        else:
            status = "on_track"

        def q(v, i): return r2(sum(v[i*3:i*3+3]))
        out["structures"].append({
            "name": name, "has_tiktok": a.get("has_tiktok", False),
            "annual_strategy": r2(strat),
            "operating_monthly": r2(op_m), "operating_annual": r2(op_annual),
            "operating_source": ("override" if name in ops_cfg else "run-rate"),
            "ytd_real": r2(ytd), "ytd_meta": r2(a.get("ytd_meta", 0)), "ytd_tiktok": r2(a.get("ytd_tiktok", 0)),
            "prorata_operating": r2(prorata_op), "pace_delta": r2(pace_delta),
            "pace_pct": (r2(pace_pct) if pace_pct is not None else None),
            "projection_year_end": r2(proj),
            "fwd_recal_monthly": r2(fwd), "remaining_months": len(rem),
            "utilizzo_tetto_pct": (r2(op_annual / strat * 100.0) if strat else None),
            "status": status,
            "monthly_real": [r2(x) for x in real],
            "monthly_plan": [r2(x) for x in plan],
            "monthly_recal": [r2(x) for x in recal],
            "quarter_plan": [q(plan, i) for i in range(4)],
            "quarter_real": [q(real, i) for i in range(4)],
        })
        T["strategy"]+=strat; T["op_annual"]+=op_annual; T["ytd"]+=ytd; T["proj"]+=proj
        for i in range(12): T["m_real"][i]+=real[i]; T["m_plan"][i]+=plan[i]; T["m_recal"][i]+=recal[i]
        for i in range(4): T["q_plan"][i]+=q(plan,i); T["q_real"][i]+=q(real,i)

    out["totals"] = {
        "annual_strategy": r2(T["strategy"]), "operating_annual": r2(T["op_annual"]),
        "ytd_real": r2(T["ytd"]), "prorata_operating": r2(sum(x for x in T["m_plan"][:as_of]) if False else T["op_annual"]*as_of/12.0),
        "projection_year_end": r2(T["proj"]),
        "monthly_real": [r2(x) for x in T["m_real"]], "monthly_plan": [r2(x) for x in T["m_plan"]],
        "monthly_recal": [r2(x) for x in T["m_recal"]],
        "quarter_plan": [r2(x) for x in T["q_plan"]], "quarter_real": [r2(x) for x in T["q_real"]],
    }
    with open(os.path.join(ws, "aghc_budget.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    t = out["totals"]
    print("OK -> aghc_budget.json (anchor run-rate, as_of %s)" % out["as_of_label"])
    print("  Portfolio: operativo annuo %.0f € | reale YTD %.0f € | proiezione fine anno %.0f € | tetto strategie %.0f €" % (
        t["operating_annual"], t["ytd_real"], t["projection_year_end"], t["annual_strategy"]))
    for s in out["structures"][:5]:
        print("  - %-30s op/mese %6.0f | YTD %6.0f | pace %s | recal/mese %6.0f | %s" % (
            s["name"], s["operating_monthly"], s["ytd_real"],
            (("%+.0f%%"%s["pace_pct"]) if s["pace_pct"] is not None else "n/d"), s["fwd_recal_monthly"], s["status"]))

if __name__ == "__main__":
    main()
