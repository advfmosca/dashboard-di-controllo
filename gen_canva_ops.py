import json,sys

MIRROR=open('/tmp/mirror_path').read().strip()
C=json.load(open(MIRROR+'/canva_fill.json'))

P1='PBH4N3HJrwWlny79'; P2='PBKmRNKt610GvxXH'; P3='PBMqlyWQvKD6y2xy'; P4='PBbNR6FZLfbx98t7'
P5='PBQT2mkSMQLyd76Y'; P6='PBzhNcPDxkFX0X4g'; P7='PBBX4WzRnLSKHbNN'

def L(p,s): return p+s

M1={'NOME_CLIENTE':'-LBYsT9FtY0ldq3Hz'}
# pagina 2 GBP: nome struttura tokenizzato (dentro il gruppo "Attività Google MyBusiness")
M2={'NOME_CLIENTE':'-LB3KLcgn7RF18rvB-LBrj33dQF0VRLVy2'}
M3={
'MESE_META':'-LBnkhlGqKfMLWbkm',
'REACH_IG_ATT':'-LB0l4tDmsYYgP6JQ','REACH_IG_PRE':'-LBhMFyPFlxqJLTqR','REACH_IG_CFR':'-LBSlqNsT2vsMyKR7',
'REACH_FB_ATT':'-LBy6my99jBgtjcbx','REACH_FB_PRE':'-LBGfmv933w6wfnyx','REACH_FB_CFR':'-LBvxKQ55CPhfdSPT',
'VIEWS_IG_ATT':'-LBLBcPH7KhHVvbCm','VIEWS_IG_PRE':'-LBqSgTbqcQ8q9KcD','VIEWS_IG_CFR':'-LBC7D7MZQxrMVC2z',
'VIEWS_FB_ATT':'-LB5JRvYHZgnLwm4D','VIEWS_FB_PRE':'-LBGRW6m9Bg9jwFSP','VIEWS_FB_CFR':'-LBzws7fcgCQfPZQW',
'INTER_IG_ATT':'-LBMwGYCjvYFMVQMz','INTER_IG_PRE':'-LBHKdM4DW6KhsXfz','INTER_IG_CFR':'-LBg74tbnxtwY70wb',
'INTER_FB_ATT':'-LB9VjdWvhFC9DGwq','INTER_FB_PRE':'-LBVS485cyfvtKxVg','INTER_FB_CFR':'-LBnsxH5ZxZmx41Pv',
'CLICK_IG_ATT':'-LBMqbVqRlPY04YWG','CLICK_IG_PRE':'-LByyjFSzG23PMbYx','CLICK_IG_CFR':'-LBLXRthJ0WPmJWLR',
'CLICK_FB_ATT':'-LBqQCf7Q8wNH8pln','CLICK_FB_PRE':'-LB469vd5SMvFzxJ7','CLICK_FB_CFR':'-LBYjgG5jbHwNmLfh',
'BUDGET_ATT':'-LB33XDLzts1HVTfr','BUDGET_PRE':'-LBs8vJfz0JRv5YDh','BUDGET_CFR':'-LBP2zDcYBj18dT4W',
'FOLL_IG_TOT':'-LB0MyyMThg2gRbZ2','FOLL_IG_DELTA':'-LBGyBZYz1K9B4scv',
'FOLL_FB_TOT':'-LB7xj0zcclTmSp9W','FOLL_FB_DELTA':'-LBHrHLdPQjgnnMGK',
'RATIONAL_META':'-LB9pt3tkt22ztK57'}
M4={'MESE_TT':'-LBL658nKtcCtW2fn',
'TT_REACH_ATT':'-LBYlPxR3X9JFRGHZ','TT_REACH_PRE':'-LB6mlkYP0DT1hVr7','TT_REACH_CFR':'-LB7kB5jlHQyhLn2T',
'TT_VIEWS_ATT':'-LBhvQlTW3C7jn91y','TT_VIEWS_PRE':'-LB0WrLWRhjYLSHXN','TT_VIEWS_CFR':'-LBtnnmQLp9wF7kk1',
'TT_CLICK_ATT':'-LBKPlwDD4gXPCdmg','TT_CLICK_PRE':'-LB59qBlf6m95332t','TT_CLICK_CFR':'-LBFXM0pglvLhWqvG',
'TT_BUDGET_ATT':'-LB43MsYYX71McTqF','TT_BUDGET_PRE':'-LBFJp3sN70xszFDl','TT_BUDGET_CFR':'-LBRY7b29zdrZLVT2',
'FOLL_TT_TOT':'-LB6xXKxRxhy2QbpV','FOLL_TT_DELTA':'-LBV9cd1nsBkS7w8S',
'RATIONAL_TT':'-LBwrlftbjtwj29B7'}
MM=['GEN','FEB','MAR','APR','MAG','GIU','LUG','AGO','SET','OTT','NOV','DIC']
META_IDS='-LBCPsMs8x59GBWhH,-LBFdGnlGC417S4NM,-LBR2wDTvX5gzdvVv,-LBTMfKF6H7TGkWS0,-LBSYzpSjzw26c5xs,-LBGMcPzTcbSqv0C6,-LBYFQSgXd6mx97SV,-LBr75TMNKdLJhqvV,-LB8ybsF8BV0Rh88B,-LB27Ps6h8TX1NxVL,-LBXCRlrl7JZb4n3H,-LB60vBk7Z16BSdtJ'.split(',')
TT_IDS='-LBy7gNzMHF9TJY0J,-LBS2QFKVlLKhSmc6,-LBVWp5c141Lghs7w,-LB8ySj9qZz1wsRyJ,-LBldkPLbmZYSdtjX,-LBl83YqxH7HkcB6b,-LBV7P4NsqlzFkDqL,-LBdKSMMSGwnFmnZt,-LBmLgChwcfh5Qy1L,-LBrDw62K7sfWHy9K,-LBZ9RSLg5Lg7LX4j,-LBfyNTS1BLL4Xd6j'.split(',')
TOT_IDS='-LB1CfKJvRFGfWhBd,-LBV9Hs2BCC90YFV7,-LB3G6vF088pP1CCP,-LBYZJXnLrKf4JpqQ,-LBv5bC4Dl5d9SBMc,-LBW6Ghy4s3KWcjCx,-LBNgsfZWJLKWbhTC,-LBn3w9jQNV1B6ld0,-LBwtqphTfsl06bGW,-LBfQvwRYtlRnX22m,-LB2cptHr9wlfGHjz,-LBw0hWMzqfxLgqQ0'.split(',')
M5={'BUD_ANNUO':'-LBLbp93VjyPZ8NJL','TOT_SPESO':'-LBTwVgyssynrgrzp','TOT_RESIDUO':'-LBw695dhfYpjr2sT'}
for i,m in enumerate(MM):
    M5['META_'+m]=META_IDS[i]; M5['TT_'+m]=TT_IDS[i]; M5['TOT_'+m]=TOT_IDS[i]

