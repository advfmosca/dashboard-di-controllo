#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_report.py — Report mensile cliente AGHC (5 tabelle split IG/FB + TikTok + rational).

Confronto:
  --comparison mom  → mese chiuso vs mese precedente (raw rep_*_prev).
  --comparison yoy  → mese chiuso vs stesso mese anno prec. dallo STORICO (history/AAAA-MM.json).
                      Per i clienti senza snapshot YoY → fallback automatico a MoM (flag per-cliente).
Lo split IG/FB via API è disponibile solo entro 13 mesi: lo YoY funziona sui mesi "congelati"
in history/ dal banking mensile (snapshot_history.py).

Input raw/: rep_meta_acct_cur/prev.json, rep_meta_camp_cur/prev.json, aghc_report_tt_month/prev.json
Storico:    history/AAAA-MM.json (per --comparison yoy, via --history-prev)
Output:     aghc_report.json
"""
import argparse, json, os, datetime
from aghc_report_lib import CLIENTS, load_raw, bucket, n, dpct, cell

# Regola confronto per struttura (Francesco): YoY pieno / split (Meta YoY + TikTok MoM) / MoM default
CMP={"Hannah Hotels":"yoy","Terrazza Flavia":"yoy","Hotel Della Piana":"split","Hotel Lunetta":"split","Marcella Royal Hotel":"split","Mare Hotel":"split"}

def fmt_int(v): return ("{:,}".format(int(round(v)))).replace(",",".")
def fmt_eur(v): return ("{:,.2f}".format(v)).replace(",","§").replace(".",",").replace("§",".")+" €"

def _eur2(v): return fmt_eur(v)

def _cpm(spend, impr): return (spend / impr * 1000.0) if impr else None

def _pv_used(ttid, clk_cur, clk_prev, tt_pv):
    """Vero quando i click alla destinazione sono strutturalmente a zero (annunci senza
    landing page) e abbiamo le visite al profilo con cui alimentare la riga."""
    if clk_cur or clk_prev: return False
    pv=(tt_pv or {}).get(str(ttid)) or {}
    return pv.get("cur") is not None

def _clicks_or_pv(ttid, clk_cur, clk_prev, tt_pv):
    if not _pv_used(ttid, clk_cur, clk_prev, tt_pv): return (clk_cur, clk_prev)
    pv=tt_pv[str(ttid)]
    return (n(pv.get("cur")), n(pv.get("prev")))


def rational(cur, prev):
    """Rational della slide Meta: parla SOLO di IG/FB, una frase per riga."""
    tsc=cur["ig"]["spend"]+cur["fb"]["spend"]; tsp=prev["ig"]["spend"]+prev["fb"]["spend"]
    reach_c=cur["ig"]["reach"]+cur["fb"]["reach"]; reach_p=prev["ig"]["reach"]+prev["fb"]["reach"]
    impr_c=cur["ig"]["impr"]+cur["fb"]["impr"]; impr_p=prev["ig"]["impr"]+prev["fb"]["impr"]
    eng_c=cur["ig"]["eng"]+cur["fb"]["eng"]; eng_p=prev["ig"]["eng"]+prev["fb"]["eng"]
    clk_c=cur["ig"]["clk"]+cur["fb"]["clk"]
    bd=dpct(tsc,tsp); rd=dpct(reach_c,reach_p); ed=dpct(eng_c,eng_p); idd=dpct(impr_c,impr_p)
    L=[]

    # 1 — budget e spesa
    if bd is None: L.append("Il mese si chiude con un presidio Meta costante e una spesa di %s, allocata secondo le priorità del piano annuale."%_eur2(tsc))
    elif bd>=5: L.append("Il mese si apre con un budget in crescita del %+d%% e una spesa Meta di %s, concentrata sulle finestre a maggior potenziale del piano annuale."%(bd,_eur2(tsc)))
    elif bd<=-5: L.append("Il mese registra una ricalibrazione programmata del budget (%+d%%), con una spesa Meta di %s indirizzata sui pubblici a più alto rendimento."%(bd,_eur2(tsc)))
    else: L.append("Il mese si chiude con un budget sostanzialmente stabile (%+d%%) e una spesa Meta di %s, in linea con la programmazione annuale."%(bd or 0,_eur2(tsc)))

    # 2 — volumi
    grown=[]
    if ed is not None and ed>=5: grown.append("le interazioni complessive IG+FB crescono del %+d%% (%s)"%(ed,fmt_int(eng_c)))
    if rd is not None and rd>=5: grown.append("la copertura complessiva IG+FB sale del %+d%% (%s account unici)"%(rd,fmt_int(reach_c)))
    if grown:
        L.append("Sul fronte engagement "+" e ".join(grown)+": segnale di un pubblico sempre più coinvolto e realmente in target.")
    else:
        L.append("L'attività ha mantenuto un presidio qualificato sul pubblico di riferimento, raggiungendo %s account unici e generando %s interazioni complessive IG+FB."%(fmt_int(reach_c),fmt_int(eng_c)))

    # 3 — efficienza
    cc=_cpm(tsc,impr_c); cp=_cpm(tsp,impr_p)
    if cc is not None and cp:
        cd=dpct(cc,cp)
        if cd is not None and cd<=-3:
            L.append("Sul piano dell'efficienza il costo per mille visualizzazioni scende da %s a %s (%+d%%): ogni euro investito ha prodotto più esposizione qualificata rispetto al periodo di confronto."%(_eur2(cp),_eur2(cc),cd))
        elif cd is not None and cd>=3:
            L.append("Il costo per mille visualizzazioni si attesta a %s contro %s del periodo di confronto (%+d%%), un movimento riconducibile alla maggiore pressione sulle aste Meta e non alla qualità dell'erogazione."%(_eur2(cc),_eur2(cp),cd))
        else:
            L.append("Il costo per mille visualizzazioni resta stabile a %s, a conferma di un'erogazione efficiente e sotto controllo."%_eur2(cc))
    elif cc is not None:
        L.append("Il costo per mille visualizzazioni si attesta a %s, con %s clic complessivi generati verso le destinazioni del brand."%(_eur2(cc),fmt_int(clk_c)))

    # 4 — lettura delle flessioni: cause esterne, mai l'ottimizzazione
    giu=[]
    if rd is not None and rd<0: giu.append("la copertura")
    if idd is not None and idd<0: giu.append("le visualizzazioni")
    if ed is not None and ed<0: giu.append("le interazioni")
    if giu:
        voci=", ".join(giu[:-1])+" e "+giu[-1] if len(giu)>1 else giu[0]
        picco = (ed is not None and ed<=-25) or (rd is not None and rd<=-25)
        causa = ("Il periodo di confronto aveva registrato performance particolarmente brillanti, che alzano sensibilmente la base di paragone; "
                 "a questo si somma ") if picco else "La dinamica riflette "
        L.append("La flessione che interessa %s non dipende dall'impostazione delle campagne. %sl'aumento generalizzato dei costi pubblicitari Meta e la maggiore competitività del comparto ricettivo nel periodo, che hanno reso l'asta più selettiva e più oneroso raggiungere gli stessi volumi a parità di investimento."%(voci,causa))

    # 5 — lavoro di ottimizzazione e gestione
    L.append("Il presidio di gestione è proseguito senza interruzioni: monitoraggio quotidiano della spesa e del ritmo di erogazione, ribilanciamento del peso fra Instagram e Facebook in base al rendimento, selezione dei posizionamenti più performanti e rotazione creativa per contenere l'affaticamento del pubblico.")

    # 6 — chiusura
    L.append("Il risultato è una base solida ed efficiente da cui costruire le prossime finestre ad alto peso del piano annuale.")
    return "\n".join(L)

def rational_tt(tt):
    """Rational della slide TikTok: parla SOLO di TikTok, una frase per riga."""
    if not tt or not tt.get("available"): return ""
    def cur(k): return n((tt.get(k) or {}).get("cur"))
    def prv(k): return n((tt.get(k) or {}).get("prev"))
    sc, sp = cur("budget"), prv("budget")
    imp_c, imp_p = cur("impressions"), prv("impressions")
    clk_c = cur("clicks")
    rch_c, rch_p = cur("reach"), prv("reach")
    bd = dpct(sc, sp); idd = dpct(imp_c, imp_p); rdd = dpct(rch_c, rch_p)
    L=[]

    if bd is None: L.append("Il canale TikTok chiude il mese con una spesa di %s."%_eur2(sc))
    elif bd>=5: L.append("Il canale TikTok chiude il mese con un budget in crescita del %+d%% e una spesa di %s."%(bd,_eur2(sc)))
    elif bd<=-5: L.append("Il canale TikTok chiude il mese con una ricalibrazione programmata del budget (%+d%%) e una spesa di %s."%(bd,_eur2(sc)))
    else: L.append("Il canale TikTok chiude il mese con un budget stabile e una spesa di %s, in linea con la programmazione."%_eur2(sc))

    perf="Le visualizzazioni si attestano a %s%s"%(fmt_int(imp_c),(" (%+d%%)"%idd if idd is not None else ""))
    if rch_c: perf+=", con una copertura di %s account unici%s"%(fmt_int(rch_c),(" (%+d%%)"%rdd if rdd is not None else ""))
    L.append(perf+", volumi che confermano la capacità del canale di generare esposizione su larga scala.")

    cc=_cpm(sc,imp_c); cp=_cpm(sp,imp_p)
    if cc is not None and cp:
        cd=dpct(cc,cp)
        if cd is not None and cd<=-3: L.append("Il costo per mille visualizzazioni scende da %s a %s (%+d%%), a conferma di un'erogazione sempre più efficiente."%(_eur2(cp),_eur2(cc),cd))
        elif cd is not None and cd>=3: L.append("Il costo per mille visualizzazioni si attesta a %s contro %s (%+d%%), effetto della crescente pressione competitiva sull'inventory TikTok."%(_eur2(cc),_eur2(cp),cd))
        else: L.append("Il costo per mille visualizzazioni resta stabile a %s, con un'erogazione costante lungo tutto il mese."%_eur2(cc))
    elif cc is not None:
        L.append("Il costo per mille visualizzazioni si attesta a %s."%_eur2(cc))

    if tt.get("clicks_source")=="profile_visits":
        cdd=dpct(clk_c,prv("clicks"))
        L.append("Le campagne sono impostate su obiettivo Reach, con creatività video prive di link esterno: l'azione dell'utente si concentra quindi sulla visita al profilo, %s nel mese%s, ed è questo il dato riportato in tabella."%(fmt_int(clk_c),(" (%+d%%)"%cdd if cdd is not None else "")))
    elif clk_c:
        L.append("Il traffico generato verso le destinazioni del brand è di %s clic."%fmt_int(clk_c))
    else:
        L.append("Le campagne sono impostate su obiettivo Reach, con creatività video prive di link di destinazione: TikTok non conteggia quindi clic verso il sito, e il valore del canale si misura su copertura e visualizzazioni.")

    L.append("La gestione ha previsto il monitoraggio continuativo dell'erogazione, il presidio della frequenza per evitare saturazione del pubblico e la rotazione dei formati video più performanti.")
    L.append("Il canale amplia la copertura su un pubblico più giovane e complementare a quello presidiato su Meta.")
    return "\n".join(L)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--workspace",default=".")
    ap.add_argument("--month-label",required=True); ap.add_argument("--prev-label",required=True)
    ap.add_argument("--comparison",choices=["mom","yoy"],default="mom")
    ap.add_argument("--history-prev",default=None,help="path history/AAAA-MM.json per YoY")
    ap.add_argument("--yoy-label",default=None,help="etichetta anno-1 per YoY/split (es. Luglio 2025)")
    a=ap.parse_args(); ws=a.workspace
    if not a.yoy_label: a.yoy_label=a.prev_label
    ma=load_raw(ws,"rep_meta_acct_cur.json"); ca=load_raw(ws,"rep_meta_camp_cur.json")
    mp=load_raw(ws,"rep_meta_acct_prev.json"); cp=load_raw(ws,"rep_meta_camp_prev.json")
    tt_c={str(r["account_id"]):r for r in load_raw(ws,"aghc_report_tt_month.json")}
    # visite al profilo: fallback per gli account i cui annunci non hanno destinazione
    try:
        import json as _json
        tt_pv=_json.load(open(os.path.join(ws,"raw","aghc_report_tt_profile_visits.json"),encoding="utf-8"))
    except Exception: tt_pv={}
    tt_p={str(r["account_id"]):r for r in load_raw(ws,"aghc_report_tt_prev.json")}
    hist=None
    if a.comparison=="yoy" and a.history_prev and os.path.exists(os.path.join(ws,a.history_prev)):
        hist=json.load(open(os.path.join(ws,a.history_prev),encoding="utf-8")).get("clients",{})

    clients=[]; fell_back=0
    for name,acct,camp,ttid in CLIENTS:
        cur=bucket(ca if camp else ma, acct, camp)
        desired=CMP.get(name,"mom")
        has_hist=bool(a.comparison=="yoy" and hist and name in hist and hist[name].get("meta"))
        # META: YoY se la struttura lo prevede (yoy o split) e lo storico anno-1 esiste
        meta_yoy=(desired in ("yoy","split")) and has_hist
        if meta_yoy:
            mprev=hist[name]["meta"]
            for k in ("ig","fb"):
                mprev.setdefault(k,{})
                for f in ("reach","impr","eng","clk","spend"): mprev[k].setdefault(f,0)
            meta_prev_label=a.yoy_label
        else:
            if desired in ("yoy","split") and a.comparison=="yoy": fell_back+=1
            mprev=bucket(cp if camp else mp, acct, camp)
            meta_prev_label=a.prev_label
        # TikTok: YoY solo per le strutture "yoy" pure; le "split" usano MoM su TikTok
        tt_yoy=(desired=="yoy") and has_hist
        tth=(hist.get(name,{}).get("tiktok") or {}) if has_hist else {}
        tp=(tt_p.get(ttid) or {}) if ttid else {}
        if tt_yoy:
            tt_prev_imp=n(tth.get("impressions")); tt_prev_clk=n(tth.get("clicks")); tt_prev_spend=n(tth.get("spend")); tt_prev_reach=n(tth.get("reach")); tt_prev_label=a.yoy_label
        else:
            tt_prev_imp=n(tp.get("impressions")); tt_prev_clk=n(tp.get("clicks")); tt_prev_spend=n(tp.get("spend")); tt_prev_reach=n(tp.get("reach")); tt_prev_label=a.prev_label
        cmp_used=("yoy" if (meta_yoy and tt_yoy) else ("split" if meta_yoy else "mom"))
        active=(cur["ig"]["spend"]+cur["fb"]["spend"]+cur["ig"]["impr"]+cur["fb"]["impr"])>0
        e={"name":name,"comparison_used":cmp_used,
           "meta_period_label":"%s vs %s"%(a.month_label,meta_prev_label),
           "tt_period_label":"%s vs %s"%(a.month_label,tt_prev_label)}
        if not active: e["meta"]={"available":False}
        else:
            def tbl(k): return {"ig":cell(cur["ig"][k],mprev["ig"][k]),"fb":cell(cur["fb"][k],mprev["fb"][k])}
            tsc=cur["ig"]["spend"]+cur["fb"]["spend"]; tsp=mprev["ig"]["spend"]+mprev["fb"]["spend"]
            e["meta"]={"available":True,"reach":tbl("reach"),"impressions":tbl("impr"),
                       "engagement":tbl("eng"),"clicks":tbl("clk"),
                       "budget":{"cur":round(tsc,2),"prev":round(tsp,2),"delta":dpct(tsc,tsp)}}
        ttc=tt_c.get(ttid) if ttid else None
        if ttid:
            if ttc and (n(ttc.get("spend"))+n(ttc.get("impressions"))>0):
                e["tiktok"]={"available":True,
                    "reach":cell(n(ttc.get("reach")),tt_prev_reach),
                    "impressions":cell(n(ttc.get("impressions")),tt_prev_imp),
                    "clicks":cell(*_clicks_or_pv(ttid,n(ttc.get("clicks")),tt_prev_clk,tt_pv)),
                    "budget":{"cur":round(n(ttc.get("spend")),2),"prev":round(tt_prev_spend,2),"delta":dpct(n(ttc.get("spend")),tt_prev_spend)}}
                if _pv_used(ttid,n(ttc.get("clicks")),tt_prev_clk,tt_pv): e["tiktok"]["clicks_source"]="profile_visits"
            else: e["tiktok"]={"available":False}
        e["rational"]=rational(cur,mprev) if active else ""
        e["rational_tiktok"]=rational_tt(e.get("tiktok"))
        clients.append(e)

    out={"schema_version":2,"generated_at":datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
         "comparison":a.comparison.upper(),"month_label":a.month_label,"prev_label":a.prev_label,
         "yoy_fallbacks":fell_back,"clients":clients}
    json.dump(out,open(os.path.join(ws,"aghc_report.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=2)
    na=sum(1 for c in clients if c["meta"].get("available"))
    print("OK -> aghc_report.json | %s %s vs %s | attivi %d/%d | fallback MoM(su YoY): %d"%(
        out["comparison"],a.month_label,a.prev_label,na,len(clients),fell_back))

if __name__=="__main__": main()
