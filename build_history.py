#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_history.py — aghc_history.json per il LATO TEAM (team.html).
Serie KPI mensili per struttura (Meta account/campagna + TikTok engagements) sugli ultimi
12 mesi chiusi, + un rational mensile ARGOMENTATO (linguaggio semplice, non tecnico) sul mese
di riferimento (ultimo chiuso). Input raw/: aghc_hist_meta_acct.json, aghc_hist_meta_camp.json,
aghc_hist_tiktok.json. Uso: python3 build_history.py --as-of-month 2026-07 --months 12 --workspace .
"""
import argparse, json, os
from datetime import date
MESI=["gennaio","febbraio","marzo","aprile","maggio","giugno","luglio","agosto","settembre","ottobre","novembre","dicembre"]
ABBR=["Gen","Feb","Mar","Apr","Mag","Giu","Lug","Ago","Set","Ott","Nov","Dic"]
STRUCTS=[
 ("Altafiumara Resort","1201395876543423",None,[],None),
 ("Hotel Castello","1489903155429629",None,[],None),
 ("Hotel Della Piana","911357333863123",None,[],"7504967007843319824"),
 ("Hannah Hotels","1528485957725509","hannah",["terraces","puntebianche"],None),
 ("Puntebianche Resort","1528485957725509","puntebianche",[],None),
 ("Hemanaire","217115315497718",None,[],None),
 ("Livata","4666471140299701",None,[],None),
 ("Hotel Lunetta","687349689221880",None,[],"7498330316248203280"),
 ("Magari Estates","1372615496521110",None,[],None),
 ("Marcella Royal Hotel","821188209852436","marcella",[],"7499093699838607377"),
 ("Terrazza Flavia","821188209852436","terrazza",[],None),
 ("Mare Hotel","1432341844596179",None,[],"7498679494010667009"),
 ("Tenuta Montemagno Relais","752450855779035",None,[],None),
 ("Villa Ermellina","30233607946222961",None,[],"7612666695502118929"),
 ("Villa Giada","1849759899186169",None,[],"7626418949391351815"),
 ("Villa Miliani","1353024533007038",None,[],None),
]
def load(ws,p):
    fp=os.path.join(ws,"raw",p)
    if not os.path.exists(fp): return []
    d=json.load(open(fp,encoding="utf-8")); return d.get("result",d) if isinstance(d,dict) else d
def n(x):
    try: return float(x) if x is not None else 0.0
    except: return 0.0
def ym(r): 
    try: return "%s-%02d"%tuple([int(v) for v in str(r.get("year_month","")).split("|")])
    except: return ""
def month_list(as_of,k):
    y,m=[int(x) for x in as_of.split("-")]; out=[]
    for i in range(k-1,-1,-1):
        mm=m-i; yy=y
        while mm<=0: mm+=12; yy-=1
        out.append("%04d-%02d"%(yy,mm))
    return out
def lab(m): y,mm=m.split("-"); return "%s '%s"%(ABBR[int(mm)-1],y[2:])
def fI(v): return ("{:,}".format(int(round(v)))).replace(",",".")
def fE(v): return ("{:,.0f}".format(v)).replace(",",".")+" €"
def dpc(c,p): return round((c-p)/p*100.0) if p else None

def series_meta(acct,camp,acct_id,kw,exc,months):
    idx={m:{"spend":0.0,"reach":0.0,"impr":0.0,"eng":0.0,"clk":0.0} for m in months}
    rows=camp if kw is not None else acct
    for r in rows:
        if str(r.get("account_id"))!=acct_id: continue
        m=ym(r)
        if m not in idx: continue
        if kw is not None:
            c=str(r.get("campaign","")).lower()
            if kw not in c or any(x in c for x in exc): continue
        idx[m]["spend"]+=n(r.get("spend")); idx[m]["reach"]+=n(r.get("reach")); idx[m]["impr"]+=n(r.get("impressions")); idx[m]["eng"]+=n(r.get("actions_page_engagement")); idx[m]["clk"]+=n(r.get("clicks"))
    return {"spend":[round(idx[m]["spend"],2) for m in months],"reach":[int(idx[m]["reach"]) for m in months],"impressions":[int(idx[m]["impr"]) for m in months],"interazioni":[int(idx[m]["eng"]) for m in months],"clicks":[int(idx[m]["clk"]) for m in months]}
def series_tt(tt,rows,months):
    idx={m:{"spend":0.0,"impr":0.0,"clk":0.0} for m in months}
    if tt:
        for r in rows:
            if str(r.get("account_id"))!=tt: continue
            m=ym(r)
            if m not in idx: continue
            idx[m]["spend"]+=n(r.get("spend")); idx[m]["impr"]+=n(r.get("impressions")); idx[m]["clk"]+=n(r.get("engagements"))
    return {"spend":[round(idx[m]["spend"],2) for m in months],"impressions":[int(idx[m]["impr"]) for m in months],"clicks":[int(idx[m]["clk"]) for m in months]}

def trend_word(cur, base):
    if base<=0: return ("stabile",0)
    d=(cur-base)/base*100
    if d>=15: return ("in netta crescita",round(d))
    if d>=5: return ("in crescita",round(d))
    if d<=-15: return ("in sensibile calo",round(d))
    if d<=-5: return ("in calo",round(d))
    return ("stabile",round(d))

def rational(name, meta, tt, combined, i, has_tt, month_label):
    # valori mese rif + prec + baseline 3 mesi prima
    def at(s,k,j): 
        return s[k][j] if (0<=j<len(s[k])) else 0
    sp=combined["spend"][i]; sp_p=combined["spend"][i-1] if i>0 else 0
    reach=meta["reach"][i]; impr=combined["impressions"][i]; inter=meta["interazioni"][i]; clk=combined["clicks"][i]
    base3=lambda k,s: (sum(s[k][max(0,i-3):i])/max(1,len(s[k][max(0,i-3):i])))
    rb=base3("reach",meta); ib=base3("interazioni",meta)
    parts=[]
    # 1 budget
    bd=dpc(sp,sp_p)
    if bd is None: op="A %s l'attività pubblicitaria di %s è stata avviata"%(month_label,name)
    elif bd>=5: op="A %s abbiamo aumentato l'investimento su %s a %s (+%d%% sul mese precedente)"%(month_label,name,fE(sp),bd)
    elif bd<=-5: op="A %s l'investimento su %s è stato ricalibrato a %s (%d%% sul mese precedente)"%(month_label,name,fE(sp),bd)
    else: op="A %s l'investimento su %s è rimasto stabile a %s"%(month_label,name,fE(sp))
    parts.append(op+".")
    # 2 copertura + trend storico
    tw,td=trend_word(reach,rb)
    parts.append("Le campagne hanno raggiunto <b>%s persone</b> (la “copertura”, cioè quante persone diverse hanno visto almeno un contenuto), un dato %s rispetto alla media degli ultimi mesi."%(fI(reach),tw))
    # 3 interazioni
    ew,ed=trend_word(inter,ib)
    parts.append("L'interesse verso i contenuti resta il segnale più importante: <b>%s interazioni</b> (like, commenti, salvataggi, clic sul profilo e sui contenuti), un livello %s."%(fI(inter),ew))
    # 4 click
    parts.append("Il traffico generato verso le destinazioni del brand è di <b>%s clic</b>."%fI(clk))
    # 5 tiktok
    if has_tt and tt["spend"][i]>0:
        parts.append("Su <b>TikTok</b> abbiamo aggiunto <b>%s visualizzazioni</b>, intercettando un pubblico più giovane e complementare a quello di Facebook e Instagram."%fI(tt["impressions"][i]))
    # 6 lettura + contesto + outlook
    if td is not None and td<0:
        parts.append("La flessione della copertura va letta nel contesto di un aumento generale dei costi pubblicitari e di una maggiore concorrenza nel settore ricettivo: a parità di budget si raggiungono un po’ meno persone, ma con un pubblico più mirato. Nel complesso il presidio del brand resta solido e pronto ad accelerare nelle finestre più importanti del piano.")
    else:
        parts.append("Nel complesso il mese conferma una presenza del brand in salute: buona visibilità e interesse costante del pubblico, una base solida su cui costruire i mesi successivi del piano.")
    return " ".join(parts)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--workspace",default="."); ap.add_argument("--as-of-month",required=True); ap.add_argument("--months",type=int,default=12)
    a=ap.parse_args(); ws=a.workspace
    acct=load(ws,"aghc_hist_meta_acct.json"); camp=load(ws,"aghc_hist_meta_camp.json"); tt=load(ws,"aghc_hist_tiktok.json")
    months=month_list(a.as_of_month,a.months); labels=[lab(m) for m in months]; i=len(months)-1
    y,m=a.as_of_month.split("-"); as_of_label="%s %s"%(MESI[int(m)-1].capitalize(),y)
    pm=months[i-1]; py,pmm=pm.split("-"); prev_label="%s %s"%(MESI[int(pmm)-1].capitalize(),py)
    out={"schema_version":1,"generated_at":date.today().isoformat(),"months":months,"month_labels":labels,
         "as_of_month":a.as_of_month,"as_of_label":as_of_label,"prev_label":prev_label,"as_of_idx":i,"structures":[]}
    for name,acct_id,kw,exc,ttid in STRUCTS:
        sm=series_meta(acct,camp,acct_id,kw,exc,months); st=series_tt(ttid,tt,months)
        sc={"spend":[round(sm["spend"][j]+st["spend"][j],2) for j in range(len(months))],
            "impressions":[sm["impressions"][j]+st["impressions"][j] for j in range(len(months))],
            "clicks":[sm["clicks"][j]+st["clicks"][j] for j in range(len(months))]}
        active=sum(sm["spend"])+sum(st["spend"])>0
        if not active: continue
        rat=rational(name,sm,st,sc,i,bool(ttid),as_of_label)
        out["structures"].append({"name":name,"has_tiktok":bool(ttid),"series":{"meta":sm,"tiktok":st,"combined":sc},"rational":rat})
    json.dump(out,open(os.path.join(ws,"aghc_history.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=2)
    print("OK -> aghc_history.json | mesi %s..%s | strutture %d"%(months[0],months[-1],len(out["structures"])))
    for s in out["structures"][:2]: print("  -",s["name"],"| rational:",s["rational"][:110],"...")

if __name__=="__main__": main()