CHART_GROUPS=[
 ('LBJ0n9cNhSjXCx3w','LB1VDhfWR1W4b742','LBgrrYxVQz1WL1D0','LBB8CQjdfN0q3NN1','LBbKHbTZkjtfTNr5'),
 ('LBgRDtqM3QJWLGV3','LBCRn9k6mhPrZQDm','LBzr0619xDn5VBNz','LBvRL547mRfKhclG','LBdcHS99JZxFNlch'),
 ('LBrlDDbz7QpH9RJD','LBgxLLvy3M7K2HNx','LB3RFSBQGS50V2tz','LBTbgPW2hRplCKV8','LBMK8vPzRBt8pcnn'),
 ('LBdmlC5zcsRtznnt','LBWDHf7bLJ1K1kWJ','LBPhcs4km4m5SBHj','LBMdVQ3CQ43mvQYm','LBvH6jRbYmFgrxQB'),
 ('LBtWTJwgPS778dSR','LBC8cjzyMhT1t9fR','LBpp15d4r2ZMPWzM','LByHDtYWpXvVFWQ5','LBDbFhdsnBpvrcnR'),
 ('LBDFRmz5mD0CR9JV','LBS5WlYkP5mxQw9j','LBC72f5cJN9Gb74B','LBj0046bGtQh83vr','LBGlXDpxQQsmFCyT'),
 ('LBNm9ST2CvH9hz8b','LBtmZB75TS6qbZ5W','LBX7ymddLpSYPkyw','LBGP0hDNkLd8527K','LBcg0dN71qZgkTtl')]
CHART_SUB='-LB8ZGRcZ4yHW17FM'

AGE_META=[('LB9H3tPqH0c4SGtV','LBpJNztvL7PLDxTm','LBgZ3H7Mh0rq9SK4'),
 ('LBzsg9C83dM0JrN0','LBXl7Nx73gH39LCH','LBhHn4HwyBCHKHpV'),
 ('LBZDSc8Vq8wnClvP','LB0LhvxWFfjKkLs1','LByZX7YVW4cWt5hq'),
 ('LBPcYZ1WyYSPmLDp','LBDSRYFRdvyTvwQC','LB8SthvHqZNm2JML')]
