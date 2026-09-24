#!/usr/bin/env python3
"""
build_breakdown.py — Analisi per TIPOLOGIA DI OBIETTIVO e FONTE DI TRAFFICO (AGHC).

Input (estratti Windsor, connector "facebook"; TikTok dallo storico mensile):
  raw/aghc_obj_meta_camp.json       campaign x year_month  (+campaign_objective, reach, link click, LPV, ...)
  raw/aghc_src_meta_placement.json  campaign x year_month x publisher_platform x platform_position
  aghc_history.json                 serie mensili TikTok per struttura (tutte campagne AON/Reach)

Output: aghc_breakdown.json  -> letto da team.html (sezione "Obiettivi e fonti di traffico")

Classificazione obiettivo = nomenclatura campagna  "AGHC | <OBIETTIVO> <peso%> | <Struttura> [| variante]"
  AON -> aon · TRAFFICO -> traffico · CONVERSIONI -> conversioni · altro token (SENSI, BRACIAMI...) -> tematiche
Campagne con naming precedente: parole chiave (AON) e, in mancanza, obiettivo nativo Meta.

Pull Windsor da rifare prima di lanciare (date_from = 1 gennaio anno corrente, date_to = ieri, filtro spend>0,
account = meta_id di aghc_roster.json):
  facebook  fields: account_id,campaign,campaign_objective,year_month,spend,reach,impressions,clicks,
                    actions_link_click,actions_page_engagement,actions_landing_page_view,actions_video_view,
                    actions_offsite_conversion_fb_pixel_purchase,actions_omni_purchase
  facebook  fields: account_id,campaign,year_month,publisher_platform,platform_position,spend,impressions,
                    clicks,actions_link_click,actions_page_engagement
Uso: python3 build_breakdown.py --workspace .
"""
import argparse, json, os, re, datetime

# stesso roster di build_aghc.py / build_history.py: (nome, meta_id, keyword campagna, esclusioni, tiktok_id)
STRUCTS = [
    ("Altafiumara Resort", "1201395876543423", None, [], None),
    ("Hotel Castello", "1489903155429629", None, [], None),
    ("Hotel Della Piana", "911357333863123", None, [], "7504967007843319824"),
    ("Hannah Hotels", "1528485957725509", "hannah", ["terraces", "puntebianche"], None),
    ("Puntebianche Resort", "1528485957725509", "puntebianche", [], None),
    ("Hemanaire", "217115315497718", None, [], None),
    ("Livata", "4666471140299701", None, [], None),
    ("Hotel Lunetta", "687349689221880", None, [], "7498330316248203280"),
    ("Magari Estates", "1372615496521110", None, [], None),
    ("Marcella Royal Hotel", "821188209852436", "marcella", [], "7499093699838607377"),
    ("Terrazza Flavia", "821188209852436", "terrazza", [], None),
    ("Mare Hotel", "1432341844596179", None, [], "7498679494010667009"),
    ("Tenuta Montemagno Relais", "752450855779035", None, [], None),
    ("Villa Ermellina", "30233607946222961", None, [], "7612666695502118929"),
    ("Villa Giada", "1849759899186169", None, [], "7626418949391351815"),
    ("Villa Miliani", "1353024533007038", None, [], None),
]

OBJ_LABEL = {"aon": "Always On (notorietà)", "traffico": "Traffico", "conversioni": "Conversioni",
             "tematiche": "Promo e campagne tematiche"}
OBJ_ORDER = ["aon", "traffico", "conversioni", "tematiche"]

PLAT_LABEL = {"instagram": "Instagram", "facebook": "Facebook", "audience_network": "Audience Network",
              "messenger": "Messenger", "threads": "Threads", "tiktok": "TikTok", "unknown": "Altro"}
