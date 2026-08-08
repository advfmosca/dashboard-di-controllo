#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_budget.py - Modulo budget AGHC: programmato annuale -> quarter -> mensile,
confronto con lo speso REALE e RICALIBRAZIONE per atterrare sull'annuale a fine anno.

Logica (mandato Francesco 2026-08-08): "considerando lo spending ad oggi rispetto al
programmato, arrivare alla spesa programmata a fine anno".
- Annuale = target autorevole (aghc_roster.json).
- Mesi CHIUSI (fino ad as_of) -> speso REALE (bloccato).
- Residuo = annuale - reale_YTD(chiusi). Distribuito sui mesi rimanenti secondo pesi
  stagionali (default: pesi in aghc_budget_weights.json; se assenti -> uniforme) e
  RINORMALIZZATO così che il piano annuo = annuale esatto.
- Per ogni struttura: passo (pace) vs pro-rata lineare, proiezione a fine anno al ritmo
  attuale, piano mensile ricalibrato, split per quarter, stato semaforico.

Input:  aghc_roster.json, aghc_actuals_monthly.json, [aghc_budget_weights.json]
Output: aghc_budget.json
Uso:    python3 build_budget.py --as-of-month 2026-07 --workspace .
"""
import argparse, json, os
from datetime import date, datetime

MESI = ["Gen","Feb","Mar","Apr","Mag","Giu","Lug","Ago","Set","Ott","Nov","Dic"]

def load(ws, p, req=True):
    fp = os.path.join(ws, p)
    if not os.path.exists(fp):
        if req: raise SystemExit(p + " mancante")
        return None
    return json.load(open(fp, encoding="utf-8"))

def r2(x): return round(x + 0.0, 2)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--as-of-month", required=True, help="YYYY-MM ultimo mese CHIUSO (reale bloccato)")
    ap.add_argument("--pace-tol", type=float, default=8.0, help="tolleranza %% pro-rata per stato on-track")
    args = ap.parse_args()
    ws = args.workspace

    roster = {s["name"]: s for s in load(ws, "aghc_roster.json")["structures"]}
    actuals = {s["name"]: s for s in load(ws, "aghc_actuals_monthly.json")["structures"]}
    weights_cfg = load(ws, "aghc_budget_weights.json", req=False) or {}
    wmap = weights_cfg.get("weights", {})  # {name: [12 pesi]} opzionale

    ay, am = map(int, args.as_of_month.split("-"))
    as_of = am  # numero mese chiuso (1..12)
    remaining_idx = list(range(as_of, 12))  # indici 0-based dei mesi da pianificare (as_of..11)

    out = {"schema_version": 1, "year": ay, "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
           "as_of_month": args.as_of_month, "as_of_label": MESI[as_of-1] + " " + str(ay),
           "method": "Mesi chiusi = speso reale (bloccato). Residuo annuale distribuito sui mesi rimanenti (pesi stagionali, default uniforme) e rinormalizzato per chiudere sull'annuale.",
           "structures": [], "totals": {}}

    T = {"annual":0.0,"ytd_real":0.0,"residual":0.0,"proj":0.0,
         "q_plan":[0,0,0,0],"q_real":[0,0,0,0],"m_plan":[0.0]*12,"m_real":[0.0]*12}

    for name, s in roster.items():
        annual = float(s["budget_annuale"])
        a = actuals.get(name, {})
        real = list(a.get("monthly", {}).get("total", [0.0]*12))
        real = [float(x or 0) for x in (real + [0.0]*12)[:12]]
        ytd_real = sum(real[:as_of])                 # mesi chiusi
        residual = max(annual - ytd_real, 0.0)
        over_annual = ytd_real > annual

        # pesi per i mesi rimanenti
        w = wmap.get(name)
        if w and len(w) == 12:
            rw = [max(float(w[i]), 0.0) for i in remaining_idx]
        else:
            rw = [1.0]*len(remaining_idx)   # uniforme
        sw = sum(rw) or 1.0
        plan = list(real)  # mesi chiusi = reale
        for k, i in enumerate(remaining_idx):
            plan[i] = r2(residual * rw[k] / sw)
        # aggiusta arrotondamento sull'ultimo mese
        drift = r2(annual - (sum(plan[:as_of]) + sum(plan[i] for i in remaining_idx)))
        if remaining_idx:
            plan[remaining_idx[-1]] = r2(plan[remaining_idx[-1]] + drift)

        # pace vs pro-rata lineare
        prorata = annual * as_of / 12.0
        pace_delta = ytd_real - prorata
        pace_pct = (pace_delta / prorata * 100.0) if prorata else None
        # proiezione a fine anno al ritmo YTD
        proj = ytd_real / as_of * 12.0 if as_of else 0.0
        # forward mensile consigliato (media sui mesi rimanenti)
        fwd_monthly = r2(residual / len(remaining_idx)) if remaining_idx else 0.0

        if over_annual:
            status = "over"
        elif pace_pct is None:
            status = "na"
        elif pace_pct > args.pace_tol:
            status = "over"
        elif pace_pct < -args.pace_tol:
            status = "under"
        else:
            status = "on_track"

        def qsum(v, q): return r2(sum(v[q*3:q*3+3]))
        q_plan = [qsum(plan, q) for q in range(4)]
        q_real = [qsum(real, q) for q in range(4)]

        out["structures"].append({
            "name": name, "annual": r2(annual), "has_tiktok": a.get("has_tiktok", False),
            "ytd_real": r2(ytd_real), "ytd_meta": r2(a.get("ytd_meta", 0)), "ytd_tiktok": r2(a.get("ytd_tiktok", 0)),
            "residual": r2(residual), "prorata_to_date": r2(prorata),
            "pace_delta": r2(pace_delta), "pace_pct": (r2(pace_pct) if pace_pct is not None else None),
            "projection_year_end": r2(proj), "projection_delta": r2(proj - annual),
            "fwd_monthly": fwd_monthly, "remaining_months": len(remaining_idx),
            "status": status,
            "monthly_real": [r2(x) for x in real],
            "monthly_plan": [r2(x) for x in plan],
            "quarter_plan": q_plan, "quarter_real": q_real,
        })

        T["annual"]+=annual; T["ytd_real"]+=ytd_real; T["residual"]+=residual; T["proj"]+=proj
        for i in range(12): T["m_plan"][i]+=plan[i]; T["m_real"][i]+=real[i]
        for q in range(4): T["q_plan"][q]+=q_plan[q]; T["q_real"][q]+=q_real[q]

    out["totals"] = {
        "annual": r2(T["annual"]), "ytd_real": r2(T["ytd_real"]), "residual": r2(T["residual"]),
        "prorata_to_date": r2(T["annual"]*as_of/12.0),
        "projection_year_end": r2(T["proj"]), "projection_delta": r2(T["proj"]-T["annual"]),
        "monthly_plan": [r2(x) for x in T["m_plan"]], "monthly_real": [r2(x) for x in T["m_real"]],
        "quarter_plan": [r2(x) for x in T["q_plan"]], "quarter_real": [r2(x) for x in T["q_real"]],
    }

    with open(os.path.join(ws, "aghc_budget.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("OK -> aghc_budget.json  (as_of %s)" % out["as_of_label"])
    t=out["totals"]
    print("  Portfolio annuale %.0f € | reale YTD %.0f € (pro-rata %.0f) | residuo %.0f | proiezione fine anno %.0f (%+.0f)" % (
        t["annual"], t["ytd_real"], t["prorata_to_date"], t["residual"], t["projection_year_end"], t["projection_delta"]))
    for s in out["structures"][:4]:
        print("  - %-32s ann %6.0f | YTD %6.0f | pace %s | fwd/mese %6.0f | %s" % (
            s["name"], s["annual"], s["ytd_real"], (("%+.0f%%"%s["pace_pct"]) if s["pace_pct"] is not None else "n/d"), s["fwd_monthly"], s["status"]))

if __name__ == "__main__":
    main()