AGE_TT=[('LB8FZpmb0pz87r3y','LB08kgVH20L82hhR','LBKWYYftTHkj0qpL'),
 ('LBJCy0dTJZzMCg2L','LBttNBBCyxvSlSbB','LBDPpnzDbZ3fK5FB'),
 ('LBTk8hRCfVhKJWGQ','LBZMwrYGvd3Jmpn6','LB4nvYZ6pRsppszc')]
GEO_META_BAR='LBZKpl4W6WV6Nxq4,LBMbXYT9PQrqXNG3,LBVTb1T6fS7h69Pb,LBl68syqDjYwpzdV,LBqCkBhP0PZndPrw,LBw2VY7wQp3LDTzG'.split(',')
GEO_META_NAME='LBgydNJqWl6JD0kR,LBH6pCz8jVVXwHwc,LBgrY2MvnvfQKtqt,LBVbMmF00mQywV29,LBHmXHGFRSj8nFbT,LBGdKp8M7gJM0Gxq'.split(',')
GEO_META_PCT='LBR1LtVFHvbnZZC3,LBsSSQd94v0VhCl9,LBG9KSjTjx0TDXC1,LBmY1pwvrb4sRQ5B,LBPwlkYWrXsfDtyZ,LBVdMyQV2rnbXjln'.split(',')
GEO_TT=[('LB5FhqHvx3ckt4yK','LB628KWyr38YCPdc','LB2PQ5PLpTRSpsjL')]
GEO_TOPS=[706,740,774,808,842,876]
GEN_META=('LBm1TnNB4JyW4MdC','LBQGXjHpg951FY3t','LBfZLjfLktVMcZj2','LBjxqsPg0RRp1g0H')
GEN_TT=('LBcK0hXLyfc36cw5','LBML4WM36LDlQXJr','LBKF4rJXYGSNgF4T','LBy6pkFvBlrhTZ16')
TEAL='#006379'; ORANGE='#EE7F4B'; GREEN='#1E9E57'; RED='#D0342C'; NEUTRAL='#262626'
MESI_EST=['Gennaio','Febbraio','Marzo','Aprile','Maggio','Giugno','Luglio','Agosto','Settembre','Ottobre','Novembre','Dicembre']

def eur(v):
    return format(int(round(v)),',').replace(',','.')+" €"
def pctit(p):
    return (format(p,'.1f').replace('.',',')+"%")
def cfr_color(v):
    # "+0%", "-0%" e "n/d" non sono variazioni: vanno neutri, non verdi.
    # Il master eredita i colori del mese di riferimento, quindi il neutro va scritto sempre.
    t=v.replace(' ','')
    if t in ('n/d','+0%','-0%','0%'): return NEUTRAL
    if t.startswith('+'): return GREEN
    if t.startswith('-'): return RED
    return NEUTRAL

def ops_page(cl, page, name):
    t=cl['tokens']; out=[]
    # il nome mostrato può differire dalla chiave interna (es. "Livata" -> "Hotel Livata")
    disp=t.get('NOME_CLIENTE') or name
    if page==1:
        out.append({'type':'replace_text','locator_id':L(P1,M1['NOME_CLIENTE']),'text':disp})
    elif page==2:
        out.append({'type':'replace_text','locator_id':L(P2,M2['NOME_CLIENTE']),'text':disp})
    elif page in (3,4):
        P = P3 if page==3 else P4
        M = M3 if page==3 else M4
        for k,sfx in M.items():
            if k in t: out.append({'type':'replace_text','locator_id':L(P,sfx),'text':t[k]})
        for k,sfx in M.items():
            if k.endswith('_CFR') and k in t:
                c=cfr_color(t[k])
                if c: out.append({'type':'format_text','locator_id':L(P,sfx),'formatting':{'color':c}})
    elif page==5:
        for k,sfx in M5.items():
            if k in t: out.append({'type':'replace_text','locator_id':L(P5,sfx),'text':t[k]})
    return out