POS_LABEL = {
    ("instagram", "feed"): "Feed", ("instagram", "instagram_reels"): "Reels",
    ("instagram", "instagram_stories"): "Stories", ("instagram", "instagram_explore"): "Esplora",
    ("instagram", "instagram_explore_grid_home"): "Esplora", ("instagram", "instagram_search"): "Ricerca",
    ("instagram", "instagram_profile_feed"): "Feed profilo",
    ("facebook", "feed"): "Feed", ("facebook", "facebook_reels"): "Reels",
    ("facebook", "facebook_reels_overlay"): "Reels (overlay)", ("facebook", "facebook_stories"): "Stories",
    ("facebook", "instream_video"): "Video in-stream", ("facebook", "facebook_profile_feed"): "Feed profilo",
    ("facebook", "marketplace"): "Marketplace", ("facebook", "search"): "Ricerca",
    ("facebook", "facebook_notification"): "Notifiche", ("facebook", "right_hand_column"): "Colonna destra",
    ("facebook", "biz_disco_feed"): "Business Explore", ("threads", "threads_feed"): "Feed",
    ("tiktok", "tiktok"): "Per te (For You)",
}


def num(x):
    try:
        return float(x) if x is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def load(path):
    if not os.path.exists(path):
        return []
    d = json.load(open(path, encoding="utf-8"))
    return d.get("result", d) if isinstance(d, dict) else d


def ym(r):
    y, m = str(r.get("year_month", "")).split("|")
    return "%s-%02d" % (int(y), int(m))


def owner(acct, campaign):
    """Struttura a cui appartiene la campagna (stesse regole keyword/esclusioni della pipeline)."""
    c = (campaign or "").lower()
    for name, mid, kw, exc, _tt in STRUCTS:
        if mid != str(acct):
            continue
        if kw is None:
            return name
        if kw in c and not any(x in c for x in exc):
            return name
    return None


def classify(campaign, native=None):
    """-> (chiave obiettivo, peso pianificato % o None)"""
    name = (campaign or "").strip()
    up = name.upper()
    parts = [p.strip() for p in name.split("|")]
    if len(parts) >= 3 and parts[0].upper() == "AGHC":
        tok = parts[1].upper()
        m = re.search(r"(\d+)\s*%", tok)
        w = int(m.group(1)) if m else None
        head = tok.split()[0] if tok else ""
        key = {"AON": "aon", "TRAFFICO": "traffico", "CONVERSIONI": "conversioni"}.get(head, "tematiche")
        return key, w
    if re.search(r"\bAON\b", up):
        return "aon", None
    n = (native or "").upper()
    if "TRAFFIC" in n:
        return "traffico", None
    if "SALES" in n or "LEADS" in n or "CONVERSION" in n:
        return "conversioni", None
    return "tematiche", None


def blank():
    return {"spend": 0.0, "reach": 0.0, "impressions": 0.0, "clicks": 0.0, "link_clicks": 0.0,
            "engagement": 0.0, "lpv": 0.0, "video_views": 0.0, "purchases": None}


def add(a, r, meta=True):
    a["spend"] += num(r.get("spend"))
    a["reach"] += num(r.get("reach"))
    a["impressions"] += num(r.get("impressions"))
    a["clicks"] += num(r.get("clicks"))
    a["link_clicks"] += num(r.get("actions_link_click"))
    a["engagement"] += num(r.get("actions_page_engagement"))
    a["lpv"] += num(r.get("actions_landing_page_view"))
    a["video_views"] += num(r.get("actions_video_view"))
    p = r.get("actions_offsite_conversion_fb_pixel_purchase")
    if p is None:
        p = r.get("actions_omni_purchase")
    if p is not None:
        a["purchases"] = (a["purchases"] or 0) + num(p)


