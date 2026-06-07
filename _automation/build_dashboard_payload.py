#!/usr/bin/env python3
"""
Costruisce le sezioni `cea` e `medtech` nel formato della dashboard master
(advfmosca/dashboard-di-controllo) partendo dai CSV di Alfredo.

Schema atteso:
{
  "cea": {
    "kpi": {actives, total, total_spend, total_contatti, total_lead, cpc_y, cpl_y, rosso, giallo, verde, nero},
    "entries": [
       {name, source:"ACTIVE", spend_y, lead_y, contatti_y, cpl_y, cpl_mean_3d, trend_3d:[], status:{color,label,reason}, ad_url}
    ],
    "recap": ""
  },
  "medtech": idem
}

Color mapping: rosso→red, giallo→yellow, verde→green, nero→gray
"""
import csv
import json
import re
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta

DATA_REPORT = sys.argv[1] if len(sys.argv) > 1 else "2026-05-18"
import os
import glob as _glob
_default_work = "/sessions/intelligent-amazing-einstein/mnt/outputs/work"
if not os.path.isdir(_default_work):
    # auto-detect: pick first /sessions/*/mnt/outputs/work that exists
    cands = _glob.glob("/sessions/*/mnt/outputs/work")
    if cands:
        _default_work = cands[0]
WORK = Path(os.environ.get("DASHBOARD_WORK_DIR", _default_work))
REPO_DASH = Path(os.environ.get("DASHBOARD_REPO_DIR", "/tmp/run-20260607-071428/dashboard-di-controllo"))
DATA_JSON = REPO_DASH / "data.json"
SNAP_DIR = REPO_DASH / "snapshots"
SNAP_FILE = SNAP_DIR / f"{DATA_REPORT}.json"
INDEX_JSON = SNAP_DIR / "index.json"

MEDTECH_META_ACCOUNT = "533672775128363"

# Color map for status
COL_MAP = {"rosso": "red", "giallo": "yellow", "verde": "green", "nero": "gray"}
LBL_MAP = {"rosso": "ROSSO", "giallo": "GIALLO", "verde": "VERDE", "nero": "NERO"}

# -------- helpers --------
def to_float(s):
    if s is None or s == "":
        return 0.0
    s = str(s).strip()
    if not s: return 0.0
    if "," in s and "." not in s: s = s.replace(",", ".")
    try: return float(s)
    except: return 0.0

def to_int(s):
    if s is None or s == "":
        return 0
    try: return int(float(str(s).strip()))
    except: return 0

