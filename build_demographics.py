#!/usr/bin/env python3
# Genera aghc_demographics.json da pull Windsor demografici (Meta + TikTok).
import json, os, argparse, datetime
MESI=["gennaio","febbraio","marzo","aprile","maggio","giugno","luglio","agosto","settembre","ottobre","novembre","dicembre"]
# account -> [(cliente, keyword nel nome campagna)]. La keyword serve SOLO sugli account
# condivisi: senza filtro i due clienti dello stesso account ricevono lo stesso blocco
# demografico (es. Terrazza Flavia, geo 8 km da Via Flavia, si vedeva Milano/Napoli/Firenze
# di Marcella Royal). Stessa convenzione di aghc_report_lib.CLIENTS.
META_ACCT={"1201395876543423":[("Altafiumara Resort",None)],"1489903155429629":[("Hotel Castello",None)],"911357333863123":[("Hotel Della Piana",None)],"1528485957725509":[("Hannah Hotels","Hannah"),("Puntebianche Resort","Puntebianche")],"217115315497718":[("Hemanaire",None)],"4666471140299701":[("Livata",None)],"687349689221880":[("Hotel Lunetta",None)],"1372615496521110":[("Magari Estates",None)],"821188209852436":[("Marcella Royal Hotel","Marcella"),("Terrazza Flavia","Terrazza")],"1432341844596179":[("Mare Hotel",None)],"752450855779035":[("Tenuta Montemagno Relais",None)],"30233607946222961":[("Villa Ermellina",None)],"1849759899186169":[("Villa Giada",None)],"1353024533007038":[("Villa Miliani",None)]}
TT_ACCT={"7504967007843319824":["Hotel Della Piana"],"7498330316248203280":["Hotel Lunetta"],"7499093699838607377":["Marcella Royal Hotel"],"7498679494010667009":["Mare Hotel"],"7612666695502118929":["Villa Ermellina"],"7626418949391351815":["Villa Giada"]}
ORDER=["Altafiumara Resort","Hotel Castello","Hotel Della Piana","Hannah Hotels","Puntebianche Resort","Hemanaire","Livata","Hotel Lunetta","Magari Estates","Marcella Royal Hotel","Terrazza Flavia","Mare Hotel","Tenuta Montemagno Relais","Villa Ermellina","Villa Giada","Villa Miliani"]
REG_IT={"Piedmont":"Piemonte","Tuscany":"Toscana","Aosta Valley":"Valle d'Aosta","Apulia":"Puglia","Sicily":"Sicilia","Lombardy":"Lombardia","England":"Inghilterra"}
AGE_MAP_TT={"AGE_18_24":"18-24","AGE_25_34":"25-34","AGE_35_44":"35-44","AGE_45_54":"45-54","AGE_55_100":"55+"}
AGE_ORDER=["18-24","25-34","35-44","45-54","55-64","65+","55+"]
UNK={"unknown","Unknown","NONE","None","none",None,""}
def load(p):
    if not os.path.exists(p): return []
    d=json.load(open(p,encoding="utf-8")); return d.get("result",d) if isinstance(d,dict) else d
def by_acct(rows,dim,metric):
    out={}
    for r in rows:
        a=str(r.get("account_id")); out.setdefault(a,[]).append((r.get(dim),float(r.get(metric) or 0),str(r.get("campaign") or "")))
    return out
def sel(store,acct,kw):
    """Righe (label,valore) di un account, filtrate sulla keyword di campagna del cliente.
    Se il pull non porta la colonna campaign (mesi storici) si ricade sull'aggregato."""
    rows=store.get(acct,[])
    if not kw or not any(c for _,_,c in rows): return [(k,v) for k,v,_ in rows]
    return [(k,v) for k,v,c in rows if kw.lower() in c.lower()]
def pct_list(pairs,label_map=None,drop_unknown=True,top=None,sort=False):
    agg={}
    for k,v in pairs:
        if drop_unknown and (k in UNK): continue
        lbl=label_map.get(k,k) if label_map else k
        agg[lbl]=agg.get(lbl,0)+v
    items=[[l,v] for l,v in agg.items()]
    if sort: items.sort(key=lambda x:-x[1])
    if top: items=items[:top]
    tot=sum(v for _,v in items) or 1
    return [{"label":l,"value":round(v),"pct":round(v/tot*100,1)} for l,v in items]