def ops_chart(cl, month_idx):
    ch=cl['budget_chart']; labels=ch['labels']; prog=ch['programmato']; spe=ch['speso']
    N=len(labels); BASE=860.0; H=600.0; X0=118.0; PITCH=1600.0/N; BW=58.0
    off=(PITCH-116-4)/2.0
    mx=max(max(prog),max(spe)) or 1
    sc=H/mx
    reuse=[];new=[]
    for i in range(N):
        tl=X0+i*PITCH+off; ol=tl+62
        hp=max(prog[i]*sc,1.0); hs=max(spe[i]*sc,1.0)
        d={'i':i,'tl':tl,'ol':ol,'hp':hp,'hs':hs,'tp':BASE-hp,'ts':BASE-hs,
           'lp':eur(prog[i]),'ls':eur(spe[i]),'m':labels[i]}
        (reuse if i<len(CHART_GROUPS) else new).append(d)
    ops=[]
    for d in reuse:
        g=CHART_GROUPS[d['i']]
        ops.append({'type':'resize_element','locator_id':L(P6,'-'+g[0]),'width':BW,'height':round(d['hp'],1)})
        ops.append({'type':'position_element','locator_id':L(P6,'-'+g[0]),'left':round(d['tl'],1),'top':round(d['tp'],1)})
        ops.append({'type':'resize_element','locator_id':L(P6,'-'+g[1]),'width':BW,'height':round(d['hs'],1)})
        ops.append({'type':'position_element','locator_id':L(P6,'-'+g[1]),'left':round(d['ol'],1),'top':round(d['ts'],1)})
        ops.append({'type':'replace_text','locator_id':L(P6,'-'+g[2]),'text':d['lp']})
        ops.append({'type':'position_element','locator_id':L(P6,'-'+g[2]),'left':round(d['tl']-16,1),'top':round(d['tp']-24,1)})
        ops.append({'type':'replace_text','locator_id':L(P6,'-'+g[3]),'text':d['ls']})
        ops.append({'type':'position_element','locator_id':L(P6,'-'+g[3]),'left':round(d['ol']-16,1),'top':round(d['ts']-24,1)})
        ops.append({'type':'replace_text','locator_id':L(P6,'-'+g[4]),'text':d['m']})
        ops.append({'type':'position_element','locator_id':L(P6,'-'+g[4]),'left':round(d['tl']+10,1),'top':872})
    for i in range(N,len(CHART_GROUPS)):
        for e in CHART_GROUPS[i]:
            ops.append({'type':'delete_element','locator_id':L(P6,'-'+e)})
    newops=[]
    for d in new:
        newops.append({'type':'insert_shape','page_id':P6,'top':round(d['tp'],1),'left':round(d['tl'],1),'width':BW,'height':round(d['hp'],1),'path':'M0 0H58V%dH0z'%round(d['hp']),'view_box_width':58,'view_box_height':round(d['hp']),'color':TEAL})
        newops.append({'type':'insert_shape','page_id':P6,'top':round(d['ts'],1),'left':round(d['ol'],1),'width':BW,'height':round(d['hs'],1),'path':'M0 0H58V%dH0z'%round(d['hs']),'view_box_width':58,'view_box_height':round(d['hs']),'color':ORANGE})
        newops.append({'type':'add_text','page_id':P6,'text':d['lp'],'top':round(d['tp']-24,1),'left':round(d['tl']-16,1),'width':90,'_fmt':{'font_size':14,'font_weight':'bold','color':TEAL,'text_align':'center'}})
        newops.append({'type':'add_text','page_id':P6,'text':d['ls'],'top':round(d['ts']-24,1),'left':round(d['ol']-16,1),'width':90,'_fmt':{'font_size':14,'font_weight':'bold','color':ORANGE,'text_align':'center'}})
        newops.append({'type':'add_text','page_id':P6,'text':d['m'],'top':872,'left':round(d['tl']+10,1),'width':100,'_fmt':{'font_size':18,'font_weight':'bold','color':'#262626','text_align':'center'}})
    sub="Gennaio–%s 2026 · programmato (pesi stagionali) vs speso reale — Meta + TikTok"%(MESI_EST[month_idx-1],)
    ops.append({'type':'replace_text','locator_id':L(P6,CHART_SUB),'text':sub})
    return ops,newops

