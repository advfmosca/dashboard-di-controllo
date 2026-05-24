"""
brief_builder.py — single source of truth per data-brief.json

Endpoint light (~1-2 KB) usato da:
- fmm-morning-brief (08:30) — health emoji + top critici + link deep
- semaforo-v2-drift-monitor (post 09:15) — kpi+_meta v2 di CEA/MedTech

Storia:
- 2026-05-22 (P3): nato per token-saving del Morning Brief (vs data.json ~400 KB)
- 2026-05-24: esteso con `kpi` + `_meta` per cea/medtech, così il drift monitor
  non deve più fare fetch del data.json (che WebFetch tronca a ~88 KB).

CRITICO: il payload DEVE restare ben sotto i 50 KB. Niente entries[], niente
series[], niente rationals HTML. Solo contatori aggregati + meta.

Chiamato da:
- build_data.py (refresh-dashboard-data, 06:34) — dopo aver scritto data.json
- _automation/build_dashboard_payload.py (dashboard-csv-update, 09:15) — dopo
  aver mergiato CEA+MedTech dai CSV di Alfredo.

Senza la chiamata da csv-update, data-brief.json restava 24h indietro su cea/medtech.
"""

import json
import os


# Campi del kpi che vogliamo esporre nel brief — minimal subset per non gonfiare
KPI_FIELDS = (
    "actives", "total", "total_spend", "total_lead",
    "rosso", "giallo", "verde", "nero", "cpl_y",
)

# Campi _meta che esponiamo (utili al drift monitor + ai client che devono
# distinguere fresh / stale / version semaforo)
META_FIELDS = (
    "reference_date", "semaphore_version", "source",
    "stale", "stale_from", "synced_at",
)


def _slim(d, allowed):
    """Filtra il dict tenendo solo le chiavi `allowed` presenti."""
    if not isinstance(d, dict):
        return {}
    return {k: d[k] for k in allowed if k in d}


def _section_summary(section, entries_key):
    """Costruisce il sommario per una sezione (cea|medtech|beefamily) dato
    il nome del campo entries (entries / cards)."""
    section = section or {}
    entries = section.get(entries_key, []) or []
    alerts = sum(
        1 for e in entries
        if (e.get("status") or {}).get("color") in ("red", "yellow")
    )
    summary = {
        f"{entries_key}_count": len(entries),
        "alerts": alerts,
    }
    kpi = _slim(section.get("kpi"), KPI_FIELDS)
    if kpi:
        summary["kpi"] = kpi
    meta = _slim(section.get("_meta"), META_FIELDS)
    if meta:
        summary["_meta"] = meta
    return summary


def build_brief_payload(data):
    """Costruisce il dict del data-brief.json a partire dal data.json completo.
    Non scrive su disco — pura trasformazione."""
    sp_obj = data.get("spending") or {}
    other_obj = data.get("other_roster") or {}

    # _section_summary già produce la chiave corretta (entries_count o cards_count)
    bf_summary  = _section_summary(data.get("beefamily"), "entries")
    ag_summary  = _section_summary(data.get("aghc"),      "cards")
    mt_summary  = _section_summary(data.get("medtech"),   "entries")
    cea_summary = _section_summary(data.get("cea"),       "entries")

    return {
        "reference_date": data.get("reference_date"),
        "reference_date_label": data.get("reference_date_label"),
        "generated_at": data.get("generated_at"),
        "pages_url": data.get("pages_url"),
        "overview": data.get("overview", {}),
        "spending": {
            # top 5 zero — il brief Slack mostra solo top 3, lasciamo margine
            "zero": (sp_obj.get("zero") or [])[:5],
            "zero_count": len(sp_obj.get("zero") or []),
            "high_count": len(sp_obj.get("high") or []),
        },
        "beefamily": bf_summary,
        "aghc": ag_summary,
        "medtech": mt_summary,
        "cea": cea_summary,
        "other_roster": {
            "total_count": other_obj.get("total_count", 0),
            "total_spend_window": other_obj.get("total_spend_window", 0),
        },
    }


def write_brief(data, workspace):
    """Scrive data-brief.json in `workspace`. Restituisce il path scritto."""
    brief = build_brief_payload(data)
    brief_path = os.path.join(workspace, "data-brief.json")
    with open(brief_path, "w", encoding="utf-8") as f:
        json.dump(brief, f, ensure_ascii=False)  # niente indent → footprint minimo
    return brief_path
