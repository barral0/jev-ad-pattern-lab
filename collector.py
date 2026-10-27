"""Public Ad Library capture. Completeness is evidence, never a scroll count."""
import json, re, asyncio, uuid
from datetime import datetime, timezone
from urllib.parse import urlencode
from labcore import Ad

def source_date(value):
    if value is None: return None
    try:
        if isinstance(value,(float,int)): return datetime.fromtimestamp(value,timezone.utc).date().isoformat()
        return datetime.fromisoformat(str(value).replace('Z','+00:00')).date().isoformat()
    except (ValueError,OverflowError,OSError): return None

def _extract(objects,page_id):
    result={'ads':[],'pagination':[],'pages':{}}
    def walk(obj,inside=False):
        if isinstance(obj,list):
            for value in obj: walk(value,inside)
        elif isinstance(obj,dict):
            relevant=inside or any(k in obj for k in ('ad_library_main','ad_library_main_search','collated_results','ad_archive_id'))
            if 'page_id' in obj and 'page_name' in obj: result['pages'][str(obj['page_id'])]=str(obj['page_name'])
            pi=obj.get('page_info')
            if relevant and isinstance(pi,dict) and type(pi.get('has_next_page')) is bool:
                result['pagination'].append({'has_next_page':pi['has_next_page'],'end_cursor':pi.get('end_cursor')})
            if 'ad_archive_id' in obj and str(obj.get('page_id',''))==page_id and obj.get('is_active') is not False:
                snap=obj.get('snapshot') or {}; body=snap.get('body') or {}
                copy=body.get('text','') if isinstance(body,dict) else str(body)
                images=snap.get('images') or []; videos=snap.get('videos') or []; cards=snap.get('cards') or []
                media=images+videos+cards; thumb=None; ids=[]
                for item in media:
                    for key in ('image_id','video_id','id'):
                        if item.get(key) is not None: ids.append(str(item[key]))
                    if thumb is None:
                        thumb=next((item[k] for k in ('video_preview_image_url','resized_image_url','original_image_url','image_url') if isinstance(item.get(k),str)),None)
                result['ads'].append(Ad(ad_id=str(obj['ad_archive_id']),page_id=page_id,page_name=str(obj.get('page_name') or snap.get('page_name') or ''),copy=copy,start_date=source_date(obj.get('start_date')),end_date=source_date(obj.get('end_date')),thumbnail_url=thumb,media_ids=sorted(set(ids))))
            for key,value in obj.items(): walk(value,relevant)
    for obj in objects: walk(obj)
    result['ads']=list({a.ad_id:a for a in result['ads']}.values())
    return result

def parse_capture(text,page_id):
    """Meta GraphQL responses: anti-JSON prefix followed by newline-delimited JSON."""
    objects=[]
    decoder=json.JSONDecoder(); clean=re.sub(r'^\s*for\s*\(;;\);','',text)
    while clean.strip():
        clean=clean.lstrip()
        try: obj,end=decoder.raw_decode(clean); objects.append(obj); clean=clean[end:]
        except json.JSONDecodeError: break
    return _extract(objects,page_id)

SCRIPT_JSON=re.compile(r'<script\b[^>]*\btype="application/json"[^>]*>(.*?)</script>',re.S|re.I)

def parse_document(html,page_id):
    """The first results page ships inside the HTML document, not in a GraphQL request."""
    objects=[]
    for match in SCRIPT_JSON.finditer(html):
        try: objects.append(json.loads(match.group(1)))
        except json.JSONDecodeError: continue
    return _extract(objects,page_id)

def collection_status(result,challenge=False):
    if challenge: return 'incomplete_challenge'
    if result['pagination'] and result['pagination'][-1]['has_next_page'] is False:
        return 'complete' if result['ads'] else 'complete_zero_ads'
    return 'incomplete_stalled'