def fmt_eur(v):
    if v is None: return "—"
    return (f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")) + " €"

def fmt_int(v):
    if v is None: return "—"
    try:
        return f"{int(v):,}".replace(",", ".")
    except Exception:
        return "—"

def date_minus(d_iso, days):
    return (datetime.strptime(d_iso, "%Y-%m-%d") - timedelta(days=days)).strftime("%Y-%m-%d")

def parse_window(adset):
    m = re.search(r"[Dd]al\s+(\d{1,2}[\./]\d{1,2})\s+al\s+(\d{1,2}[\./]\d{1,2})", adset)
    if m:
        return f"{m.group(1)} → {m.group(2)}"
    return ""

# -------- parse CSVs --------
def _csv_header_index(header_row, *aliases):
    """Ritorna l'indice della prima colonna nel cui nome (case-insensitive)
    matcha uno degli `aliases`. None se nessuna colonna trovata.
    Esempio: _csv_header_index(header, 'reach', 'copertura') → indice colonna reach."""
    norm = [str(h or "").strip().lower() for h in header_row]
    for alias in aliases:
        key = alias.strip().lower()
        if key in norm:
            return norm.index(key)
    return None

def parse_cea_csv():
    # Schema base: 0=Cliente; 1=Spesa; 2=Lead; 3=CPL; 4=CPM; 5=CTR; 9=Nome Campagna;
    #              10=Nome Adset; 11=Data; 12=CPC; 13=Impressioni; 14=Click; 15=Account ID (opzionale);
    #              16=Target geo (opzionale); 17=Audience size (opzionale).
    # Opzionali (lookup case-insensitive sull'header): "Reach"/"Copertura" e "Frequency"/"Frequenza".
    # Se le colonne non sono presenti, reach/frequency restano None e il dashboard mostra "—".
    rows = []
    with open(WORK / f"cea_{DATA_REPORT}.csv", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")
        header = next(reader)
        idx_reach = _csv_header_index(header, "reach", "copertura")
        idx_freq  = _csv_header_index(header, "frequency", "frequenza")
        for row in reader:
            if not row or len(row) < 14: continue
            cliente = row[0].strip()
            if not cliente: continue
            acc_id = (row[15].strip() if len(row) > 15 else "").replace("act_", "").strip()
            target_geo = row[16].strip() if len(row) > 16 else ""
            audience_size = row[17].strip() if len(row) > 17 else ""
            campagna = (row[9].strip() if len(row) > 9 else "") or ""
            reach_v = to_int(row[idx_reach]) if (idx_reach is not None and len(row) > idx_reach and row[idx_reach].strip()) else None
            freq_v  = to_float(row[idx_freq])  if (idx_freq  is not None and len(row) > idx_freq  and row[idx_freq].strip())  else None
            rows.append({
                "cliente": cliente,
                "campagna": campagna,
                "spesa": to_float(row[1]),
                "lead":  to_int(row[2]),
                "cpm":   to_float(row[4]),
                "ctr":   to_float(row[5]),
                "impr":  to_int(row[13]) if len(row) > 13 else 0,
                "click": to_int(row[14]) if len(row) > 14 else 0,
                "reach": reach_v,
                "frequency": freq_v,
                "account_id": acc_id,
                "target_geo": target_geo,
                "audience_size": audience_size,
            })
    # Aggregate per cliente: CPM e CTR vanno pesati per impressioni.
    # In più aggreghiamo le righe per (cliente, campagna) così possiamo esporre la
    # lista delle CAMPAGNE ATTIVE per la vista cliente — una card per campagna.
    # Più adset sotto la stessa campagna vengono sommati: spesa/lead/impr/click sommati,
    # adset_count incrementato.
    agg = defaultdict(lambda: {"spesa": 0.0, "lead": 0, "adset_count": 0,
                               "impr": 0, "click": 0, "reach_sum": 0, "reach_count": 0,
                               "freq_sum": 0.0, "freq_count": 0,
                               "cpm_sum": 0.0, "ctr_sum": 0.0,
                               "account_id": "", "target_geo": "", "audience_size": "",
                               "campagne": defaultdict(lambda: {"spesa": 0.0, "lead": 0,
                                                                "impr": 0, "click": 0,
                                                                "adset_count": 0})})
    for r in rows:
        a = agg[r["cliente"]]
        a["spesa"] += r["spesa"]
        a["lead"]  += r["lead"]
        a["impr"]  += r["impr"]
        a["click"] += r["click"]
        # Media pesata: CPM/CTR pesato per impressioni del riga
        a["cpm_sum"] += r["cpm"] * r["impr"]
        a["ctr_sum"] += r["ctr"] * r["impr"]
        a["adset_count"] += 1
        # Reach + Frequency (best-effort: la reach tra adset può overlap, sommiamo come proxy;
        # la frequency la prendiamo pesata sulle impressioni)
        if r.get("reach") is not None:
            a["reach_sum"] += r["reach"]
            a["reach_count"] += 1
        if r.get("frequency") is not None:
            a["freq_sum"] += r["frequency"] * (r.get("impr") or 0)
            a["freq_count"] += (r.get("impr") or 0)
        # Account ID + target_geo + audience_size: primo non-vuoto (statici per cliente)
        if r.get("account_id") and not a["account_id"]:
            a["account_id"] = r["account_id"]
        if r.get("target_geo") and not a["target_geo"]:
            a["target_geo"] = r["target_geo"]
        if r.get("audience_size") and not a["audience_size"]:
            a["audience_size"] = r["audience_size"]
        # Breakdown per campagna Meta
        camp_key = r["campagna"] or "(campagna senza nome)"
        c = a["campagne"][camp_key]
        c["spesa"] += r["spesa"]
        c["lead"]  += r["lead"]
        c["impr"]  += r["impr"]
        c["click"] += r["click"]
        c["adset_count"] += 1
    out = []
    for cli, v in agg.items():
        cpl = (v["spesa"] / v["lead"]) if v["lead"] > 0 else None
        cpm = (v["cpm_sum"] / v["impr"]) if v["impr"] > 0 else None
        ctr = (v["ctr_sum"] / v["impr"]) if v["impr"] > 0 else None
        # Reach aggregata (somma adset; underestimato vero overlap)
        reach_v = v["reach_sum"] if v["reach_count"] > 0 else None
        # Frequency: prima sceglie il campo CSV (pesato per impressioni), altrimenti deriva da imp/reach
        if v["freq_count"] > 0:
            freq_v = round(v["freq_sum"] / v["freq_count"], 2)
        elif reach_v and reach_v > 0:
            freq_v = round(v["impr"] / reach_v, 2)
        else:
            freq_v = None
        ad_url = (f"https://business.facebook.com/adsmanager/manage/campaigns?act={v['account_id']}"
                  if v["account_id"] else "")
        # Costruisci lista campagne attive, ordinata per spesa desc.
        # Una campagna è considerata "attiva" se ha avuto spesa > 0 nella giornata.
        campaigns_list = []
        for camp_name, cstat in v["campagne"].items():
            c_cpl = (cstat["spesa"] / cstat["lead"]) if cstat["lead"] > 0 else None
            campaigns_list.append({
                "name":         camp_name,
                "spend":        round(cstat["spesa"], 2),
                "lead":         cstat["lead"],
                "cpl":          round(c_cpl, 2) if c_cpl is not None else None,
                "impressions":  cstat["impr"],
                "clicks":       cstat["click"],
                "adset_count":  cstat["adset_count"],
                "active":       cstat["spesa"] > 0,
            })
        campaigns_list.sort(key=lambda c: -c["spend"])
        out.append({
            "cliente": cli,
            "spesa":   round(v["spesa"], 2),
            "lead":    v["lead"],
            "cpl":     round(cpl, 2) if cpl is not None else None,
            "cpm":     round(cpm, 2) if cpm is not None else None,
            "ctr":     round(ctr, 2) if ctr is not None else None,
            "impr":    v["impr"],
            "click":   v["click"],
            "reach":   reach_v,
            "frequency": freq_v,
            "adset_count": v["adset_count"],
            "account_id": v["account_id"],
            "ad_url": ad_url,
            "target_geo": v["target_geo"],
            "audience_size": v["audience_size"],
            "campaigns": campaigns_list,
        })
    out.sort(key=lambda x: -x["spesa"])
    return out

def parse_medtech_csv():
    # Schema CSV: stesso del CEA. Campagna è singola entry (no aggregazione cliente).
    # Opzionali: "Reach"/"Copertura" e "Frequency"/"Frequenza" — lookup case-insensitive sull'header.
    out = []
    with open(WORK / f"medtech_{DATA_REPORT}.csv", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")
        header = next(reader)
        idx_reach = _csv_header_index(header, "reach", "copertura")
        idx_freq  = _csv_header_index(header, "frequency", "frequenza")
        for row in reader:
            if not row or len(row) < 14: continue
            campagna = row[9].strip()
            adset = row[10].strip()
            spesa = to_float(row[1])
            lead = to_int(row[2])
            cpm  = to_float(row[4])
            ctr  = to_float(row[5])
            impr = to_int(row[13]) if len(row) > 13 else 0
            click = to_int(row[14]) if len(row) > 14 else 0
            reach_v = to_int(row[idx_reach]) if (idx_reach is not None and len(row) > idx_reach and row[idx_reach].strip()) else None
            freq_v  = to_float(row[idx_freq])  if (idx_freq  is not None and len(row) > idx_freq  and row[idx_freq].strip())  else None
            # Se manca freq esplicita ma c'è reach, deriva: freq = impr / reach
            if freq_v is None and reach_v and reach_v > 0:
                freq_v = round(impr / reach_v, 2)
            m = re.search(r"-\s*(?:Total\s+(?:Lift|Sculpt))\s*-\s*(.+)$", campagna, re.IGNORECASE)
            studio = m.group(1).strip() if m else campagna
            cpl = spesa / lead if lead > 0 else None
            out.append({
                "id": campagna,
                "studio": studio,
                "campagna": campagna,
                "window": parse_window(adset),
                "spesa": round(spesa, 2),
                "lead": lead,
                "cpl": round(cpl, 2) if cpl is not None else None,
                "cpm": round(cpm, 2) if cpm else None,
                "ctr": round(ctr, 2) if ctr else None,
                "impr": impr,
                "click": click,
                "reach": reach_v,
                "frequency": freq_v,
            })
    out.sort(key=lambda x: -x["spesa"])
    return out

# -------- semaphore (v2: lead-volume based) --------  # SEMAPHORE_V2
# Sostituita il 2026-05-22: il colore è guidato dalla media leads/day su 3 giorni
# rolling (incluso ieri), non più dal confronto CPL vs media. Soglie:
#   VERDE  ≥ 2 lead/day  (sopra soglia di copertura agenda appuntamenti)
#   GIALLO 1-2 lead/day  (sotto soglia, segnali di traction presenti)
#   ROSSO  < 1 lead/day  (volume insufficiente per il funnel di conversione)
#   NERO   spesa 0       (campagna ferma)
# Il CPL resta calcolato e visualizzato ma diventa informativo, non guida il colore.
def semaphore(spesa, lead_y, mean_leads, days_history):
    if spesa == 0:
        return ("nero", "Nessuna spesa registrata: campagna ferma.")
    if days_history < 2:
        # Cold start: fallback su lead di ieri come proxy
        avg = lead_y
        prefix = (
            f"In apprendimento (storico {days_history} {'giorno' if days_history == 1 else 'giorni'}): "
            f"valutazione provvisoria su lead di ieri ({lead_y})."
        )
    else:
        avg = mean_leads if mean_leads is not None else 0
        prefix = f"Media {avg:.1f} lead/day su {days_history} giorni rolling."
    if avg >= 2:
        return ("verde", f"{prefix} Sopra soglia di copertura agenda (≥2 lead/day): volume in linea con il benchmark di conversione appuntamenti.")
    if avg >= 1:
        return ("giallo", f"{prefix} A metà strada (1-2 lead/day): segnali presenti ma sotto soglia per coprire l'agenda appuntamenti.")
    return ("rosso", f"{prefix} Volume insufficiente (<1 lead/day): il funnel di conversione non ha materiale da lavorare.")

# -------- 3gg lookback (campagne corte) using local csv-daily-snapshots data.json --------
def load_history_csv_snapshots():
    """Read the cumulative history from the csv-daily-snapshots repo."""
    p = Path(os.environ.get("DASHBOARD_CSV_SNAPSHOTS_DIR", "/tmp/run-20260607-071428/csv-daily-snapshots")) / "data.json"
    if not p.exists():
        return {}
    return json.load(open(p)).get("history", {})

def mean_cpl(history, section, key_field, key_value, current_date):
    # Soglia 3gg invece di 7gg: campagne brevi (≈14 gg) richiedono ottimizzazione giornaliera
    cpls = []
    days_data = 0
    for i in range(1, 4):
        d = date_minus(current_date, i)
        items = history.get(d, {}).get(section, [])
        for it in items:
            if it.get(key_field) == key_value:
                days_data += 1
                if it.get("lead", 0) > 0 and it.get("cpl") is not None:
                    cpls.append(it["cpl"])
                break
    return (sum(cpls) / len(cpls) if cpls else None), days_data

def mean_leads(history, section, key_field, key_value, current_date, lead_today=0):
    """Media leads/day su 3 giorni rolling, INCLUSIVO di current_date (= ieri).
    `lead_today` è il valore di lead del current_date stesso (= lead_y).
    Ritorna (avg, days_with_data) dove days_with_data conta anche il current_date."""
    leads = [lead_today]   # include reference_date stesso
    days = 1
    for i in range(1, 3):  # i = 1, 2 → 2 giorni precedenti
        d = date_minus(current_date, i)
        items = history.get(d, {}).get(section, [])
        for it in items:
            if it.get(key_field) == key_value:
                leads.append(it.get("lead", 0) or 0)
                days += 1
                break
    avg = sum(leads) / len(leads) if leads else 0
    return avg, days

# -------- narrative + performance evaluation --------
def cpl_narrative(cpl, mean3, days_history, lead, spesa, color_it):
    """Genera frase argomentata sul trend del costo per contatto: contesto + valutazione + cosa significa."""
    if spesa == 0:
        return "Campagna ferma in giornata: nessuna distribuzione attiva e nessun aggiornamento dell'apprendimento. Da chiarire se è una pausa voluta o un blocco tecnico."
    if days_history < 3:
        if lead == 0:
            return f"Fase di apprendimento (giorno {days_history+1}/3): {fmt_eur(spesa)} investiti senza contatti. È normale nei primi giorni di erogazione; se anche oggi la campagna non genera richieste sarà utile una verifica rapida del modulo e del pubblico."
        if cpl is None:
            return f"Fase di apprendimento (giorno {days_history+1}/3): {lead} contatti raccolti, ancora poca storia per giudicare il costo per contatto. Servono altri giorni per attivare il confronto."
        return f"Fase di apprendimento (giorno {days_history+1}/3): primo costo per contatto utile a {fmt_eur(cpl)}. La valutazione vera arriva quando saranno disponibili almeno 3 giorni di storico."
    if lead == 0:
        return f"{fmt_eur(spesa)} investiti ieri senza contatti tracciati. Il punto di rottura può essere in tre aree: il tracciamento (pixel/CAPI), il modulo (caricamento o campi), oppure l'offerta non sufficientemente chiara. Verifica prioritaria."
    if mean3 is None or mean3 == 0:
        return f"Primi contatti consolidati a un costo di {fmt_eur(cpl)} ciascuno. Lo storico è ancora corto per il confronto: monitoriamo se nei prossimi 2 giorni il valore resta stabile."
    delta = (cpl - mean3) / mean3 * 100
    if cpl <= mean3:
        return f"Costo per contatto ieri {fmt_eur(cpl)}, sotto la media degli ultimi 3 giorni ({fmt_eur(mean3)}, {delta:+.0f}%). L'apprendimento sta consolidando: c'è margine per un aumento controllato del budget (+15-20%) senza compromettere l'efficienza."
    if delta <= 25:
        return f"Costo per contatto ieri {fmt_eur(cpl)} contro media 3 giorni {fmt_eur(mean3)} (+{delta:.0f}%): leggera salita, ancora ampiamente nella tolleranza. Da osservare oggi: se rimbalza sotto media è rumore di breve periodo; se cresce ancora si entra in zona gialla."
    if delta <= 50:
        return f"Costo per contatto ieri {fmt_eur(cpl)} contro media 3 giorni {fmt_eur(mean3)} (+{delta:.0f}%): tendenza in salita, vicina al limite +50%. È probabile una saturazione delle creatività o un'asta più competitiva: rotazione creativa consigliata entro 48 ore."
    return f"Costo per contatto ieri {fmt_eur(cpl)} contro media 3 giorni {fmt_eur(mean3)} (+{delta:.0f}%, oltre +50%): fuori scala. La combinazione creatività + pubblico + offerta non sta più convertendo agli stessi costi. Intervento immediato: nuovo set creativo + verifica targeting + revisione delle puntate d'asta."


# Soglie performance Meta Lead Ads (settore estetica/medical leggermente diverso da retail)
_CTR_GOOD = 1.5   # ≥ 1.5% buono, ≥ 2.0% ottimo
_CTR_LOW  = 0.8   # < 0.8% basso
_CPM_HIGH = 12.0  # > 12 € audience cara
_CPM_LOW  = 8.0   # ≤ 8 € audience economica

def performance_eval(ctr, cpm, impr, lead):
    """Valutazione combinata CTR+CPM con suggerimento azione."""
    if impr is None or impr == 0:
        return "Nessun dato di visibilità in questo giorno (impressioni a zero)."
    bits = []
    # Classificazione CTR
    ctr_v = ctr if ctr is not None else 0
    cpm_v = cpm if cpm is not None else 0
    if ctr_v >= 2.0:
        ctr_lbl = f"CTR {ctr_v:.2f}% (ottimo)"
        ctr_cat = "high"
    elif ctr_v >= _CTR_GOOD:
        ctr_lbl = f"CTR {ctr_v:.2f}% (buono)"
        ctr_cat = "high"
    elif ctr_v >= _CTR_LOW:
        ctr_lbl = f"CTR {ctr_v:.2f}% (nella media)"
        ctr_cat = "mid"
    else:
        ctr_lbl = f"CTR {ctr_v:.2f}% (basso)"
        ctr_cat = "low"
    # Classificazione CPM
    if cpm_v == 0:
        cpm_lbl = "CPM n/d"
        cpm_cat = "mid"
    elif cpm_v <= _CPM_LOW:
        cpm_lbl = f"CPM {fmt_eur(cpm_v)} (contenuto)"
        cpm_cat = "low"
    elif cpm_v <= _CPM_HIGH:
        cpm_lbl = f"CPM {fmt_eur(cpm_v)} (in media)"
        cpm_cat = "mid"
    else:
        cpm_lbl = f"CPM {fmt_eur(cpm_v)} (alto)"
        cpm_cat = "high"
    # Suggerimento azione (matrix CTR × CPM)
    if ctr_cat == "high" and cpm_cat == "low":
        action = "Creative + audience funzionano bene a costi contenuti. Spazio per scalare il budget del 20–30% senza forzare l'asta."
    elif ctr_cat == "high" and cpm_cat == "mid":
        action = "Creative aggancia bene il pubblico ma il costo media è in linea. Scaling controllato (+15%) tenendo d'occhio la frequenza."
    elif ctr_cat == "high" and cpm_cat == "high":
        action = "Creative performa ma l'audience è cara/satura. Ampliare il targeting (lookalike più ampi o nuovi interessi) per ridurre la pressione sull'asta."
    elif ctr_cat == "mid" and cpm_cat == "low":
        action = "Distribuzione efficiente ma engagement medio. Si può testare un'angolazione creativa più diretta per spingere il CTR."
    elif ctr_cat == "mid" and cpm_cat == "mid":
        action = "Performance regolare, niente segnali di rottura. Confermare assetto e preparare un test creative a basso budget per la prossima settimana."
    elif ctr_cat == "mid" and cpm_cat == "high":
        action = "CPM in salita ma CTR tiene: audience che sta diventando cara. Refresh creative entro 7 giorni per non scivolare in saturazione."
    elif ctr_cat == "low" and cpm_cat == "low":
        action = "Algoritmo distribuisce a basso costo ma la creative non aggancia. Refresh creative prioritario — sostituire l'asset principale."
    elif ctr_cat == "low" and cpm_cat == "mid":
        action = "Creative non aggancia, costi in linea. Test di 2 nuove varianti creative su angolazioni diverse, mantenendo audience e budget."
    else:  # low + high
        action = "Audience cara E creative poco reattiva: combinazione peggiore. Ricostruire campagna: nuovo creative + revisione targeting + ripartire con budget contenuto."
    return f"{ctr_lbl} · {cpm_lbl}. {action}"


# -------- frequency analysis (Meta lead-gen) --------
# Scala basata su benchmark Meta lead-gen estetico/medical:
#   ≤ 1.5     pubblico fresco — fase apprendimento
#   1.6 – 2.5 sweet spot       — ottimale
#   2.6 – 3.5 inizio saturazione — da monitorare
#   3.6 – 5.0 saturazione concreta — alta
#   > 5.0     fatigue conclamata — critica
def freq_bucket(frequency):
    """Ritorna (code, label) per la frequency. None → ('', '')."""
    if frequency is None:
        return ("", "")
    f = float(frequency)
    if f <= 1.5:
        return ("bassa", "Bassa · pubblico fresco")
    if f <= 2.5:
        return ("ottimale", "Ottimale")
    if f <= 3.5:
        return ("monitorare", "Da monitorare")
    if f <= 5.0:
        return ("alta", "Alta · saturazione")
    return ("critica", "Critica · fatigue")

def freq_analysis(frequency, lead, reach, impressions):
    """Narrative breve (1 paragrafo) per la sezione 'Analisi frequenza' (vista team).
    Logica: incrocia bucket frequenza × lead. Ritorna (code_color, text).
    code_color ∈ {'rosso','giallo','verde',''} per coerenza CSS con .nc-story.<code>."""
    if frequency is None:
        return ("", "")
    bucket, label = freq_bucket(frequency)
    f = float(frequency)
    reach_str = f"Reach {fmt_int(reach)}" if reach else "—"
    impr_str  = fmt_int(impressions) if impressions else "—"
    lead_v = lead or 0
    if bucket in ("bassa",):
        if lead_v > 0:
            return ("verde",
                f"Frequenza {f:.2f} (zona <b>{label}</b>): le {reach_str.replace('Reach ', '')} persone raggiunte "
                f"hanno visto l'annuncio in media {f:.1f} volte, ricevendo già richieste — combo virtuosa "
                f"di pubblico fresco e conversione. <b>Ottimo per scaling</b>.")
        return ("",
            f"Frequenza {f:.2f} (zona <b>{label}</b>): il pubblico è ancora poco esposto al messaggio. "
            f"È <b>presto per giudicare</b>: la fase di apprendimento ha bisogno di più ripetizioni prima di "
            f"valutare la capacità di convertire.")
    if bucket in ("ottimale",):
        if lead_v > 0:
            return ("verde",
                f"Frequenza {f:.2f} (zona <b>{label}</b>): le persone raggiunte hanno visto l'annuncio in media "
                f"{f:.1f} volte — <b>sweet spot per lead-gen</b>, il messaggio entra senza saturare il pubblico. "
                f"<b>Niente da toccare sul front-end</b>, c'è margine per scaling controllato del budget "
                f"prima di rischiare la saturazione.")
        return ("giallo",
            f"Frequenza {f:.2f} (zona <b>{label}</b>): esposizione adeguata ma <b>0 lead</b> nonostante "
            f"il pubblico abbia visto l'annuncio in media {f:.1f} volte. Il problema non è la frequenza: "
            f"verificare <b>audience</b> (qualità) e <b>angolazione dell'offerta</b> "
            f"(timing, urgenza, ricettività del target in questa finestra) — il modulo Meta è già minimal e le domande sono essenziali, il punto di rottura non è lì.")
    if bucket in ("monitorare",):
        if lead_v > 0:
            return ("giallo",
                f"Frequenza {f:.2f} (zona <b>{label}</b>): il pubblico è ancora ricettivo e converte "
                f"({lead_v} {'contatto' if lead_v == 1 else 'contatti'}), ma siamo nella fascia in cui inizia la saturazione. "
                f"Conviene <b>preparare il refresh creative</b> da introdurre nei prossimi 5-7 giorni per non "
                f"perdere efficacia.")
        return ("giallo",
            f"Frequenza {f:.2f} (zona <b>{label}</b>): l'esposizione inizia a saturare e <b>nessun contatto</b> arriva. "
            f"Front-end <b>al limite</b>: ruotare creative entro 48h e verificare offerta — siamo nella fascia che "
            f"separa il sweet spot dalla fatigue.")
    if bucket in ("alta",):
        if lead_v > 0:
            return ("giallo",
                f"Frequenza {f:.2f} (zona <b>{label}</b>): saturazione concreta, ma il front-end <b>continua a "
                f"convertire</b> ({lead_v} {'contatto' if lead_v == 1 else 'contatti'}). Significa che creative e offerta tengono, "
                f"ma il pubblico è cotto: <b>ruotare creative entro 24-48h</b> o ampliare l'audience per spezzare "
                f"la pressione sull'asta.")
        return ("rosso",
            f"Frequenza {f:.2f} (zona <b>{label}</b>): il pubblico è stato esposto in media {f:.1f} volte ma "
            f"<b>nessun contatto</b> è arrivato. Combinazione tipica del <b>front-end NON adatto</b> — creative "
            f"e/o offerta non agganciano l'audience nonostante l'esposizione massiccia. Azioni: (1) sospendere "
            f"creative attuali, (2) sostituire con nuovo set basato su un benefit chiaro, (3) se persiste allargare "
            f"il pubblico per spezzare la saturazione.")
    # critica
    if lead_v > 0:
        return ("rosso",
            f"Frequenza {f:.2f} (zona <b>{label}</b>): pubblico in <b>fatigue conclamata</b>. Anche se arrivano "
            f"ancora {lead_v} {'contatto' if lead_v == 1 else 'contatti'}, la curva sta per crollare: <b>stop creative attuali</b> "
            f"e rifresh completo + revisione targeting prima che il CPL esploda.")
    return ("rosso",
        f"Frequenza {f:.2f} (zona <b>{label}</b>): <b>fatigue conclamata</b> con <b>0 lead</b>. Il front-end ha "
        f"esaurito la spinta su questo pubblico. Intervento immediato: pausa, rewrite completo del set creative, "
        f"revisione targeting, ripartenza con budget contenuto.")


# -------- audience narrative (v2: per ROSSE/GIALLE) --------  # SEMAPHORE_V2
# Diagnosi che incrocia audience size × CTR × frequenza × reach per spiegare
# perché una campagna non sta generando lead. 4 etichette possibili:
#   - "Audience con potenziale di lead"   → pubblico c'è, creative aggancia: problema downstream
#   - "Audience poco recettiva"            → creative non aggancia: problema messaggio
#   - "Zona target vuota / esaurita"       → bacino troppo piccolo: problema targeting
#   - "Audience tiepida"                   → zona grigia, segnali misti
_AUD_CTR_GOOD = 1.5    # ≥ → buono
_AUD_CTR_LOW  = 0.8    # < → basso
_AUD_FREQ_SAT = 2.5    # > → saturazione iniziale
_AUD_FREQ_HIGH = 5.0   # > → fatigue
_AUD_REACH_TINY = 1500 # < → bacino troppo piccolo
_AUD_SMALL_AUDIENCE = 30_000  # audience dichiarata < 30K = small

def _parse_audience_size(s):
    """'279K' -> 279000, '11.3M' -> 11_300_000, '20K' -> 20000."""
    if not s: return None
    s = str(s).strip().upper().replace(" ", "")
    m = re.match(r"([\d.,]+)\s*([KM])?", s)
    if not m: return None
    try:
        n = float(m.group(1).replace(",", "."))
    except: return None
    unit = m.group(2) or ""
    if unit == "K": n *= 1_000
    elif unit == "M": n *= 1_000_000
    return int(n)

def audience_narrative(lead_avg, ctr, freq, reach, audience_size_str, lead_y):
    """Ritorna dict {label, code, text} oppure None se non applicabile.
    code ∈ {'rosso','giallo'} per coerenza CSS con .rational.<code>."""
    if reach is None and ctr is None and freq is None:
        return None  # nessun dato per diagnosi
    audience_n = _parse_audience_size(audience_size_str)
    reach_v = reach or 0
    ctr_v = ctr if ctr is not None else 0.0
    freq_v = freq if freq is not None else 0.0
    aud_str = audience_size_str if audience_size_str else "—"
    reach_str = fmt_int(reach_v) if reach_v else "—"

    # Check #1: ZONA TARGET VUOTA / ESAURITA
    is_tiny_reach = reach_v > 0 and reach_v < _AUD_REACH_TINY
    is_burnt = freq_v > _AUD_FREQ_HIGH
    is_small_audience = audience_n is not None and audience_n < _AUD_SMALL_AUDIENCE
    if is_tiny_reach or is_burnt or (is_small_audience and freq_v > 2.0):
        bits = []
        if reach_v: bits.append(f"reach {reach_str}")
        if audience_n: bits.append(f"audience dichiarata {aud_str}")
        if freq_v: bits.append(f"frequenza {freq_v:.2f}")
        diag = " · ".join(bits) if bits else "dati audience parziali"
        return {
            "label": "Zona target vuota / esaurita",
            "code": "rosso",
            "text": (
                f"{diag}. Il bacino è troppo ridotto per sostenere l'investimento giornaliero — "
                f"{'poche persone nuove da intercettare e già esposte oltre soglia' if freq_v > 3 else 'poche persone nuove da intercettare in proporzione al budget impostato'}. "
                f"<b>Zona target vuota</b>: l'audience non regge il ritmo di spesa. "
                f"Allargare il raggio geografico (+5-10 km) o aprire un secondo set di interessi prima di rimettere mano alla creatività."
            ),
        }

    # Check #2: AUDIENCE POCO RECETTIVA (CTR basso)
    if ctr_v > 0 and ctr_v < _AUD_CTR_LOW:
        sat_note = (
            f" e frequenza {freq_v:.2f} già in fascia di saturazione iniziale (>2.5) — la creatività non aggancia E il pubblico è cotto"
            if freq_v > _AUD_FREQ_SAT
            else f" con frequenza {freq_v:.2f} ancora nella norma — il pubblico vede l'annuncio ma non lo trova rilevante"
        )
        return {
            "label": "Audience poco recettiva",
            "code": "rosso",
            "text": (
                f"CTR {ctr_v:.2f}% sotto soglia di engagement (target ≥{_AUD_CTR_GOOD}%){sat_note}. "
                f"<b>Audience poco recettiva</b>: il problema non è il bacino né la pressione, è il messaggio. "
                f"Refresh creative entro 48h con angolazione diversa (benefit chiaro in head, prova sociale o leva temporale), audience invariata."
            ),
        }

    # Check #3: AUDIENCE CON POTENZIALE LEAD (CTR buono)
    if ctr_v >= _AUD_CTR_GOOD:
        if freq_v > _AUD_FREQ_SAT:
            label = "Audience con potenziale, in saturazione iniziale"
            text = (
                f"CTR {ctr_v:.2f}% sopra la media (target ≥{_AUD_CTR_GOOD}%), frequenza {freq_v:.2f} sopra il sweet spot (1.5-2.5): "
                f"il pubblico ha già visto l'annuncio più volte. <b>Preparare il refresh creative</b> nei prossimi 5-7 giorni per non perdere "
                f"l'aggancio, in parallelo rivedere l'angolazione dell'offerta (timing, stagionalità, leva di urgenza) — il modulo Meta è già minimal, "
                f"se il pubblico apre ma non chiude è perché l'offerta in questa finestra non sta intercettando l'attenzione."
            )
        else:
            label = "Audience con potenziale di lead"
            consumed_pct = (reach_v / audience_n * 100) if (audience_n and reach_v) else None
            extra = (
                f" Reach {reach_str} su bacino dichiarato {aud_str} (consumato il {consumed_pct:.2f}%)."
                if consumed_pct
                else f" Reach {reach_str}, frequenza {freq_v:.2f} ancora fresca."
            )
            text = (
                f"CTR {ctr_v:.2f}% sopra la media (target ≥{_AUD_CTR_GOOD}%).{extra} "
                f"Aggancio e copertura ci sono, ma la conversione finale non scatta. Il modulo Meta è già minimal "
                f"(domande essenziali, attrito quasi nullo): il punto di rottura sta nell'<b>offerta</b>, che probabilmente "
                f"non è arrivata nel momento giusto o in questa finestra non sta godendo dell'attenzione necessaria dal target. "
                f"Da rivedere l'angolazione (urgenza, prova sociale, leva stagionale) o ri-testare l'offerta in una finestra temporale diversa "
                f"prima di mettere mano a creative o targeting."
            )
        return {
            "label": label,
            "code": "giallo" if lead_avg >= 1 else "rosso",
            "text": text,
        }

    # Check #4: AUDIENCE TIEPIDA (zona grigia 0.8 ≤ CTR < 1.5%)
    return {
        "label": "Audience tiepida",
        "code": "giallo",
        "text": (
            f"CTR {ctr_v:.2f}% in fascia neutra (0.8-1.5%), frequenza {freq_v:.2f}, reach {reach_str}. "
            f"<b>Audience tiepida</b>: segnali misti — né rifiuto netto né adesione chiara. "
            f"Test A/B di una variante creative su angolazione diversa mantenendo budget e audience: "
            f"se sblocca il CTR vuol dire che mancava il match copy/pubblico, altrimenti il problema è a valle."
        ),
    }



# -------- entry builders --------
def entry_status(color_it, reason):
    return {
        "color": COL_MAP[color_it],
        "label": LBL_MAP[color_it],
        "reason": reason,
    }

def build_cea_payload(items, history, date_str):
    entries = []
    counts = {"rosso": 0, "giallo": 0, "verde": 0, "nero": 0}
    tot_spend = 0.0
    tot_lead = 0
    for it in items:
        mean7, days = mean_cpl(history, "cea", "cliente", it["cliente"], date_str)
        avg_leads, days_v2 = mean_leads(history, "cea", "cliente", it["cliente"], date_str, lead_today=it["lead"])  # SEMAPHORE_V2
        sem, reason = semaphore(it["spesa"], it["lead"], avg_leads, days_v2)
        counts[sem] += 1
        tot_spend += it["spesa"]
        tot_lead += it["lead"]
        narrative = cpl_narrative(it["cpl"], mean7, days, it["lead"], it["spesa"], sem)
        perf_eval = performance_eval(it.get("ctr"), it.get("cpm"), it.get("impr"), it["lead"])
        freq_v = it.get("frequency")
        f_code, f_label = freq_bucket(freq_v)
        f_color, f_text = freq_analysis(freq_v, it["lead"], it.get("reach"), it.get("impr"))
        entries.append({
            "name": it["cliente"],
            "source": "ACTIVE",
            "spend_y": it["spesa"],
            "lead_y": it["lead"],
            "contatti_y": it["lead"],
            "cpl_y": it["cpl"],
            "cpl_mean_3d": round(mean7, 2) if mean7 is not None else None,
            "cpm": it.get("cpm"),
            "ctr": it.get("ctr"),
            "impressions": it.get("impr"),
            "clicks": it.get("click"),
            "reach": it.get("reach"),
            "frequency": freq_v,
            "freq_bucket": f_code,
            "freq_bucket_label": f_label,
            "freq_analysis_color": f_color,
            "freq_analysis": f_text,
            "mean_leads_3d": round(avg_leads, 2),  # SEMAPHORE_V2: nuovo KPI driver
            "days_history": days_v2,                # SEMAPHORE_V2
            "audience_narrative": audience_narrative(  # SEMAPHORE_V2: solo per rosse/gialle
                avg_leads, it.get("ctr"), freq_v, it.get("reach"), it.get("audience_size"), it["lead"]
            ) if sem in ("rosso", "giallo") else None,
            "trend_3d": [],
            "prev7_spend": 0,
            "prev7_lead": 0,
            "prev7_contatti": 0,
            "status": entry_status(sem, reason),
            "cpl_narrative": narrative,
            "performance_eval": perf_eval,
            "ad_url": it.get("ad_url") or "",
            "target_geo": it.get("target_geo") or "",
            "audience_size": it.get("audience_size") or "",
            # Breakdown per campagna Meta (usato dalla vista cliente per il blocco
            # "Campagne attive" con Target + Grandezza Pubblico per campagna).
            "campaigns": it.get("campaigns") or [],
        })
    # sort: red > yellow > gray > green
    order = {"red": 0, "yellow": 1, "gray": 2, "green": 3}
    entries.sort(key=lambda e: (order.get(e["status"]["color"], 9), -e["spend_y"]))
    cpl_y = (tot_spend / tot_lead) if tot_lead > 0 else None
    return {
        "kpi": {
            "actives": len(items),
            "total": len(items),
            "total_spend": round(tot_spend, 2),
            "total_contatti": tot_lead,
            "total_lead": tot_lead,
            "cpc_y": round(cpl_y, 2) if cpl_y is not None else None,
            "cpl_y": round(cpl_y, 2) if cpl_y is not None else None,
            "rosso": counts["rosso"],
            "giallo": counts["giallo"],
            "verde": counts["verde"],
            "nero": counts["nero"],
        },
        "entries": entries,
        "recap": "",
    }

def build_medtech_payload(items, history, date_str):
    entries = []
    counts = {"rosso": 0, "giallo": 0, "verde": 0, "nero": 0}
    tot_spend = 0.0
    tot_lead = 0
    for it in items:
        mean7, days = mean_cpl(history, "medtech", "id", it["id"], date_str)
        avg_leads, days_v2 = mean_leads(history, "medtech", "id", it["id"], date_str, lead_today=it["lead"])  # SEMAPHORE_V2
        sem, reason = semaphore(it["spesa"], it["lead"], avg_leads, days_v2)
        counts[sem] += 1
        tot_spend += it["spesa"]
        tot_lead += it["lead"]
        narrative = cpl_narrative(it["cpl"], mean7, days, it["lead"], it["spesa"], sem)
        perf_eval = performance_eval(it.get("ctr"), it.get("cpm"), it.get("impr"), it["lead"])
        freq_v = it.get("frequency")
        f_code, f_label = freq_bucket(freq_v)
        f_color, f_text = freq_analysis(freq_v, it["lead"], it.get("reach"), it.get("impr"))
        entries.append({
            "name": it["campagna"],
            "source": "ACTIVE",
            "spend_y": it["spesa"],
            "lead_y": it["lead"],
            "contatti_y": it["lead"],
            "cpl_y": it["cpl"],
            "cpl_mean_3d": round(mean7, 2) if mean7 is not None else None,
            "cpm": it.get("cpm"),
            "ctr": it.get("ctr"),
            "impressions": it.get("impr"),
            "clicks": it.get("click"),
            "reach": it.get("reach"),
            "frequency": freq_v,
            "freq_bucket": f_code,
            "freq_bucket_label": f_label,
            "freq_analysis_color": f_color,
            "freq_analysis": f_text,
            "mean_leads_3d": round(avg_leads, 2),  # SEMAPHORE_V2: nuovo KPI driver
            "days_history": days_v2,                # SEMAPHORE_V2
            "audience_narrative": audience_narrative(  # SEMAPHORE_V2: solo per rosse/gialle
                avg_leads, it.get("ctr"), freq_v, it.get("reach"), it.get("audience_size"), it["lead"]
            ) if sem in ("rosso", "giallo") else None,
            "trend_3d": [],
            "prev7_spend": 0,
            "prev7_lead": 0,
            "prev7_contatti": 0,
            "status": entry_status(sem, reason),
            "cpl_narrative": narrative,
            "performance_eval": perf_eval,
            "ad_url": f"https://business.facebook.com/adsmanager/manage/campaigns?act={MEDTECH_META_ACCOUNT}",
            # Per MedTech ogni entry è già una campagna singola: lista con un solo elemento
            # così la vista cliente usa il blocco "Campagne attive" in modo uniforme con CEA/BF/AGHC.
            "campaigns": [{
                "name":        it["campagna"],
                "spend":       it["spesa"],
                "lead":        it["lead"],
                "cpl":         it["cpl"],
                "impressions": it.get("impr"),
                "clicks":      it.get("click"),
                "active":      it["spesa"] > 0,
            }],
        })
    order = {"red": 0, "yellow": 1, "gray": 2, "green": 3}
    entries.sort(key=lambda e: (order.get(e["status"]["color"], 9), -e["spend_y"]))
    cpl_y = (tot_spend / tot_lead) if tot_lead > 0 else None
    return {
        "kpi": {
            "actives": len(items),
            "total": len(items),
            "total_spend": round(tot_spend, 2),
            "total_contatti": tot_lead,
            "total_lead": tot_lead,
            "cpc_y": round(cpl_y, 2) if cpl_y is not None else None,
            "cpl_y": round(cpl_y, 2) if cpl_y is not None else None,
            "rosso": counts["rosso"],
            "giallo": counts["giallo"],
            "verde": counts["verde"],
            "nero": counts["nero"],
        },
        "entries": entries,
        "recap": "",
    }

# -------- merge into data.json + snapshot --------
def _update_overview_projects(target, cea_payload, medtech_payload):
    """Aggiunge/aggiorna 'Med & Tech' e 'CEA' in overview.projects, ricalcola pct."""
    if "overview" not in target or "projects" not in target["overview"]:
        return
    projects = [p for p in target["overview"]["projects"] if p["name"] not in ("Med & Tech", "CEA")]
    mt_spend = (medtech_payload.get("kpi", {}) or {}).get("total_spend", 0) or 0
    mt_count = (medtech_payload.get("kpi", {}) or {}).get("total", 0) or 0
    cea_spend = (cea_payload.get("kpi", {}) or {}).get("total_spend", 0) or 0
    cea_count = (cea_payload.get("kpi", {}) or {}).get("total", 0) or 0
    if mt_spend > 0 or mt_count > 0:
        projects.append({"name": "Med & Tech", "spend": round(mt_spend, 2), "accounts": mt_count})
    if cea_spend > 0 or cea_count > 0:
        projects.append({"name": "CEA", "spend": round(cea_spend, 2), "accounts": cea_count})
    tot = sum(p["spend"] for p in projects) or 1
    for p in projects:
        p["pct"] = round(p["spend"] / tot * 100, 2)
    target["overview"]["projects"] = projects

def merge_into_dashboard(cea_payload, medtech_payload, date_str):
    now = datetime.now()
    iso_now = now.strftime("%Y-%m-%dT%H:%M:%S.%f")
    iso_label = now.strftime("%d/%m/%Y %H:%M")

    # Tag di freschezza: serve a preserve_csv_sections() in build_data.py per
    # distinguere sezioni "appena sincronizzate dal CSV" da copie stale lette
    # da un data.json locale non ancora aggiornato dal git pull.
    csv_meta = {
        "reference_date": date_str,
        "synced_at": iso_now,
        "source": "csv_alfredo",
        "semaphore_version": "v2",  # SEMAPHORE_V2: soglie leads/day
    }
    # IMPORTANTE: preserva _meta se è già stato impostato a stale_fallback in main()
    # (caso CSV mancante). Sovrascrive solo quando i payload arrivano dal parse CSV fresh.
    if not (cea_payload.get("_meta") or {}).get("stale"):
        cea_payload["_meta"] = dict(csv_meta)
    if not (medtech_payload.get("_meta") or {}).get("stale"):
        medtech_payload["_meta"] = dict(csv_meta)

    # data.json: aggiorna cea/medtech + overview.projects + generated_at
    data = json.load(open(DATA_JSON))
    data["cea"] = cea_payload
    data["medtech"] = medtech_payload
    _update_overview_projects(data, cea_payload, medtech_payload)
    data["generated_at"] = iso_now
    data["generated_at_label"] = iso_label
    with open(DATA_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # snapshot del giorno: stesso trattamento
    if SNAP_FILE.exists():
        snap = json.load(open(SNAP_FILE))
    else:
        snap = dict(data)
    snap["cea"] = cea_payload
    snap["medtech"] = medtech_payload
    _update_overview_projects(snap, cea_payload, medtech_payload)
    snap["generated_at"] = iso_now
    snap["generated_at_label"] = iso_label
    with open(SNAP_FILE, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=2)

    # Ensure snapshot is in index.json
    idx = json.load(open(INDEX_JSON))
    dates = idx.get("dates", [])
    if date_str not in dates:
        dates.insert(0, date_str)
        # keep last 90
        dates = dates[:90]
    idx["dates"] = sorted(dates, reverse=True)[:90]
    with open(INDEX_JSON, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)

def _load_stale_section(project, requested_date):
    """Carica la sezione `project` (cea|medtech) dallo snapshot più recente prima
    di `requested_date` che ha entries non vuote. Ritorna (payload_dict, source_date)
    oppure (None, None) se non trova niente di utile.

    Marca _meta.stale=True, _meta.stale_from=<source_date>,
    _meta.reference_date=<requested_date>, _meta.synced_at=<now>,
    _meta.source="stale_fallback".

    Introdotto 2026-05-22 per gestire i giorni in cui i CSV di Alfredo non arrivano.
    """
    snaps_dir = SNAP_FILE.parent
    if not snaps_dir.exists():
        return None, None
    # Ordina snapshots/*.json per data discendente, salta requested_date e successivi
    candidates = sorted(snaps_dir.glob("*.json"), reverse=True)
    for snap_path in candidates:
        m = re.match(r"(\d{4}-\d{2}-\d{2})\.json$", snap_path.name)
        if not m:
            continue
        snap_date = m.group(1)
        if snap_date >= requested_date:
            continue  # serve uno snapshot ANTECEDENTE al giorno richiesto
        try:
            snap = json.load(open(snap_path, encoding="utf-8"))
        except Exception:
            continue
        sec = snap.get(project) or {}
        if not sec.get("entries"):
            continue
        # Trovato. Clono e taglio _meta + marker stale.
        payload = json.loads(json.dumps(sec))  # deep copy
        now = datetime.now()
        payload["_meta"] = {
            "reference_date": requested_date,
            "synced_at": now.strftime("%Y-%m-%dT%H:%M:%S.%f"),
            "source": "stale_fallback",
            "stale": True,
            "stale_from": snap_date,
        }
        return payload, snap_date
    return None, None


def main():
    cea_csv  = WORK / f"cea_{DATA_REPORT}.csv"
    mt_csv   = WORK / f"medtech_{DATA_REPORT}.csv"
    cea_present = cea_csv.exists()
    mt_present  = mt_csv.exists()

    history = load_history_csv_snapshots()

    # CEA: fresh se CSV presente, altrimenti stale fallback
    if cea_present:
        cea_items = parse_cea_csv()
        cea_payload = build_cea_payload(cea_items, history, DATA_REPORT)
    else:
        cea_payload, sf = _load_stale_section("cea", DATA_REPORT)
        if cea_payload is None:
            print(f"⚠ CEA: nessun fallback stale disponibile per {DATA_REPORT}")
            cea_payload = {"entries": [], "kpi": {}, "_meta": {
                "reference_date": DATA_REPORT,
                "synced_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f"),
                "source": "stale_fallback_empty",
                "stale": True,
                "stale_from": None,
            }}
        else:
            print(f"⚠ CEA: CSV {DATA_REPORT} mancante → uso fallback STALE da {sf}")

    # MEDTECH: idem
    if mt_present:
        medtech_items = parse_medtech_csv()
        medtech_payload = build_medtech_payload(medtech_items, history, DATA_REPORT)
    else:
        medtech_payload, sf = _load_stale_section("medtech", DATA_REPORT)
        if medtech_payload is None:
            print(f"⚠ MEDTECH: nessun fallback stale disponibile per {DATA_REPORT}")
            medtech_payload = {"entries": [], "kpi": {}, "_meta": {
                "reference_date": DATA_REPORT,
                "synced_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f"),
                "source": "stale_fallback_empty",
                "stale": True,
                "stale_from": None,
            }}
        else:
            print(f"⚠ MEDTECH: CSV {DATA_REPORT} mancante → uso fallback STALE da {sf}")


    # Save preview for inspection
    (WORK / "cea_payload.json").write_text(json.dumps(cea_payload, ensure_ascii=False, indent=2))
    (WORK / "medtech_payload.json").write_text(json.dumps(medtech_payload, ensure_ascii=False, indent=2))

    merge_into_dashboard(cea_payload, medtech_payload, DATA_REPORT)

    # Rigenera data-brief.json (endpoint light, usato da fmm-morning-brief +
    # semaforo-v2-drift-monitor). Senza questa chiamata il brief restava 24h
    # indietro sulle sezioni cea/medtech aggiornate qui dai CSV di Alfredo.
    # Aggiunto 2026-05-24 contestualmente all'esposizione di kpi+_meta v2 nel brief.
    try:
        from brief_builder import write_brief
        data_fresh = json.load(open(DATA_JSON))
        brief_path = write_brief(data_fresh, str(REPO_DASH))
        print(f"BRIEF rigenerato: {brief_path}")
    except Exception as e:
        print(f"⚠ BRIEF non rigenerato (non bloccante): {type(e).__name__}: {e}")

    print("CEA KPI:", json.dumps(cea_payload["kpi"], ensure_ascii=False))
    print("MEDTECH KPI:", json.dumps(medtech_payload["kpi"], ensure_ascii=False))

if __name__ == "__main__":
    main()