def ops_demo(cl):
    d=cl.get('demographics')
    if not d: return None,None
    S=10.0/3.0; BASE=500.0
    ops=[]; newops=[]
    ma=(d.get('meta') or {}).get('age') or []
    for i,a in enumerate(ma[:6]):
        x=132+90*i; h=max(a['pct']*S,1.0); top=BASE-h
        if i<len(AGE_META):
            bar,val,lab=AGE_META[i]
            ops.append({'type':'resize_element','locator_id':L(P7,'-'+bar),'width':66,'height':round(h,1)})
            ops.append({'type':'position_element','locator_id':L(P7,'-'+bar),'left':x,'top':round(top,1)})
            ops.append({'type':'replace_text','locator_id':L(P7,'-'+val),'text':pctit(a['pct'])})
            ops.append({'type':'position_element','locator_id':L(P7,'-'+val),'left':x-12,'top':round(top-24,1)})
            ops.append({'type':'replace_text','locator_id':L(P7,'-'+lab),'text':a['label']})
            ops.append({'type':'position_element','locator_id':L(P7,'-'+lab),'left':x-12,'top':506})
        else:
            newops.append({'type':'insert_shape','page_id':P7,'top':round(top,1),'left':x,'width':66,'height':round(h,1),'path':'M0 0H66V%dH0z'%round(h),'view_box_width':66,'view_box_height':round(h),'color':TEAL})
            newops.append({'type':'add_text','page_id':P7,'text':pctit(a['pct']),'top':round(top-24,1),'left':x-12,'width':90,'_fmt':{'font_size':13,'font_weight':'bold','color':TEAL,'text_align':'center'}})
            newops.append({'type':'add_text','page_id':P7,'text':a['label'],'top':506,'left':x-12,'width':90,'_fmt':{'font_size':13,'font_weight':'normal','color':'#262626','text_align':'center'}})
    for i in range(len(ma),4):
        for e in AGE_META[i]: ops.append({'type':'delete_element','locator_id':L(P7,'-'+e)})
    tt=(d.get('tiktok') or {}) if cl.get('has_tiktok') else {}
    ta=(tt.get('age') or [])
    for i,a in enumerate(ta):
        x=1042+90*i; h=max(a['pct']*S,1.0); top=BASE-h
        if i<len(AGE_TT):
            bar,val,lab=AGE_TT[i]
            ops.append({'type':'resize_element','locator_id':L(P7,'-'+bar),'width':66,'height':round(h,1)})
            ops.append({'type':'position_element','locator_id':L(P7,'-'+bar),'left':x,'top':round(top,1)})
            ops.append({'type':'replace_text','locator_id':L(P7,'-'+val),'text':pctit(a['pct'])})
            ops.append({'type':'position_element','locator_id':L(P7,'-'+val),'left':x-12,'top':round(top-24,1)})
            ops.append({'type':'replace_text','locator_id':L(P7,'-'+lab),'text':a['label']})
            ops.append({'type':'position_element','locator_id':L(P7,'-'+lab),'left':x-12,'top':506})
        else:
            newops.append({'type':'insert_shape','page_id':P7,'top':round(top,1),'left':x,'width':66,'height':round(h,1),'path':'M0 0H66V%dH0z'%round(h),'view_box_width':66,'view_box_height':round(h),'color':ORANGE})
            newops.append({'type':'add_text','page_id':P7,'text':pctit(a['pct']),'top':round(top-24,1),'left':x-12,'width':90,'_fmt':{'font_size':13,'font_weight':'bold','color':ORANGE,'text_align':'center'}})
            newops.append({'type':'add_text','page_id':P7,'text':a['label'],'top':506,'left':x-12,'width':90,'_fmt':{'font_size':13,'font_weight':'normal','color':'#262626','text_align':'center'}})
    for i in range(len(ta),len(AGE_TT)):
        for e in AGE_TT[i]: ops.append({'type':'delete_element','locator_id':L(P7,'-'+e)})
    def gender(gl, ids, x0):
        gd={g['label'].lower():g['pct'] for g in gl}
        pd=gd.get('donne'); pu=gd.get('uomini')
        o=[]
        if pd is None or pu is None:
            for e in ids: o.append({'type':'delete_element','locator_id':L(P7,'-'+e)})
            return o
        wd=770.0*pd/100.0; wu=770.0-wd
        o.append({'type':'resize_element','locator_id':L(P7,'-'+ids[0]),'width':round(wd,1),'height':32})
        o.append({'type':'position_element','locator_id':L(P7,'-'+ids[0]),'left':x0,'top':585})
        o.append({'type':'resize_element','locator_id':L(P7,'-'+ids[1]),'width':round(wu,1),'height':32})
        o.append({'type':'position_element','locator_id':L(P7,'-'+ids[1]),'left':round(x0+wd,1),'top':585})
        o.append({'type':'replace_text','locator_id':L(P7,'-'+ids[2]),'text':'Donne '+pctit(pd)})
        o.append({'type':'replace_text','locator_id':L(P7,'-'+ids[3]),'text':'Uomini '+pctit(pu)})
        return o
    ops+=gender((d.get('meta') or {}).get('gender') or [], GEN_META, 110)
    ops+=gender(tt.get('gender') or [], GEN_TT, 1020)
    mg=((d.get('meta') or {}).get('geo') or [])[:6]
    for i,g in enumerate(mg):
        top=GEO_TOPS[i]; w=max(g['pct']*3.0,1.0)
        ops.append({'type':'resize_element','locator_id':L(P7,'-'+GEO_META_BAR[i]),'width':round(w,1),'height':18})
        ops.append({'type':'position_element','locator_id':L(P7,'-'+GEO_META_BAR[i]),'left':270,'top':top})
        ops.append({'type':'replace_text','locator_id':L(P7,'-'+GEO_META_NAME[i]),'text':g['label']})
        ops.append({'type':'position_element','locator_id':L(P7,'-'+GEO_META_NAME[i]),'left':100,'top':top-1})
        ops.append({'type':'replace_text','locator_id':L(P7,'-'+GEO_META_PCT[i]),'text':pctit(g['pct'])})
        ops.append({'type':'position_element','locator_id':L(P7,'-'+GEO_META_PCT[i]),'left':582,'top':top-1})
    for i in range(len(mg),6):
        for e in (GEO_META_BAR[i],GEO_META_NAME[i],GEO_META_PCT[i]):
            ops.append({'type':'delete_element','locator_id':L(P7,'-'+e)})
    tg=(tt.get('geo') or [])[:6]
    for i,g in enumerate(tg):
        top=GEO_TOPS[i]; w=max(g['pct']*3.0,1.0)
        if i<len(GEO_TT):
            bar,nm,pc=GEO_TT[i]
            ops.append({'type':'resize_element','locator_id':L(P7,'-'+bar),'width':round(w,1),'height':18})
            ops.append({'type':'position_element','locator_id':L(P7,'-'+bar),'left':1180,'top':top})
            ops.append({'type':'replace_text','locator_id':L(P7,'-'+nm),'text':g['label']})
            ops.append({'type':'position_element','locator_id':L(P7,'-'+nm),'left':1010,'top':top-1})
            ops.append({'type':'replace_text','locator_id':L(P7,'-'+pc),'text':pctit(g['pct'])})
            ops.append({'type':'position_element','locator_id':L(P7,'-'+pc),'left':1492,'top':top-1})
        else:
            newops.append({'type':'insert_shape','page_id':P7,'top':top,'left':1180,'width':round(w,1),'height':18,'path':'M0 0H%dV18H0z'%round(w),'view_box_width':round(w),'view_box_height':18,'color':ORANGE})
            newops.append({'type':'add_text','page_id':P7,'text':g['label'],'top':top-1,'left':1010,'width':165})
            newops.append({'type':'add_text','page_id':P7,'text':pctit(g['pct']),'top':top-1,'left':1492,'width':70})
    if not tg:
        for bar,nm,pc in GEO_TT:
            for e in (bar,nm,pc): ops.append({'type':'delete_element','locator_id':L(P7,'-'+e)})
    return ops,newops

if __name__=='__main__':
    name=sys.argv[1]; what=sys.argv[2]
    PID=sys.argv[3] if len(sys.argv)>3 else None
    if PID:
        P1=P2=P3=P4=P5=P6=P7=PID
    cl=C['clients'][name]
    mi=int(C['month'].split('-')[1])
    if what in ('1','2','3','4','5'):
        print(json.dumps(ops_page(cl,int(what),name),ensure_ascii=False))
    elif what=='6':
        a,b=ops_chart(cl,mi); print(json.dumps({'reuse':a,'new':b},ensure_ascii=False))
    elif what=='7':
        a,b=ops_demo(cl); print(json.dumps({'ops':a,'new':b},ensure_ascii=False))
    elif what=='info':
        d=cl.get('demographics') or {}
        print(json.dumps({'has_tiktok':cl['has_tiktok'],'demo':bool(d),
          'meta_age':len((d.get('meta') or {}).get('age') or []),
          'tt_age':len((d.get('tiktok') or {}).get('age') or []),
          'meta_geo':len((d.get('meta') or {}).get('geo') or []),
          'tt_geo':len((d.get('tiktok') or {}).get('geo') or []),
          'n_months':len(cl['budget_chart']['labels'])},ensure_ascii=False))