def rnd(a):
    out = {}
    for k, v in a.items():
        if v is None:
            out[k] = None
        elif k == "spend":
            out[k] = round(v, 2)
        else:
            out[k] = int(round(v))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default=".")
    a = ap.parse_args()
    ws = a.workspace
    camp = load(os.path.join(ws, "raw/aghc_obj_meta_camp.json"))
    plac = load(os.path.join(ws, "raw/aghc_src_meta_placement.json"))
    hist = json.load(open(os.path.join(ws, "aghc_history.json"), encoding="utf-8"))

    S = {n: {} for n, *_ in STRUCTS}   # struttura -> mese -> dati

    def M(name, month):
        return S[name].setdefault(month, {"obj": {}, "src": {}, "camps": {}})

    # --- obiettivi Meta (livello campagna) ---
    for r in camp:
        name = owner(r.get("account_id"), r.get("campaign"))
        if not name or num(r.get("spend")) <= 0:
            continue
        key, w = classify(r.get("campaign"), r.get("campaign_objective"))
        m = M(name, ym(r))
        o = m["obj"].setdefault(key, {"meta": blank(), "tiktok": blank(), "planned": set(), "campaigns": set()})
        add(o["meta"], r)
        if w is not None:
            o["planned"].add(w)
        o["campaigns"].add(r.get("campaign"))

    # --- TikTok (tutte campagne Reach / AON) dallo storico mensile ---
    months = hist.get("months", [])
    for s in hist.get("structures", []):
        if s["name"] not in S or not s.get("has_tiktok"):
            continue
        t = s["series"].get("tiktok") or {}
        for i, mo in enumerate(months):
            sp = num((t.get("spend") or [0] * len(months))[i])
            if sp <= 0:
                continue
            m = M(s["name"], mo)
            o = m["obj"].setdefault("aon", {"meta": blank(), "tiktok": blank(), "planned": set(), "campaigns": set()})
            tt = o["tiktok"]
            tt["spend"] += sp
            tt["reach"] += num(t["reach"][i])
            tt["impressions"] += num(t["impressions"][i])
            tt["clicks"] += num(t["clicks"][i])
            tt["engagement"] += num(t["interazioni"][i])
            # fonte TikTok
            src = m["src"].setdefault(("aon", "tiktok", "tiktok"), blank())
            src["spend"] += sp
            src["impressions"] += num(t["impressions"][i])
            src["clicks"] += num(t["clicks"][i])
            src["engagement"] += num(t["interazioni"][i])

    # --- fonti Meta (piattaforma x posizionamento x obiettivo) ---
    for r in plac:
        name = owner(r.get("account_id"), r.get("campaign"))
        if not name or num(r.get("spend")) <= 0:
            continue
        # obiettivo nativo non presente nel pull placement: lo ricavo dal pull campagne
        key, _ = classify(r.get("campaign"), NATIVE.get((str(r.get("account_id")), r.get("campaign"))))
        plat = (r.get("publisher_platform") or "unknown").lower()
        pos = (r.get("platform_position") or "unknown").lower()
        if plat == "audience_network":
            pos = "audience_network"
        m = M(name, ym(r))
        src = m["src"].setdefault((key, plat, pos), blank())
        add(src, r)

    out = {"schema_version": 1,
           "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
           "objectives": [{"key": k, "label": OBJ_LABEL[k]} for k in OBJ_ORDER],
           "structures": {}}
    for name, mm in S.items():
        blk = {}
        for mo, d in sorted(mm.items()):
            objs = []
            for k in OBJ_ORDER:
                o = d["obj"].get(k)
                if not o:
                    continue
                objs.append({"key": k, "label": OBJ_LABEL[k],
                             "planned_pct": sorted(o["planned"]) or None,
                             "campaigns": sorted(o["campaigns"]),
                             "meta": rnd(o["meta"]), "tiktok": rnd(o["tiktok"])})
            srcs = []
            for (k, plat, pos), v in d["src"].items():
                srcs.append(dict(rnd(v), obj=k, platform=plat, platform_label=PLAT_LABEL.get(plat, plat.title()),
                                 position=pos,
                                 position_label=("Rete di app e siti" if pos == "audience_network"
                                                 else POS_LABEL.get((plat, pos), pos.replace("_", " ").capitalize()))))
            srcs.sort(key=lambda x: -x["spend"])
            blk[mo] = {"objectives": objs, "sources": srcs}
        out["structures"][name] = blk
    json.dump(out, open(os.path.join(ws, "aghc_breakdown.json"), "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    n = sum(len(v) for v in out["structures"].values())
    print("OK -> aghc_breakdown.json | strutture %d | struttura-mese %d" % (len(out["structures"]), n))


NATIVE = {}
if __name__ == "__main__":
    import sys
    _ws = "."
    if "--workspace" in sys.argv:
        _ws = sys.argv[sys.argv.index("--workspace") + 1]
    for _r in load(os.path.join(_ws, "raw/aghc_obj_meta_camp.json")):
        NATIVE[(str(_r.get("account_id")), _r.get("campaign"))] = _r.get("campaign_objective")
    main()
