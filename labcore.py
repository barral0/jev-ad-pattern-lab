"""Local evidence store. Never seeds demonstration data."""
import json, sqlite3, hashlib, re
from urllib.parse import urlsplit
from pathlib import Path
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pydantic import BaseModel, ConfigDict, Field

class Ad(BaseModel):
    model_config=ConfigDict(extra='forbid')
    ad_id: str=Field(pattern=r'^[A-Za-z0-9_-]{1,100}$')
    page_id: str
    page_name: str=''
    ad_copy: str=Field(default='',alias='copy')
    active: bool=True
    start_date: str|None=None
    end_date: str|None=None
    thumbnail_url: str|None=None
    media_ids: list[str]=Field(default_factory=list)
    group_ad_ids: list[str]=Field(default_factory=list)
    fingerprint: str=''
    captured_at: str=Field(default_factory=lambda:datetime.now(timezone.utc).isoformat())

def stable_media_key(url):
    """CDN file path only: hosts and signed query strings (oh/oe tokens) change on every capture."""
    if not url: return None
    path=urlsplit(url).path
    return 'file:'+path if path and path!='/' else None

def fingerprint(ad):
    normalized=' '.join(ad.ad_copy.casefold().split())
    # No media identity -> do not assert duplicate identity from copy alone.
    identity=sorted(ad.media_ids) or [stable_media_key(ad.thumbnail_url) or 'unknown:'+ad.ad_id]
    return hashlib.sha256(json.dumps([normalized,identity],ensure_ascii=False).encode()).hexdigest()

class Store:
    def __init__(self,root):
        self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/'lab.sqlite3'
        with self.connect() as c:
            c.executescript('CREATE TABLE IF NOT EXISTS ads(id TEXT PRIMARY KEY,data TEXT NOT NULL); CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT); CREATE TABLE IF NOT EXISTS labels(key TEXT PRIMARY KEY,data TEXT NOT NULL); CREATE TABLE IF NOT EXISTS charges(id TEXT PRIMARY KEY,run TEXT NOT NULL,amount TEXT NOT NULL,status TEXT NOT NULL);')
    @contextmanager
    def connect(self):
        c=sqlite3.connect(self.path,timeout=30)
        try:
            with c: yield c
        finally: c.close()
    def put_ads(self,ads):
        with self.connect() as c:
            for ad in ads:
                ad.fingerprint=fingerprint(ad)
                c.execute('INSERT OR REPLACE INTO ads VALUES(?,?)',(ad.ad_id,json.dumps(ad.model_dump(by_alias=True))))
    def reconcile_inventory(self,page_id,current_ids,complete=False):
        if not complete: return
        current_ids=set(current_ids)
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            for identifier,raw in c.execute('SELECT id,data FROM ads').fetchall():
                row=json.loads(raw)
                if row['page_id']==page_id and identifier not in current_ids:
                    row['active']=False
                    c.execute('UPDATE ads SET data=? WHERE id=?',(json.dumps(row),identifier))
    def ads(self):
        with self.connect() as c: rows=[json.loads(x[0]) for x in c.execute('SELECT data FROM ads ORDER BY id')]
        groups={}
        for row in rows: groups.setdefault(row['fingerprint'],set()).update([row['ad_id']]+row['group_ad_ids'])
        for row in rows: row['group_ad_ids']=sorted(groups[row['fingerprint']])
        return rows
    def set_meta(self,key,value):
        with self.connect() as c: c.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',(key,json.dumps(value)))
    def meta(self,key,default=None):
        with self.connect() as c: row=c.execute('SELECT value FROM meta WHERE key=?',(key,)).fetchone()
        return json.loads(row[0]) if row else default
    def cache_get(self,key):
        with self.connect() as c: row=c.execute('SELECT data FROM labels WHERE key=?',(key,)).fetchone()
        return json.loads(row[0]) if row else None
    def cache_get_many(self,keys):
        """One connection for many labels; missing keys are simply absent from the result."""
        keys=list(dict.fromkeys(keys)); found={}
        with self.connect() as c:
            for i in range(0,len(keys),500):
                chunk=keys[i:i+500]
                for key,data in c.execute('SELECT key,data FROM labels WHERE key IN (%s)'%','.join('?'*len(chunk)),chunk): found[key]=json.loads(data)
        return found
    def cache_put(self,key,value):
        with self.connect() as c: c.execute('INSERT OR REPLACE INTO labels VALUES(?,?)',(key,json.dumps(value)))
