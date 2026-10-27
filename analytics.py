"""Descriptive analysis only: longevity is not revenue, ROI or ad performance."""
from datetime import date
from statistics import median
from collections import Counter
import math, re, hashlib
from taxonomy import DIMENSIONS, NEXT_TESTS, label_pt

def days_active(row,today=None):
    today=today or date.today()
    try:
        start=date.fromisoformat(row.get('start_date') or '')
        end=today if row.get('active',True) else date.fromisoformat(row.get('end_date') or '')
        if start>end or start>today: return None
        return (min(end,today)-start).days
    except (ValueError,TypeError): return None

def statistics(rows,today=None):
    rows=[r for r in rows if r.get('active',True)]
    durations={r['ad_id']:days_active(r,today) for r in rows}
    eligible=[d for d in durations.values() if d is not None]
    result={'total_ads':len(rows),'unique_creatives':len({r['fingerprint'] for r in rows}),'eligible_ads':len(eligible),'unknown_date_ads':len(rows)-len(eligible),'winner_proxy_ads':sum(d>=60 for d in eligible),'median_days':median(eligible) if eligible else None,'winner_definition':'Longevity proxy only: days active >=60. Not spend, profitability, conversion or causal performance.','analyzed_ads':sum(bool(r.get('labels')) for r in rows),'categories':{}}
    for dimension in DIMENSIONS:
        grouped={}
        for row in rows:
            answer=(row.get('labels') or {}).get('answers',{}).get(dimension)
            if answer: grouped.setdefault(answer['choice'],[]).append(row)
        ordered=sorted(grouped,key=lambda k:(-len(grouped[k]),k))
        comparator=ordered[1] if len(ordered)>1 else None
        def rate(category):
            ds=[durations[r['ad_id']] for r in grouped.get(category,[]) if durations[r['ad_id']] is not None]
            return sum(d>=60 for d in ds)/len(ds) if ds else None
        comparison_rate=rate(comparator)
        cards=[]; labeled=sum(map(len,grouped.values()))
        for category in ordered:
            ads=grouped[category]; ds=[durations[r['ad_id']] for r in ads if durations[r['ad_id']] is not None]; own=rate(category)
            cards.append({'category':category,'ad_count':len(ads),'unique_creatives':len({r['fingerprint'] for r in ads}),'share':len(ads)/labeled if labeled else None,'share_denominator':'analyzed ads in this dimension','eligible_ads':len(ds),'unknown_date_ads':len(ads)-len(ds),'median_days':median(ds) if ds else None,'winner_proxy_rate':own,'comparator':comparator,'comparator_rate':comparison_rate,'lift_pp':100*(own-comparison_rate) if own is not None and comparison_rate is not None else None,'relative_lift':(own/comparison_rate)-1 if own is not None and comparison_rate else None,'evidence_ad_ids':[r['ad_id'] for r in sorted(ads,key=lambda r:-(durations[r['ad_id']] if durations[r['ad_id']] is not None else -1))]})
        result['categories'][dimension]=cards
    return result

def landscape(rows):
    """TF-IDF cosine components; deterministic signed hash projection for display."""
    unique={r['fingerprint']:r for r in rows}; keys=sorted(unique)
    tokens={k:Counter(re.findall(r'\w+',unique[k].get('copy','').casefold())) for k in keys}
    document_frequency=Counter(t for counter in tokens.values() for t in counter)
    vectors={}
    for key,counter in tokens.items():
        vector={t:(1+math.log(n))*(1+math.log((1+len(keys))/(1+document_frequency[t]))) for t,n in counter.items()}
        norm=math.sqrt(sum(v*v for v in vector.values())) or 1
        vectors[key]={t:v/norm for t,v in vector.items()}
    components=[]; assigned=set()
    for key in keys:
        if key in assigned: continue
        component=[key]; assigned.add(key); queue=[key]
        while queue:
            current=queue.pop()
            for other in keys:
                if other in assigned: continue
                similarity=sum(v*vectors[other].get(t,0) for t,v in vectors[current].items())
                if similarity>=.65: assigned.add(other); component.append(other); queue.append(other)
        components.append(component)
    points=[]
    for cluster,component in enumerate(components):
        for key in component:
            vector=vectors[key]; x=y=0
            for token,value in vector.items():
                digest=hashlib.sha256(token.encode()).digest()
                x+=value*(int.from_bytes(digest[:4],'big')/4294967295*2-1)
                y+=value*(int.from_bytes(digest[4:8],'big')/4294967295*2-1)
            points.append({'fingerprint':key,'ad_id':unique[key]['ad_id'],'x':x,'y':y,'cluster':cluster,'ad_count':sum(r['fingerprint']==key for r in rows)})
    return {'method':'Similaridade de cosseno TF-IDF entre os textos, agrupada por componentes conectados (limiar 0,65). A projeção 2D é determinística, por hash assinado, e não representa grupos visuais aprendidos.','points':points,'clusters':len(components)}


WINNER_DAYS=60
FINDING_DIMENSIONS=('format','hook','offer')
GENERIC_NEXT_TEST='Teste uma abordagem original com os fatos do seu produto e compare com o seu criativo atual. Este rótulo não tem uma hipótese pronta.'

def _choice(row,dimension):
    answers=((row.get('labels') or {}).get('answers') or {})
    return (answers.get(dimension) or {}).get('choice')

