#!/usr/bin/env python
"""Jev Ad Pattern Lab local CLI. .env secrets are never printed."""
import sys, os, json, argparse, asyncio, importlib.util, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def load_env(path):
    """Only this application's key; externally set environment wins."""
    if not path.is_file(): return
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        key,sep,value=line.partition('=')
        if sep and key.strip()=='TYPESAFE_API_KEY':
            value=value.strip()
            if len(value)>=2 and value[0]==value[-1] and value[0] in ('\"',"'"): value=value[1:-1]
            os.environ.setdefault('TYPESAFE_API_KEY',value)

def settings():
    data=json.loads((ROOT/'settings.json').read_text(encoding='utf-8'))
    if data['endpoint']!='https://api.typesafe.ai/v1/systemone' or data['input_usd_per_million']!='0.042' or data['output_usd_per_million']!='0.0' or data['reserve_max_input_tokens']!=65536: raise ValueError('Settings disagree with audited native endpoint/pricing/safety limits')
    return data

def doctor(store):
    from media import ocr_status
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p: browser=Path(p.chromium.executable_path)
    return {'python':sys.version.split()[0],'data_dir':str(store.root),'sqlite':'ready','api_key':'configured' if os.environ.get('TYPESAFE_API_KEY') else 'missing','api_key_source':'environment or project .env; never returned','ocr':ocr_status(),'chromium':'installed' if browser.is_file() else 'missing: run .venv/Scripts/python.exe -m playwright install chromium','chromium_path':str(browser),'packages':{name:bool(importlib.util.find_spec(name)) for name in ['fastapi','uvicorn','httpx','pydantic','PIL','playwright','pytesseract']},'settings':settings(),'collection':store.meta('collection',{'status':'not_collected'}),'analysis':store.meta('analysis',{'status':'not_analyzed'})}

def main(argv=None):
    parser=argparse.ArgumentParser(description='Collect public active Meta ads, classify via native Jev, inspect local evidence. Never seeds examples.')
    parser.add_argument('--data-dir',type=Path,default=ROOT/'data',help='SQLite/raw evidence directory (default: project/data)')
    commands=parser.add_subparsers(dest='command',required=True)
    commands.add_parser('doctor',help='Local prerequisite and key-presence checks; no paid calls')
    capture=commands.add_parser('collect',help='Public active-only Playwright GraphQL capture')
    capture.add_argument('advertiser',nargs='?',default='',help='Advertiser name for page discovery, or exact numeric page ID')
    capture.add_argument('--page-id',help='Exact numeric page ID, required after ambiguous name search')
    capture.add_argument('--max-scrolls',type=int,default=80)
    capture.add_argument('--timeout',type=int,default=180)
    capture.add_argument('--headed',action='store_true')
    classify=commands.add_parser('analyze',help='Native TypeSafe Choice, batched and cached; bounded cost')
    classify.add_argument('--page-id',help='Analyze only this exact numeric page ID')
    classify.add_argument('--budget',default=None,help='USD cap >0 and <=0.4999')
    classify.add_argument('--model',choices=['jev-1.14.0','jev-latest'],default=None)
    classify.add_argument('--batch-size',type=int,default=None)
    classify.add_argument('--concurrency',type=int,default=None)
    classify.add_argument('--no-images',action='store_true',help='Copy-only; labels explicitly flagged for visual review')
    classify.add_argument('--run-id',help='Resume an existing run budget ledger; use same ID across processes')
    server=commands.add_parser('serve',help='Dashboard and protected jobs at http://localhost:5194 (fixed loopback binding)')
    importer=commands.add_parser('import-json',help='Import normalized captured ads, never assumes completeness')
    importer.add_argument('path',type=Path)
    importer.add_argument('--page-id',required=True,help='Reject cross-page rows, numeric exact ID')
    args=parser.parse_args(argv)
    load_env(ROOT/'.env')
    from labcore import Store, Ad
    store=Store(args.data_dir.resolve())
    cfg=settings()
    try:
        if args.command=='doctor': report=doctor(store)
        elif args.command=='collect':
            from collector import collect
            if not args.advertiser and not args.page_id: parser.error('Provide advertiser name or --page-id')
            if args.max_scrolls<1 or args.timeout<1: parser.error('Positive max-scrolls and timeout required')
            report=asyncio.run(collect(store,args.advertiser,args.page_id,args.max_scrolls,args.timeout,args.headed))
        elif args.command=='analyze':
            from inference import analyze
            report=asyncio.run(analyze(store,model=args.model or cfg['model'],budget=args.budget or cfg['budget_usd'],batch_size=args.batch_size or cfg['batch_size'],concurrency=args.concurrency or cfg['concurrency'],images=not args.no_images,run_id=args.run_id,page_id=args.page_id))
        elif args.command=='serve':
            import uvicorn
            from webapp import create_app
            uvicorn.run(create_app(store),host='127.0.0.1',port=5194,access_log=False)
            return 0
        else:
            import re
            if not re.fullmatch(r'[0-9]+',args.page_id): raise ValueError('Exact numeric page ID required')
            raw=json.loads(args.path.read_text(encoding='utf-8-sig'))
            rows=raw.get('ads') if isinstance(raw,dict) else raw
            if not isinstance(rows,list): raise ValueError('Expected JSON array or {ads: [...]}')
            ads=[Ad.model_validate(row) for row in rows]
            if any(ad.page_id!=args.page_id or not ad.active for ad in ads): raise ValueError('Import must contain active ads from exact requested page only')
            store.put_ads(ads)
            report={'status':'imported_completeness_unverified','imported_ads':len({a.ad_id for a in ads}),'page_id':args.page_id,'source':str(args.path.resolve())}
            store.set_meta('collection',report)
            destination=store.root/'imports'; destination.mkdir(exist_ok=True)
            import uuid
            (destination/(uuid.uuid4().hex+'.json')).write_text(json.dumps(raw,indent=2),encoding='utf-8')
        print(json.dumps(report,indent=2,ensure_ascii=True))
        return 0
    except Exception as exc:
        # Do not include request headers, environment or provider body in console errors.
        print(json.dumps({'status':'error','error':type(exc).__name__,'message':str(exc)[:350]},ensure_ascii=True),file=sys.stderr)
        return 1

if __name__=='__main__': raise SystemExit(main())
