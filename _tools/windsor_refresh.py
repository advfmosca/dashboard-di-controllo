#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Refresh giornaliero Dashboard di Controllo — versione Claude Code (dal 22/10/2026).

Le chiamate a Windsor le fa l'agente (connettore MCP get_data). Questo script:
  plan     -> elenco delle chiamate da fare, con i parametri esatti (date calcolate su oggi);
  harvest  -> recupera i risultati di quelle chiamate dalle trascrizioni Claude Code
              (~/.claude/projects/**.jsonl e <sessione>/tool-results/) e li scrive in raw/;
  summary  -> righe del report della run lette da data.json, actions.json e dai file AGHC.
Nessun numero passa a mano: o arriva da un risultato get_data, o il file non viene scritto.

Exit code di harvest: 0 = tutto ok · 3 = manca almeno un file obbligatorio (Meta/Google/TikTok 16gg).
I file AGHC sono facoltativi: se ne manca anche uno stampa AGHC_OK=0 e gli stadi AGHC vanno saltati.
"""
import argparse, datetime as dt, glob, json, os, sys, time

WS = os.environ.get("DASH_WORKSPACE") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(WS, "raw")

ACCOUNTS_META = ["1201395876543423", "1489903155429629", "911357333863123", "1528485957725509",
                 "217115315497718", "4666471140299701", "687349689221880", "1372615496521110",
                 "821188209852436", "1432341844596179", "752450855779035", "30233607946222961",
                 "1849759899186169", "1353024533007038"]
SHARED = ["1528485957725509", "821188209852436"]
TT = ["7504967007843319824", "7498330316248203280", "7499093699838607377", "7498679494010667009",
      "7612666695502118929", "7626418949391351815"]

F_META = ["account_id", "account_name", "date", "campaign", "campaign_effective_status", "spend", "clicks",
          "impressions", "reach", "actions_landing_page_view", "actions_page_engagement", "actions_lead",
          "account_status"]
F_GOOGLE = ["account_id", "account_name", "date", "campaign", "spend", "clicks", "impressions"]
F_TIKTOK = ["account_id", "account_name", "date", "spend", "clicks", "impressions"]
F_AGHC_ACCT = ["account_id", "account_name", "spend", "clicks", "impressions", "reach", "actions_page_engagement"]
F_AGHC_CAMP = ["account_id", "campaign", "spend", "clicks", "impressions", "reach", "actions_page_engagement"]
F_AGHC_TT = ["account_id", "account_name", "spend", "impressions", "engagements"]
SPEND_GT0 = [["spend", "gt", 0]]


def plan(today=None):
    t = today or dt.date.today()
    ieri = t - dt.timedelta(days=1)
    cur_from = t.replace(day=1)
    prev_to = cur_from - dt.timedelta(days=1)
    prev_from = prev_to.replace(day=1)
    yoy_from = dt.date(t.year - 1, t.month, 1)
    yoy_to = dt.date(t.year - 1 + (t.month == 12), t.month % 12 + 1, 1) - dt.timedelta(days=1)
    jan = dt.date(ieri.year, 1, 1)
    first_day = t.day == 1          # il mese in corso non ha ancora giorni chiusi
    R = []

    def add(file, connector, fields, d_from, d_to, accounts=None, filters=None, required=False, empty=False):
        R.append({"file": file, "connector": connector, "fields": fields, "accounts": accounts,
                  "date_from": d_from.isoformat(), "date_to": d_to.isoformat(), "filters": filters,
                  "required": required, "empty": empty})

    # 1) BeeFamily + overview: 16 giorni chiusi (= date_preset last_16d), solo righe con spesa
    add("meta.json", "facebook", F_META, t - dt.timedelta(days=16), ieri, filters=SPEND_GT0, required=True)
    add("google.json", "google_ads", F_GOOGLE, t - dt.timedelta(days=16), ieri, filters=SPEND_GT0, required=True)
    add("tiktok.json", "tiktok", F_TIKTOK, t - dt.timedelta(days=16), ieri, filters=SPEND_GT0, required=True)
    # 1B) AGHC vista unica: corrente / MoM / YoY + giornalieri 30gg
    add("aghc_meta_current.json", "facebook", F_AGHC_ACCT, cur_from, ieri, ACCOUNTS_META, empty=first_day)
    add("aghc_meta_prev.json", "facebook", F_AGHC_ACCT, prev_from, prev_to, ACCOUNTS_META)
    add("aghc_meta_yoy.json", "facebook", F_AGHC_ACCT, yoy_from, yoy_to, ACCOUNTS_META)
    add("aghc_meta_camp_current.json", "facebook", F_AGHC_CAMP, cur_from, ieri, SHARED, empty=first_day)
    add("aghc_meta_camp_prev.json", "facebook", F_AGHC_CAMP, prev_from, prev_to, SHARED)
    add("aghc_meta_camp_yoy.json", "facebook", F_AGHC_CAMP, yoy_from, yoy_to, SHARED)
    add("aghc_tiktok_current.json", "tiktok", F_AGHC_TT, cur_from, ieri, TT, empty=first_day)
    add("aghc_tiktok_prev.json", "tiktok", F_AGHC_TT, prev_from, prev_to, TT)
    add("aghc_meta_daily.json", "facebook",
        ["account_id", "date", "spend", "impressions", "clicks", "reach", "actions_page_engagement"],
        ieri - dt.timedelta(days=29), ieri, ACCOUNTS_META)
    add("aghc_tiktok_daily.json", "tiktok", ["account_id", "date", "spend", "impressions", "engagements"],
        ieri - dt.timedelta(days=29), ieri, TT)
    # 1C) AGHC mensile YTD per il budget
    add("aghc_monthly_meta.json", "facebook", ["account_id", "year_month", "spend"], jan, ieri, ACCOUNTS_META)
    add("aghc_meta_camp_monthly.json", "facebook", ["account_id", "campaign", "year_month", "spend"], jan, ieri, SHARED)
    add("aghc_monthly_tiktok.json", "tiktok", ["account_id", "year_month", "spend"], jan, ieri, TT)
    return R


def call_params(r):
    p = {"connector": r["connector"], "fields": r["fields"]}
    if r["accounts"]:
        p["accounts"] = r["accounts"]
    p["date_from"], p["date_to"] = r["date_from"], r["date_to"]
    if r["filters"]:
        p["filters"] = r["filters"]
    return p


# ------------------------------------------------------------------ harvest
def _transcripts(since_hours):
    base = os.path.expanduser("~/.claude/projects")
    lim = time.time() - since_hours * 3600
    out = [f for f in glob.glob(os.path.join(base, "**", "*.jsonl"), recursive=True) if os.path.getmtime(f) >= lim]
    return sorted(out, key=os.path.getmtime)


def _result_text(block):
    c = block.get("content")
    if isinstance(c, list):
        c = "".join(x.get("text", "") for x in c if isinstance(x, dict))
    c = c or ""
    if c.lstrip().startswith("{"):
        return c
    # risultato troppo grande: l'harness lo salva in <sessione>/tool-results/
    for tok in c.split():
        t2 = tok.strip("`'\".,:;()[]")
        if t2.endswith((".txt", ".json")) and os.path.exists(t2):
            return open(t2, encoding="utf-8").read()
    return None


def _rows(txt):
    """Righe di un risultato get_data: {"status":"done","data":[...]} (connettore MCP) o {"result":[...]}.
    Un pull ancora "pending" o un errore non danno righe."""
    try:
        d = json.loads(txt or "")
    except Exception:
        return None
    if not isinstance(d, dict) or d.get("error"):
        return None
    if isinstance(d.get("result"), list):
        return d["result"]
    if d.get("status") in (None, "done") and isinstance(d.get("data"), list):
        return d["data"]
    return None


def _norm(v):
    if isinstance(v, str) and v.strip().startswith("["):
        try:
            v = json.loads(v)
        except Exception:
            pass
    if v in (None, "", []):
        return None
    if isinstance(v, list) and all(not isinstance(x, (list, dict)) for x in v):
        return sorted(str(x) for x in v)
    return json.dumps(v, sort_keys=True)


def _same(r, inp):
    if "get_data" not in inp.get("_tool", ""):
        return False
    if inp.get("date_preset"):
        return False
    for k in ("connector", "date_from", "date_to"):
        if str(inp.get(k)) != str(r[k]):
            return False
    return all(_norm(inp.get(k)) == _norm(r[k]) for k in ("fields", "accounts", "filters"))


def harvest(reqs, since_hours, also):
    found = {}
    for path in _transcripts(since_hours):
        uses = {}
        for line in open(path, encoding="utf-8", errors="ignore"):
            if '"tool_use"' not in line and '"tool_result"' not in line:
                continue
            try:
                o = json.loads(line)
            except Exception:
                continue
            content = (o.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for b in content:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "tool_use" and "get_data" in b.get("name", ""):
                    inp = dict(b.get("input") or {}); inp["_tool"] = b.get("name", "")
                    uses[b["id"]] = inp
                elif b.get("type") == "tool_result" and b.get("tool_use_id") in uses:
                    inp = uses[b["tool_use_id"]]
                    for r in reqs:
                        if r["empty"] or not _same(r, inp):
                            continue
                        txt = _result_text(b)
                        rows = _rows(txt)
                        if rows is not None:
                            found[r["file"]] = {"result": rows}      # l'ultima chiamata vince
    for r in reqs:
        if r["empty"]:
            found[r["file"]] = {"result": []}
    dirs = [RAW] + [os.path.join(d, "raw") for d in also]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        for f, data in found.items():
            json.dump(data, open(os.path.join(d, f), "w", encoding="utf-8"), ensure_ascii=False)
    return found


def _span(rows, key):
    vals = sorted({str(x.get(key)) for x in rows if isinstance(x, dict) and x.get(key)})
    return "%s→%s" % (vals[0], vals[-1]) if vals else "-"


# ------------------------------------------------------------------ summary
def _load(p):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return None


def eur(v):
    s = "{:,.2f}".format(float(v or 0))
    return s.replace(",", "X").replace(".", ",").replace("X", ".") + " €"


def summary(mirror):
    d = _load(os.path.join(mirror, "data.json")) or {}
    acts = (_load(os.path.join(mirror, "actions.json")) or {}).get("actions", [])
    ov = d.get("overview", {})
    print("RIF=%s" % d.get("reference_date_label", "?"))
    print("SPEND_TOT=%s" % eur(ov.get("total_spend")))
    print("ATTIVI=%s/%s" % (ov.get("active_accounts", "?"), ov.get("total_accounts", "?")))
    for p in ov.get("platforms", []):
        print("PIATTAFORMA %s=%s (%s account)" % (p.get("name"), eur(p.get("spend")), p.get("accounts")))
    sp = d.get("spending", {})
    print("ALERT_SPENDING zero=%d high=%d" % (len(sp.get("zero", [])), len(sp.get("high", []))))
    bf, ag = d.get("beefamily", {}).get("kpi", {}), d.get("aghc", {}).get("kpi", {})
    print("BF attivi=%s/%s spesa=%s" % (bf.get("actives"), bf.get("total"), eur(bf.get("total_spend"))))
    print("AGHC attivi=%s/%s spesa_ieri=%s" % (ag.get("actives"), ag.get("total"), eur(ag.get("total_spend_y"))))
    for a in acts:
        if a.get("type") in ("high_spending", "new_fermo"):
            print("AZIONE %s | %s | %s | %s | %s | %s" % (a.get("type"), a.get("title"), a.get("platform"),
                                                     a.get("details"), a.get("ad_url"), a.get("reference_date")))
    a = _load(os.path.join(mirror, "aghc_data.json")) or {}
    tot = a.get("totals", {})
    for ch in ("meta", "tiktok"):
        s = (tot.get(ch) or {}).get("spend") or {}
        if s:
            print("AGHC_%s %s=%s (MoM %s, %+.1f%%)" % (ch.upper(), a.get("current_label"), eur(s.get("cur")),
                                                     eur(s.get("prev")), float(s.get("delta") or 0)))
    b = (_load(os.path.join(mirror, "aghc_budget.json")) or {}).get("totals", {})
    if b:
        print("BUDGET annuale=%s ytd=%s proiezione=%s" % (eur(b.get("annual")), eur(b.get("ytd_real")),
                                                         eur(b.get("projection_year_end"))))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("plan")
    h = sub.add_parser("harvest")
    h.add_argument("--since-hours", type=float, default=8)
    h.add_argument("--also", action="append", default=[], help="altra cartella in cui scrivere raw/ (es. il mirror)")
    s = sub.add_parser("summary")
    s.add_argument("--mirror", default=WS)
    a = ap.parse_args()
    reqs = plan()

    if a.cmd == "plan":
        n = 0
        for r in reqs:
            if r["empty"]:
                print("--  %s: saltata (1° del mese, il mese in corso non ha giorni chiusi)" % r["file"])
                continue
            n += 1
            print("%2d. %s%s" % (n, r["file"], "  [obbligatoria]" if r["required"] else ""))
            print("    " + json.dumps(call_params(r), ensure_ascii=False))
        return 0

    if a.cmd == "summary":
        summary(a.mirror)
        return 0

    found = harvest(reqs, a.since_hours, a.also)
    ieri = (dt.date.today() - dt.timedelta(days=1)).isoformat()
    missing_req, missing_aghc = [], []
    for r in reqs:
        f = r["file"]
        if f not in found:
            (missing_req if r["required"] else missing_aghc).append(r)
            print("MANCA %s -> %s" % (f, json.dumps(call_params(r), ensure_ascii=False)))
            continue
        rows = found[f]["result"]
        key = "date" if "date" in r["fields"] else ("year_month" if "year_month" in r["fields"] else None)
        span = _span(rows, key) if key else "-"
        note = ""
        if r["required"] and not rows:
            note = "  ⚠️ vuoto"
        elif key == "date" and rows and _span(rows, "date").split("→")[-1] < ieri:
            note = "  ⚠️ ultimo giorno < ieri (%s): Windsor in ritardo?" % ieri
        print("OK %s: %d righe %s%s" % (f, len(rows), span, note))
    print("AGHC_OK=%d" % (0 if missing_aghc else 1))
    return 3 if missing_req else 0


if __name__ == "__main__":
    sys.exit(main())