def pattern_examples(rows,dimension,category,older_only=False,today=None):
    """Active labeled ads for one category: oldest first, one per creative family before any repeat."""
    selected=[]
    for row in rows:
        if not row.get('active',True) or _choice(row,dimension)!=category: continue
        days=days_active(row,today)
        if older_only and (days is None or days<WINNER_DAYS): continue
        selected.append((row,days))
    # Undated ads go last; ties are stable by ad id so the order never depends on insertion.
    selected.sort(key=lambda item:(item[1] is None,-(item[1] or 0),str(item[0].get('ad_id'))))
    seen=set(); first=[]; repeats=[]
    for row,_ in selected:
        family=row.get('fingerprint') or row.get('ad_id')
        (repeats if family in seen else first).append(row)
        seen.add(family)
    return first+repeats

def findings(rows,today=None,dimensions=FINDING_DIMENSIONS):
    """Longevity patterns: one highlighted group per dimension, with the evidence behind it.

    The 60+ day share is observational. It is not spend, conversion or profitability.
    Groups smaller than max(5, 2% of dated ads) are never highlighted.
    """
    active=[r for r in rows if r.get('active',True)]
    result=[]
    for dimension in dimensions:
        labeled=[r for r in active if _choice(r,dimension)]
        dated=[(r,days_active(r,today)) for r in labeled]
        dated=[(r,d) for r,d in dated if d is not None]
        if not dated: continue
        baseline=sum(d>=WINNER_DAYS for _,d in dated)/len(dated)
        minimum=max(5,math.ceil(len(dated)*.02))
        groups={}
        for r,d in dated: groups.setdefault(_choice(r,dimension),[]).append((r,d))
        ranked=[]
        for category,items in groups.items():
            if category=='unknown' or len(items)<minimum: continue
            old=sum(d>=WINNER_DAYS for _,d in items)
            ranked.append({'category':category,'dated':len(items),'old':old,'share':old/len(items),'median_days':median([d for _,d in items])})
        if not ranked: continue
        ranked.sort(key=lambda g:(-g['share'],-g['dated'],g['category']))
        top=ranked[0]; category=top['category']
        members=[r for r in labeled if _choice(r,dimension)==category]
        examples=pattern_examples(rows,dimension,category,today=today)
        older=pattern_examples(rows,dimension,category,older_only=True,today=today)
        facets=[]
        for other in [d for d in ('hook','offer') if d!=dimension][:2] if dimension=='format' else ['format','proof']:
            counts=Counter(v for v in (_choice(r,other) for r in older) if v and v!='unknown')
            if counts:
                value,n=sorted(counts.items(),key=lambda kv:(-kv[1],kv[0]))[0]
                facets.append({'dimension':other,'category':value,'label':label_pt(other,value),'n':n,'total':len(older)})
        comparison=sorted((g for g in ranked[1:]),key=lambda g:(-g['dated'],g['category']))
        comparison=({'category':comparison[0]['category'],'label':label_pt(dimension,comparison[0]['category']),'n':comparison[0]['dated'],'share':comparison[0]['share']} if comparison else None)
        label=label_pt(dimension,category)
        result.append({'dimension':dimension,'category':category,'label':label,'n':len(members),
            'creatives':len({r.get('fingerprint') or r.get('ad_id') for r in members}),
            'dated':top['dated'],'old':top['old'],'share':top['share'],'median_days':top['median_days'],
            'baseline':baseline,'minimum_group_size':minimum,'lift':top['share']/baseline if baseline else None,
            'facets':facets,'comparison':comparison,'example_ids':[r['ad_id'] for r in examples[:4]],
            'heading':f'{label} tem a maior fatia de anúncios com 60+ dias',
            'observation':f"{top['old']} de {top['dated']} anúncios ativos com data neste grupo começaram há pelo menos 60 dias. Mediana de idade: {round(top['median_days'])} dias.",
            'next_test':NEXT_TESTS.get(category,GENERIC_NEXT_TEST)})
    return result

_CTA=re.compile(r"(^|\n\s*\n|[.!?]\s+)[^\w]*(?:clique|toque|baixe|baixar|agende|agendar|reserve|cadastre|inscreva|participe|garanta|comece|aproveite|saiba mais|assista|acesse|visite|compre|comprar|chame|envie|comente|click|tap|download|book|register|sign\s?up|join|grab|get started|claim|apply|learn more|watch|visit|shop|buy|message|comment)\b", re.IGNORECASE)

def copy_breakdown(copy,transcript=''):
    """Reading aid over saved words: opening, body and closing call. Not a model annotation."""
    speech=bool((transcript or '').strip())
    text=str(transcript if speech else copy or '').strip()
    source='Transcrição da fala' if speech else 'Texto salvo do anúncio'
    if not text: return {'source':'Sem texto salvo','text':'','sections':[]}
    boundary=re.search(r"[!?](?=\s|$)|\.(?=\s+\S|$)|\n\s*\n",text)
    hook_end=boundary.end() if boundary else len(text)
    cta_start=len(text)
    for match in _CTA.finditer(text):
        start=match.start()+len(match.group(1))
        if start>=hook_end: cta_start=start; break
    parts=[('Abertura',text[:hook_end]),('Corpo',text[hook_end:cta_start]),('Fechamento / chamada',text[cta_start:])]
    return {'source':source,'text':text,'sections':[{'role':r,'text':t.strip()} for r,t in parts if t.strip()]}
