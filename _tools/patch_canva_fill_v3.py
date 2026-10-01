#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_canva_fill_v3.py — correzioni v3 (01/10/2026) agli script del report AGHC.
Da lanciare UNA volta nella radice del repo dashboard-di-controllo:
    python3 _tools/patch_canva_fill_v3.py        (oppure: python3 patch_canva_fill_v3.py)
1) build_canva_fill.py: i mesi chiusi precedenti al mese di report vengono dallo storico
   raw/aghc_hist_* (ri-estratto per intero a ogni refresh mensile) e non da aghc_data.json;
   la colonna TikTok viene dallo storico TikTok anche a canale fermo nel mese di report.
build_report.py NON viene toccato (Mare Hotel resta "split": Meta YoY + TikTok MoM).
Idempotente: se la patch è già applicata non fa nulla. Fa una copia .bak del file."""
import os, shutil, sys, ast
ROOT = os.getcwd() if os.path.exists("build_canva_fill.py") else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def rw(name, edits, marker):
    p = os.path.join(ROOT, name); s = open(p, encoding="utf-8").read()
    if marker in s: print(name, ": già aggiornato"); return
    for a, b in edits:
        if s.count(a) != 1: sys.exit("%s: testo atteso non trovato (lo script è cambiato) -> patch NON applicata:\n%s" % (name, a[:80]))
        s = s.replace(a, b)
    ast.parse(s)                      # controllo di sintassi prima di scrivere
    shutil.copy(p, p + ".bak"); open(p, "w", encoding="utf-8").write(s); print(name, ": aggiornato")

A1 = '''    demoM=L("aghc_demographics_monthly.json")'''
B1 = '''    demoM=L("aghc_demographics_monthly.json")
    # --- v3: storico mensile autoritativo per i mesi chiusi (vedi uso più sotto) ---
    from aghc_report_lib import CLIENTS, load_raw, match_client, n as _n
    _cl={c[0]:c for c in CLIENTS}
    _accts=[c[1] for c in CLIENTS]; _shared={x for x in _accts if _accts.count(x)>1}
    _hm=load_raw(W,"aghc_hist_meta_acct.json"); _hc=load_raw(W,"aghc_hist_meta_camp.json"); _ht=load_raw(W,"aghc_hist_tiktok.json")
    def _ymi(v):
        p=re.split(r"[|-]",str(v or ""))
        try: return int(p[0]),int(p[1])-1
        except Exception: return None,None
    def _hist_month(name,year):
        """({indice_mese: spesa Meta}, {indice_mese: spesa TikTok}) del cliente nell'anno.
        Un mese è presente solo se lo storico ha righe per quell'account in quel mese."""
        c=_cl.get(name)
        if not c: return {},{}
        acct,tt=c[1],c[3]; hm={}; ht={}
        if acct in _shared:
            for r in _hc:
                y,i=_ymi(r.get("year_month"))
                if y!=year or str(r.get("account_id"))!=acct: continue
                hm.setdefault(i,0.0)   # l'account ha dati nel mese: 0 se il cliente non ha campagne
                if match_client(r.get("campaign"))==name: hm[i]+=_n(r.get("spend"))
        else:
            for r in _hm:
                y,i=_ymi(r.get("year_month"))
                if y==year and str(r.get("account_id"))==acct: hm[i]=hm.get(i,0.0)+_n(r.get("spend"))
        if tt:
            for r in _ht:
                y,i=_ymi(r.get("year_month"))
                if y==year and str(r.get("account_id"))==tt: ht[i]=ht.get(i,0.0)+_n(r.get("spend"))
        return hm,ht'''
A2 = '''        i0=mm-1
        if 0<=i0<12:'''
B2 = '''        # v3 — MESI CHIUSI PRECEDENTI: valori dallo storico ri-estratto a ogni refresh mensile.
        # aghc_data.json è scritto dal refresh quotidiano e può fermarsi prima di fine mese
        # (agosto 2026 congelato al 29/08: riga Agosto, speso/rimanente e grafico -10%).
        # La colonna TikTok viene dallo storico TikTok anche se has_tt è falso nel mese di
        # report (canale in stand-by): la spesa dei mesi passati NON va accorpata in Meta.
        hmeta,htt=_hist_month(name,int(ym.split("-")[0]))
        for i in range(mm-1):
            if i in hmeta: mmeta[i]=round(hmeta[i],2)
            if i in htt: mtt[i]=round(htt[i],2)
            if i in hmeta or i in htt: mr[i]=round(mmeta[i]+mtt[i],2)
        i0=mm-1
        if 0<=i0<12:'''
rw("build_canva_fill.py", [(A1, B1), (A2, B2)], "_hist_month")
print("Fatto. Rilancia build_canva_fill.py e controlla che META_AGO/TT_AGO coincidano con raw/aghc_hist_*.")
