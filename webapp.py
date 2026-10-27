"""Loopback evidence dashboard with CSRF-protected capture/classification jobs."""
from pathlib import Path
import asyncio, secrets, re
from decimal import Decimal, InvalidOperation
from contextlib import asynccontextmanager
from webjobs import Jobs
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import FileResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from analytics import statistics, landscape, days_active, findings, copy_breakdown
from inference import cache_key, MODEL, LEGACY_RUBRIC_VERSION
from taxonomy import DIMENSIONS, DIMENSION_TITLES, label_pt
from media import safe_thumbnail, fetch_thumbnail, ocr_status

ROOT=Path(__file__).resolve().parent

def create_app(store,job_runner=None):
    jobs=Jobs(store,job_runner)
    csrf_token=secrets.token_urlsafe(32)
    @asynccontextmanager
    async def lifespan(app):
        jobs.recover()
        yield
        for task in list(jobs.tasks): task.cancel()
        if jobs.tasks: await asyncio.gather(*list(jobs.tasks),return_exceptions=True)
    app=FastAPI(title='Jev Ad Pattern Lab',docs_url=None,redoc_url=None,openapi_url=None,lifespan=lifespan)
    @app.get('/api/bootstrap')
    async def bootstrap(): return {'csrf_token':csrf_token}
    @app.post('/api/jobs',status_code=202)
    async def submit_job(request: Request):
        if not secrets.compare_digest(request.headers.get('x-csrf-token','').encode('utf-8'),csrf_token.encode('ascii')): raise HTTPException(403,detail='Token de segurança inválido; recarregue a página.')
        if request.headers.get('content-type','').split(';')[0].strip()!='application/json': raise HTTPException(415,detail='Use application/json.')
        try: payload=await request.json()
        except Exception: raise HTTPException(422,detail='JSON inválido.')
        if not isinstance(payload,dict): raise HTTPException(422,detail='Objeto JSON obrigatório.')
        if set(payload)-{'action','page_id','budget','paid_consent'}: raise HTTPException(422,detail='Campos desconhecidos.')
        action=payload.get('action'); page_id=payload.get('page_id')
        if action not in ('collect','analyze','collect_analyze'): raise HTTPException(422,detail='Ação inválida.')
        if not isinstance(page_id,str) or not re.fullmatch(r'[0-9]{1,30}',page_id): raise HTTPException(422,detail='Page ID deve conter 1 a 30 dígitos ASCII.')
        value=payload.get('budget','0.4999')
        try:
            if type(value) not in (str,int,float): raise ValueError()
            budget=Decimal(str(value))
            if not budget.is_finite() or not Decimal('0')<budget<=Decimal('0.4999'): raise ValueError()
        except (InvalidOperation,ValueError): raise HTTPException(422,detail='Orçamento deve ser maior que zero e no máximo US$ 0,4999.')
        consent=payload.get('paid_consent',False)
        if type(consent) is not bool or (action!='collect' and consent is not True): raise HTTPException(422,detail='Confirme explicitamente a cobrança do Jev.')
        return jobs.submit({'action':action,'page_id':page_id,'budget':str(budget),'paid_consent':consent})
    @app.get('/api/jobs/current')
    def current_job(): return jobs.snapshot()
    @app.get('/api/jobs/{identifier}')
    def get_job(identifier: str):
        job=jobs.snapshot(identifier)
        if job is None: raise HTTPException(404,detail='Execução não encontrada.')
        return job
    @app.middleware('http')
    async def local_only(request,call_next):
        host=request.headers.get('host','')
        allowed={'localhost','127.0.0.1','[::1]','localhost:5194','127.0.0.1:5194','[::1]:5194'}
        if host not in allowed: return JSONResponse({'detail':'Invalid localhost Host'},status_code=400)
        origin=request.headers.get('origin')
        if origin and origin != 'http://'+host: return JSONResponse({'detail':'Cross-origin access blocked'},status_code=403)
        if request.headers.get('sec-fetch-site')=='cross-site': return JSONResponse({'detail':'Cross-site access blocked'},status_code=403)
        response=await call_next(request)
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['Cache-Control']='no-store'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
        return response
    def rows():
        report=store.meta('analysis',{})
        model=report.get('model',MODEL); images=report.get('images',True)
        result=store.ads()
        current=store.cache_get_many([cache_key(r,model,images) for r in result])
        legacy=store.cache_get_many([cache_key(r,model,images,rubric=LEGACY_RUBRIC_VERSION) for r in result])
        for row in result:
            labels=current.get(cache_key(row,model,images))
            if labels is None:
                # Rótulos da rubrica 1.0.0 continuam visíveis, sinalizados, até uma nova classificação autorizada.
                labels=legacy.get(cache_key(row,model,images,rubric=LEGACY_RUBRIC_VERSION))
                if labels is not None: labels={**labels,'legacy':True}
            row['labels']=labels
            row['days_active']=days_active(row)
            row['winner_proxy']=None if row['days_active'] is None else row['days_active']>=60
            row['thumbnail_available']=bool(safe_thumbnail(row.get('thumbnail_url')))
            row['thumbnail_src']='/api/thumbnail/'+row['ad_id'] if row['thumbnail_available'] else None
            # Never hand a remote image URI to the DOM.
            row.pop('thumbnail_url',None)
        return result
    def observed_options(data):
        options={}
        for dimension in DIMENSIONS:
            values={(r.get('labels') or {}).get('answers',{}).get(dimension,{}).get('choice') for r in data}
            values.discard(None)
            options[dimension]=sorted(({'value':v,'label':label_pt(dimension,v)} for v in values),key=lambda o:(o['label'].casefold(),o['value']))
        return options
    def label_coverage(data):
        v2=sum(bool(r['labels']) and not r['labels'].get('legacy') for r in data)
        legacy=sum(bool(r['labels']) and bool(r['labels'].get('legacy')) for r in data)
        return {'v2':v2,'legacy':legacy,'unlabeled':len(data)-v2-legacy,'total':len(data)}
    @app.get('/')
    def index(): return FileResponse(ROOT/'static'/'index.html')
    @app.get('/api/state')
    def state(page_id: str=''):
        everything=rows()
        data=[r for r in everything if r['active'] and (not page_id or r['page_id']==page_id)]
        def scoped_meta(key,default):
            latest=store.meta(key,default)
            if not page_id or latest.get('page_id')==page_id: return latest
            return store.meta(key+':'+page_id,default)
        return {'metrics':statistics(data),'findings':findings(data),'options':observed_options(data),'label_coverage':label_coverage(data),'taxonomy':{'dimensions':list(DIMENSIONS),'titles':DIMENSION_TITLES},'landscape':landscape(data),'collection':scoped_meta('collection',{'status':'not_collected'}),'analysis':scoped_meta('analysis',{'status':'not_analyzed'}),'pages':{r['page_id']:r['page_name'] for r in everything},'ocr':ocr_status()}
    @app.get('/api/ads')
    def ads(request: Request,q: str='',page_id: str='',review: bool=False,winner: bool=False,offset: int=Query(0,ge=0),limit: int=Query(100,ge=1,le=500)):
        wanted={dimension:request.query_params.get(dimension,'') for dimension in DIMENSIONS}
        data=[]
        for row in rows():
            if not row['active'] or (page_id and row['page_id']!=page_id): continue
            if q and q.casefold() not in (row['copy']+' '+row['ad_id']+' '+row['page_name']).casefold(): continue
            labels=row.get('labels') or {}
            if any(value and labels.get('answers',{}).get(key,{}).get('choice')!=value for key,value in wanted.items()): continue
            if review and not labels.get('needs_review',not labels): continue
            if winner and row['winner_proxy'] is not True: continue
            data.append(row)
        return {'ads':data[offset:offset+limit],'total':len(data),'offset':offset,'limit':limit,'has_more':offset+limit<len(data)}
    @app.get('/api/ads/{ad_id}')
    def ad(ad_id: str):
        row=next((r for r in rows() if r['ad_id']==ad_id),None)
        if row is None: raise HTTPException(404)
        answers=(row.get('labels') or {}).get('answers',{})
        row['copy_breakdown']=copy_breakdown(row.get('copy',''))
        row['label_names']={dimension:label_pt(dimension,answer.get('choice')) for dimension,answer in answers.items()}
        row['dimension_titles']={**DIMENSION_TITLES,'audience':'Público citado'}
        if 'audience' in answers: row['label_names']['audience']=(row.get('labels') or {}).get('called_audience') or 'nenhum trecho selecionado'
        return row
    @app.get('/api/thumbnail/{ad_id}')
    async def thumbnail(ad_id: str):
        row=next((r for r in store.ads() if r['ad_id']==ad_id),None)
        if not row: raise HTTPException(404)
        cached=store.root/'thumbnails'/(row['fingerprint']+'.jpg')
        if cached.is_file(): return FileResponse(cached,media_type='image/jpeg')
        if not safe_thumbnail(row.get('thumbnail_url')): raise HTTPException(404)
        try: return Response(await fetch_thumbnail(row['thumbnail_url']),media_type='image/jpeg')
        except Exception: raise HTTPException(404,detail='Miniatura indisponível')
    app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')
    return app