async def collect(store,advertiser,page_id=None,max_scrolls=80,timeout=180,headed=False):
    from playwright.async_api import async_playwright
    if page_id is None and advertiser.isdecimal(): page_id=advertiser
    if page_id is not None and not re.fullmatch(r'[0-9]+',page_id): raise ValueError('page_id must contain only ASCII digits')
    params={'active_status':'active','ad_type':'all','country':'ALL','media_type':'all','search_type':'page' if page_id else 'keyword_unordered'}
    if page_id: params['view_all_page_id']=page_id
    else: params['q']=advertiser
    combined={'ads':[],'pagination':[],'pages':{}}; tasks=set(); errors=[]
    capture_id=uuid.uuid4().hex; raw=store.root/'captures'/capture_id; raw.mkdir(parents=True)
    async def response_handler(response):
        is_document=response.request.resource_type=='document' and response.status==200 and '/ads/library' in response.url
        if '/api/graphql' not in response.url and not is_document: return
        try:
            text=await response.text()
            if is_document:
                (raw/(uuid.uuid4().hex+'.html')).write_text(text,encoding='utf-8')
                parsed=parse_document(text,page_id or '')
            else:
                (raw/(uuid.uuid4().hex+'.json')).write_text(text,encoding='utf-8')
                parsed=parse_capture(text,page_id or '')
            combined['pages'].update(parsed['pages'])
            combined['pagination'].extend(parsed['pagination']); combined['ads'].extend(parsed['ads'])
            store.put_ads(parsed['ads'])
            store.set_meta('collection',{'status':'incomplete_collecting','page_id':page_id,'capture_id':capture_id,'ads':len({a.ad_id for a in combined['ads']})})
        except Exception as exc: errors.append(type(exc).__name__)
    challenge=False; reason=None
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=not headed)
        context=await browser.new_context()
        await context.route('**/*',lambda route: route.abort() if route.request.resource_type=='media' or re.search(r'\.(mp4|webm|m3u8)(\?|$)',route.request.url,re.I) else route.continue_())
        page=await context.new_page()
        def listener(resp):
            task=asyncio.create_task(response_handler(resp)); tasks.add(task); task.add_done_callback(tasks.discard)
        page.on('response',listener)
        try:
            await page.goto('https://www.facebook.com/ads/library/?'+urlencode(params),timeout=timeout*1000,wait_until='domcontentloaded')
            deadline=asyncio.get_running_loop().time()+timeout
            for _ in range(max_scrolls):
                await page.wait_for_timeout(1300)
                text=(await page.locator('body').inner_text()).lower()
                challenge=any(x in text for x in ('captcha','confirm you are human','temporarily blocked','log in to continue','confirme que você é humano'))
                if challenge or (combined['pagination'] and not combined['pagination'][-1]['has_next_page']): break
                if asyncio.get_running_loop().time()>deadline: reason='incomplete_timed_out'; break
                await page.evaluate('window.scrollTo(0,document.body.scrollHeight)')
            else: reason='incomplete_scroll_cap'
        except Exception as exc: reason='incomplete_'+type(exc).__name__
        finally:
            if tasks: await asyncio.gather(*list(tasks),return_exceptions=True)
            await browser.close()
    status=collection_status(combined,challenge)
    if status=='incomplete_stalled' and reason: status=reason
    if errors and status.startswith('complete'): status='incomplete_parse_errors'
    if not page_id: status='page_selection_required'
    if page_id: store.reconcile_inventory(page_id,[a.ad_id for a in combined['ads']],complete=status in ('complete','complete_zero_ads'))
    report={'status':status,'page_id':page_id,'capture_id':capture_id,'ads':len({a.ad_id for a in combined['ads']}),'page_candidates':combined['pages'],'errors':errors}
    store.set_meta('collection',report)
    (raw/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (raw/'ads.json').write_text(json.dumps([a.model_dump(by_alias=True) for a in {a.ad_id:a for a in combined['ads']}.values()],indent=2),encoding='utf-8')
    return report
