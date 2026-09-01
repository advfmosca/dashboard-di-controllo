# -*- coding: utf-8 -*-
"""Libreria condivisa report cliente AGHC: anagrafica + bucket IG/FB."""
import json, os

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
 # entrata in gestione ad agosto 2026 (prima erogazione il 17/08): confronto MoM, solo Meta
 ("Livata","4666471140299701",None,None),
]

def load_raw(ws, p):
    fp=os.path.join(ws,"raw",p)
    if not os.path.exists(fp): return []
    d=json.load(open(fp,encoding="utf-8")); return d.get("result",d) if isinstance(d,dict) else d

def n(x):
    try: return float(x or 0)
    except: return 0.0

def empty(): return {"reach":0,"impr":0,"eng":0,"clk":0,"spend":0.0}

def bucket(rows, account, camp):
    agg={"ig":empty(),"fb":empty()}
    for r in rows:
        if str(r.get("account_id"))!=account: continue
        if camp and camp.lower() not in str(r.get("campaign","")).lower(): continue
        p="ig" if r.get("publisher_platform")=="instagram" else "fb"
        agg[p]["reach"]+=n(r.get("reach")); agg[p]["impr"]+=n(r.get("impressions"))
        agg[p]["eng"]+=n(r.get("actions_page_engagement")); agg[p]["clk"]+=n(r.get("clicks"))
        agg[p]["spend"]+=n(r.get("spend"))
    return agg

def dpct(c,p): return round((c-p)/p*100.0,0) if p else None
def cell(c,p): return {"cur":int(round(c)),"prev":int(round(p)),"delta":dpct(c,p)}

# Keyword sul NOME CAMPAGNA per mappare le righe CSV al cliente (backfill storico da CSV Ads Manager).
# exclude: keyword che escludono la riga da quel cliente (disambigua account condivisi).
KEYWORDS = [
 ("Altafiumara Resort",       ["altafiumara"], []),
 ("Hotel Castello",           ["castello"], []),
 ("Hotel Della Piana",        ["della piana","piana"], []),
 ("Hannah Hotels",            ["hannah"], ["terraces","puntebianche"]),
 ("Puntebianche Resort",      ["puntebianche"], []),
 ("Hemanaire",                ["hemanaire"], []),
 ("Hotel Lunetta",            ["lunetta"], []),
 ("Magari Estates",           ["magari"], []),
 ("Marcella Royal Hotel",     ["marcella"], []),
 ("Terrazza Flavia",          ["terrazza"], []),
 ("Mare Hotel",               ["mare"], []),
 ("Tenuta Montemagno Relais", ["montemagno"], []),
 ("Villa Ermellina",          ["ermellina"], []),
 ("Villa Giada",              ["giada"], []),
 ("Villa Miliani",            ["miliani"], []),
 ("Livata",                   ["livata"], []),
]

def match_client(campaign_name):
    c=(campaign_name or "").lower()
    for name,inc,exc in KEYWORDS:
        if any(k in c for k in inc) and not any(x in c for x in exc):
            return name
    return None
