#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backfill_csv.py — Popola lo storico YoY da CSV Ads Manager (livello campagna, con Piattaforma).
Legge i .csv in --indir, mappa le righe ai clienti per keyword sul nome campagna,
aggrega IG/FB e scrive history/<MESE>.json. Numeri in locale IT (punto=migliaia, virgola=decimali).
Uso: python3 backfill_csv.py --indir csv_2025_07 --month 2025-07 --workspace .
"""
import argparse, csv, glob, io, json, os, re
from aghc_report_lib import KEYWORDS, match_client, empty

def norm(s): return re.sub(r"\s+"," ",(s or "").strip().lower())

H={
 "campaign":["nome della campagna","campagna","campaign name","nome campagna"],
 "platform":["piattaforma","platform","publisher platform"],
 "reach":["copertura","reach"],
 "impr":["impression","impressioni","impressions"],
 "eng":["interazione con la pagina","interazioni con la pagina","page engagement"],
 "clk":["clic (tutti)","clic(tutti)","clic tutti","clicks","clic","link click","clic sul link"],
 "spend":["importo speso (eur)","importo speso","amount spent (eur)","spesa","budget"],
}
def find_col(headers):
    hl={norm(h):h for h in (headers or [])}; m={}
    for k,al in H.items():
        for a in al:
            if a in hl: m[k]=hl[a]; break
    return m

def num(v):
    if v is None: return 0.0
    s=str(v).strip().replace("€","").replace("%","").replace(" ","")
    if s in ("","-","--","n/d","N/D"): return 0.0
    s=s.replace(".","").replace(",",".")
    s=re.sub(r"[^0-9.\-]","",s)
    try: return float(s or 0)
    except: return 0.0

def platform_bucket(p):
    p=norm(p); return "ig" if ("instagram" in p or p=="ig") else "fb"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--indir",required=True); ap.add_argument("--month",required=True); ap.add_argument("--workspace",default=".")
    a=ap.parse_args(); ws=a.workspace
    clients={name:{"ig":empty(),"fb":empty()} for name,_,_ in KEYWORDS}
    unmatched={}; nfiles=0; nrows=0
    for fp in sorted(glob.glob(os.path.join(a.indir,"*.csv"))):
        nfiles+=1; raw=open(fp,encoding="utf-8-sig",errors="replace").read()
        head=raw.split("\n",1)[0]
        delim=";" if head.count(";")>head.count(",") else ","
        rd=csv.DictReader(io.StringIO(raw),delimiter=delim); cols=find_col(rd.fieldnames)
        if "campaign" not in cols or "platform" not in cols:
            print("  ! header non riconosciuti in",os.path.basename(fp),"->",rd.fieldnames); continue
        for r in rd:
            nrows+=1; cli=match_client(r.get(cols["campaign"]))
            if not cli:
                k=(r.get(cols["campaign"]) or "").strip()
                if k: unmatched[k]=unmatched.get(k,0)+1
                continue
            b=clients[cli][platform_bucket(r.get(cols["platform"]))]
            b["reach"]+=num(r.get(cols.get("reach"))); b["impr"]+=num(r.get(cols.get("impr")))
            b["eng"]+=num(r.get(cols.get("eng"))); b["clk"]+=num(r.get(cols.get("clk")))
            b["spend"]+=num(r.get(cols.get("spend")))
    active={n:{"meta":clients[n]} for n in clients if (clients[n]["ig"]["impr"]+clients[n]["fb"]["impr"]+clients[n]["ig"]["spend"]+clients[n]["fb"]["spend"])>0}
    out={"month":a.month,"source":"csv_backfill","clients":active}
    os.makedirs(os.path.join(ws,"history"),exist_ok=True)
    json.dump(out,open(os.path.join(ws,"history",a.month+".json"),"w",encoding="utf-8"),ensure_ascii=False,indent=2)
    print("OK -> history/%s.json | file:%d righe:%d clienti:%d"%(a.month,nfiles,nrows,len(active)))
    if unmatched:
        print("  campagne NON mappate (rivedere KEYWORDS in aghc_report_lib.py):")
        for k,c in sorted(unmatched.items(),key=lambda x:-x[1])[:20]: print("    [%dx] %s"%(c,k))

if __name__=="__main__": main()