def age_sorted(pairs,label_map=None):
    lst=pct_list(pairs,label_map); lst.sort(key=lambda x: AGE_ORDER.index(x["label"]) if x["label"] in AGE_ORDER else 99); return lst
def gender_norm(pairs):
    return pct_list(pairs,{"female":"Donne","male":"Uomini","FEMALE":"Donne","MALE":"Uomini"})
def drop_noise(lst):
    """Scarta le righe che arrotondano a 0,0% (uno-due utenti): su slide cliente
    "Abruzzo 0,0%" sembra un errore. Se resterebbe vuota, si tiene la lista originale."""
    keep=[x for x in lst if x["pct"]>=0.1]
    return keep or lst
def region_it(pairs):
    return drop_noise(pct_list([(REG_IT.get(k,k),v) for k,v in pairs],None,True,6,True))
def country_it(pairs):
    m={"Italy":"Italia","France":"Francia","Germany":"Germania","United Kingdom":"Regno Unito","United States":"USA","Canada":"Canada","Spain":"Spagna","Switzerland":"Svizzera","Austria":"Austria","Belgium":"Belgio","Netherlands":"Paesi Bassi","Poland":"Polonia","Portugal":"Portogallo","Ireland":"Irlanda","Qatar":"Qatar","United Arab Emirates":"Emirati Arabi","Denmark":"Danimarca","Finland":"Finlandia","Norway":"Norvegia"}
    return drop_noise(pct_list([(m.get(k,k),v) for k,v in pairs],None,True,6,True))
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--workspace",default="."); ap.add_argument("--month",default="2026-07")
    a=ap.parse_args(); W=a.workspace; R=lambda n: load(os.path.join(W,"raw",n))
    ma=by_acct(R("aghc_demo_meta_age.json"),"age","reach"); mg=by_acct(R("aghc_demo_meta_gender.json"),"gender","reach"); mr=by_acct(R("aghc_demo_meta_region.json"),"region","reach")
    ta=by_acct(R("aghc_demo_tt_age.json"),"age","impressions"); tg=by_acct(R("aghc_demo_tt_gender.json"),"gender","impressions"); tc=by_acct(R("aghc_demo_tt_country.json"),"country","impressions")
    s2meta={}; s2tt={}
    for acct,entries in META_ACCT.items():
        for n,kw in entries: s2meta[n]=(acct,kw)
    for acct,names in TT_ACCT.items():
        for n in names: s2tt[n]=(acct,None)
    month=a.month; y,m=month.split("-"); structs=[]
    for name in ORDER:
        e={"name":name,"meta":None,"tiktok":None}; macc,mkw=s2meta.get(name,(None,None))
        if macc and (macc in ma or macc in mg or macc in mr):
            e["meta"]={"age":age_sorted(sel(ma,macc,mkw)),"gender":gender_norm(sel(mg,macc,mkw)),"geo":region_it(sel(mr,macc,mkw))}
        tacc,tkw=s2tt.get(name,(None,None))
        if tacc and (tacc in ta or tacc in tg or tacc in tc):
            e["tiktok"]={"age":age_sorted(sel(ta,tacc,tkw),AGE_MAP_TT),"gender":gender_norm(sel(tg,tacc,tkw)),"geo":country_it(sel(tc,tacc,tkw))}
        if e["meta"] or e["tiktok"]: structs.append(e)
    out={"schema_version":1,"generated_at":datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),"as_of_month":month,"as_of_label":"%s %s"%(MESI[int(m)-1].capitalize(),y),"structures":structs}
    json.dump(out,open(os.path.join(W,"aghc_demographics.json"),"w"),ensure_ascii=False,indent=0)
    print("strutture con demo:",len(structs))
    mare=[s for s in structs if s["name"]=="Mare Hotel"][0]
    print("Mare meta age:",[(x["label"],x["pct"]) for x in mare["meta"]["age"]])
    print("Mare meta gender:",[(x["label"],x["pct"]) for x in mare["meta"]["gender"]])
    print("Mare meta geo:",[(x["label"],x["pct"]) for x in mare["meta"]["geo"]])
    print("Mare tt age:",[(x["label"],x["pct"]) for x in mare["tiktok"]["age"]])
    print("Mare tt geo:",[(x["label"],x["pct"]) for x in mare["tiktok"]["geo"]])
if __name__=="__main__": main()
