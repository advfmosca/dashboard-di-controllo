#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_report.py — Report mensile cliente AGHC (formato a 5 tabelle split Instagram/Facebook).

Confronto MoM (mese chiuso vs precedente) — l'unico automatizzabile con lo split
piattaforma (Meta non restituisce reach con breakdown oltre 13 mesi → YoY split non via API).
Account condivisi separati per campagna (Hannah/Puntebianche, Marcella/Terrazza).

Input (raw/):
  rep_meta_acct_cur.json / rep_meta_acct_prev.json   (account × publisher_platform)
  rep_meta_camp_cur.json / rep_meta_camp_prev.json   (campaign × publisher_platform, account condivisi)
  aghc_report_tt_month.json / aghc_report_tt_prev.json (TikTok mese/precedente)
Output: aghc_report.json
Uso: python3 build_report.py --month-label "Luglio 2026" --prev-label "Giugno 2026" --workspace .
"""
import argparse, json, os

# name, meta_account, campaign_include (substring, opz.), tiktok_account (opz.)
CLIENTS = [
 ("Altafiumara Resort","1201395876543423",None,None),
 ("Hotel Castello","1489903155429629",None,None),
 ("Hotel Della Piana","911357333863123",None,"7504967007843319824"),
 ("Hannah Hotels","1528485957725509","Hannah",None),
 ("Puntebianche Resort","1528485957725509","Puntebianche",None),
 ("Hemanaire","217115315497718",None,None),
 ("Hotel Lunetta","687349689221880",None,"7498330316248203280"),
 ("Magari Estates","1372615496521110",None,None),
 ("Marcella Royal Hotel","821188209852436","Marcella","7499093699838607377"),
 ("Terrazza Flavia","821188209852436","Terrazza",None),
 ("Mare Hotel","1432341844596179",None,"7498679494010667009"),
 ("Tenuta Montemagno Relais","752450855779035",None,None),
 ("Villa Ermellina","30233607946222961",None,"7612666695502118929"),
 ("Villa Giada","1849759899186169",None,"7626418949391351815"),
 ("Villa Miliani","1353024533007038",None,None),
]

def load(ws,p):
    fp=os.path.join(ws,"raw",p)
    if not os.path.exists(fp): return []
    d=json.load(open(fp,encoding="utf-8")); return d.get("result",d) if isinstance(d,dict) else d

def n(x):
    try: return float(x or 0)
    except: return 0.0

def bucket(rows, account, camp):
    """Somma per piattaforma IG/FB filtrando account + (opz.) keyword campagna."""
    agg={"ig":{"reach":0,"impr":0,"eng":0,"clk":0,"spend":0.0},
         "fb":{"reach":0,"impr":0,"eng":0,"clk":0,"spend":0.0}}
    for r in rows:
        if str(r.get("account_id"))!=account: continue
        if camp and camp.lower() not in str(r.get("campaign","")).lower(): continue
        p = "ig" if r.get("publisher_platform")=="instagram" else "fb"
        agg[p]["reach"]+=n(r.get("reach")); agg[p]["impr"]+=n(r.get("impressions"))
        agg[p]["eng"]+=n(r.get("actions_page_engagement")); agg[p]["clk"]+=n(r.get("clicks"))
        agg[p]["spend"]+=n(r.get("spend"))
    return agg

def dpct(c,p): return round((c-p)/p*100.0,0) if p else None
def cell(c,p): return {"cur":int(round(c)),"prev":int(round(p)),"delta":dpct(c,p)}

def fmt_int(v): return ("{:,}".format(int(round(v)))).replace(",",".")
def fmt_eur(v): return ("{:,.2f}".format(v)).replace(",","§").replace(".",",").replace("§",".")+" €"

def rational(name, cur, prev, tt_cur, tt_prev):
    tot_spend_c=cur["ig"]["spend"]+cur["fb"]["spend"]; tot_spend_p=prev["ig"]["spend"]+prev["fb"]["spend"]
    reach_c=cur["ig"]["reach"]+cur["fb"]["reach"]; reach_p=prev["ig"]["reach"]+prev["fb"]["reach"]
    eng_c=cur["ig"]["eng"]+cur["fb"]["eng"]; eng_p=prev["ig"]["eng"]+prev["fb"]["eng"]
    clk_c=cur["ig"]["clk"]+cur["fb"]["clk"]
    bd=dpct(tot_spend_c,tot_spend_p)
    # apertura budget
    if bd is None: op="Il mese si chiude con un presidio Meta costante"
    elif bd>=5: op="Il mese si apre con un budget in crescita (%+d%%)"%bd
    elif bd<=-5: op="Il mese registra una ricalibrazione del budget (%+d%%)"%bd
    else: op="Il mese si chiude con un budget sostanzialmente stabile (%+d%%)"%(bd or 0)
    parts=[op+" e una spesa complessiva di %s."%fmt_eur(tot_spend_c)]
    # crescita
    grown=[]
    ed=dpct(eng_c,eng_p); rd=dpct(reach_c,reach_p)
    if ed is not None and ed>=5: grown.append("le interazioni su Meta crescono del %+d%% (%s)"%(ed,fmt_int(eng_c)))
    if rd is not None and rd>=5: grown.append("la copertura sale del %+d%%"%rd)
    if grown:
        parts.append("Sul fronte engagement "+ " e ".join(grown)+", segnale di un pubblico sempre più coinvolto e in target.")
    else:
        parts.append("L'attività mantiene un presidio qualificato, con un'ampia efficienza per euro investito: con %s l'algoritmo Meta ha generato oltre %s clic verso le destinazioni del brand."%(fmt_eur(tot_spend_c),fmt_int(clk_c)))
    # contestualizza cali
    if (rd is not None and rd<0) or (ed is not None and ed<0):
        parts.append("Le variazioni in flessione si inseriscono in uno scenario di aumento generalizzato dei costi pubblicitari Meta e di crescente competitività nel comparto ricettivo, che ha reso più selettiva l'erogazione sui pubblici a maggior valore.")
    if tt_cur:
        ttd=dpct(tt_cur.get("impressions",0),tt_prev.get("impressions",0) if tt_prev else 0)
        parts.append("Il canale TikTok ha contribuito con %s visualizzazioni%s, ampliando la copertura su un pubblico più giovane e complementare."%(fmt_int(tt_cur.get("impressions",0)), (" (%+d%%)"%ttd if ttd is not None else "")))
    parts.append("Una base solida ed efficiente da cui costruire le prossime finestre ad alto peso del piano annuale.")
    return " ".join(parts)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--workspace",default=".")
    ap.add_argument("--month-label",required=True)
    ap.add_argument("--prev-label",required=True)
    a=ap.parse_args(); ws=a.workspace
    ma=load(ws,"rep_meta_acct_cur.json"); mp=load(ws,"rep_meta_acct_prev.json")
    ca=load(ws,"rep_meta_camp_cur.json"); cp=load(ws,"rep_meta_camp_prev.json")
    tt_c={str(r["account_id"]):r for r in load(ws,"aghc_report_tt_month.json")}
    tt_p={str(r["account_id"]):r for r in load(ws,"aghc_report_tt_prev.json")}

    clients=[]
    for name,acct,camp,ttid in CLIENTS:
        src_c = ca if camp else ma
        src_p = cp if camp else mp
        cur=bucket(src_c,acct,camp); prev=bucket(src_p,acct,camp)
        active = (cur["ig"]["spend"]+cur["fb"]["spend"]+cur["ig"]["impr"]+cur["fb"]["impr"])>0
        entry={"name":name,"channels":camp and "campagna" or "account"}
        if not active:
            entry["meta"]={"available":False}
        else:
            def tbl(k): return {"ig":cell(cur["ig"][k],prev["ig"][k]),"fb":cell(cur["fb"][k],prev["fb"][k])}
            tsc=cur["ig"]["spend"]+cur["fb"]["spend"]; tsp=prev["ig"]["spend"]+prev["fb"]["spend"]
            entry["meta"]={"available":True,
              "reach":tbl("reach"),"impressions":tbl("impr"),"engagement":tbl("eng"),"clicks":tbl("clk"),
              "budget":{"cur":round(tsc,2),"prev":round(tsp,2),"delta":dpct(tsc,tsp)}}
        ttc=tt_c.get(ttid) if ttid else None; ttp=tt_p.get(ttid) if ttid else None
        if ttid:
            act_tt = ttc and (n(ttc.get("spend"))+n(ttc.get("impressions"))>0)
            if act_tt:
                entry["tiktok"]={"available":True,
                  "impressions":cell(n(ttc.get("impressions")),n(ttp.get("impressions")) if ttp else 0),
                  "clicks":cell(n(ttc.get("clicks")),n(ttp.get("clicks")) if ttp else 0),
                  "budget":{"cur":round(n(ttc.get("spend")),2),"prev":round(n(ttp.get("spend")) if ttp else 0,2),
                            "delta":dpct(n(ttc.get("spend")),n(ttp.get("spend")) if ttp else 0)}}
            else:
                entry["tiktok"]={"available":False}
        entry["rational"]= rational(name,cur,prev,
            {"impressions":n(ttc.get("impressions"))} if (ttid and ttc) else None,
            {"impressions":n(ttp.get("impressions"))} if (ttid and ttp) else None) if active else ""
        clients.append(entry)

    out={"schema_version":1,"generated_at":__import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M"),
         "comparison":"MoM","month_label":a.month_label,"prev_label":a.prev_label,"clients":clients}
    json.dump(out,open(os.path.join(ws,"aghc_report.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=2)
    na=sum(1 for c in clients if c["meta"].get("available"))
    print("OK -> aghc_report.json |",a.month_label,"vs",a.prev_label,"| clienti attivi:",na,"/",len(clients))
    for c in clients[:4]:
        if c["meta"].get("available"):
            b=c["meta"]; print("  -",c["name"],"| Copertura IG",b["reach"]["ig"]["cur"],"FB",b["reach"]["fb"]["cur"],"| Budget",b["budget"]["cur"],"€")

if __name__=="__main__": main()
