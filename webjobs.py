"""Loopback job orchestration. SQLite history; no shell or secret output."""
import asyncio
import json
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import HTTPException

ROOT=Path(__file__).resolve().parent
ACTIVE=('queued','running')
def now(): return datetime.now(timezone.utc).isoformat()

class Jobs:
    def __init__(self,store,runner=None):
        self.store=store
        self.runner=runner or self.run_cli
        self.tasks=set()
        with store.connect() as c:
            c.execute('CREATE TABLE IF NOT EXISTS web_jobs(id TEXT PRIMARY KEY,status TEXT NOT NULL,data TEXT NOT NULL)')

    def save(self,job):
        with self.store.connect() as c:
            c.execute('UPDATE web_jobs SET status=?,data=? WHERE id=?',(job['status'],json.dumps(job),job['id']))

    def recover(self):
        with self.store.connect() as c:
            for raw, in c.execute("SELECT data FROM web_jobs WHERE status IN ('queued','running')").fetchall():
                job=json.loads(raw); job.update(status='failed',finished_at=now(),error='Servidor interrompido; confira captura e reservas antes de iniciar outra execução.')
                c.execute('UPDATE web_jobs SET status=?,data=? WHERE id=?',(job['status'],json.dumps(job),job['id']))

    def get(self,identifier=None):
        with self.store.connect() as c:
            row=c.execute('SELECT data FROM web_jobs WHERE id=?',(identifier,)).fetchone() if identifier else c.execute('SELECT data FROM web_jobs ORDER BY rowid DESC LIMIT 1').fetchone()
        return json.loads(row[0]) if row else None

    def snapshot(self,identifier=None):
        job=self.get(identifier)
        if job is None: return None
        from inference import cache_key, MODEL
        rows=[r for r in self.store.ads() if r['active'] and r['page_id']==job.get('page_id')]
        capture=self.store.meta('collection',{})
        job['live']={'active_ads':len(rows),'analyzed_ads':sum(bool(self.store.cache_get(cache_key(r,MODEL,True))) for r in rows),'capture_status':capture.get('status') if capture.get('page_id')==job.get('page_id') else None}
        return job

    def submit(self,payload):
        job={'id':uuid.uuid4().hex,**payload,'status':'queued','stage':'queued','created_at':now(),'started_at':None,'finished_at':None,'results':{},'error':None}
        collection=self.store.meta('collection:'+job['page_id'],self.store.meta('collection',{}))
        job['warning']=None
        if job['action']=='analyze' and (collection.get('page_id')!=job['page_id'] or collection.get('status') not in ('complete','complete_zero_ads')):
            job['warning']='Captura incompleta ou não verificada: classificando somente o inventário ativo já salvo desta página.'
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            if c.execute("SELECT 1 FROM web_jobs WHERE status IN ('queued','running') LIMIT 1").fetchone():
                raise HTTPException(409,detail='Já há uma execução ativa. Aguarde sua conclusão.')
            c.execute('INSERT INTO web_jobs VALUES(?,?,?)',(job['id'],job['status'],json.dumps(job)))
        task=asyncio.create_task(self.execute(job.copy()))
        self.tasks.add(task); task.add_done_callback(self.tasks.discard)
        return job

    async def execute(self,job):
        job.update(status='running',started_at=now()); self.save(job)
        try:
            stages=['collect','analyze'] if job['action']=='collect_analyze' else [job['action']]
            for stage in stages:
                job['stage']=stage; self.save(job)
                report=await self.runner(stage,job)
                if not isinstance(report,dict) or not isinstance(report.get('status'),str): raise ValueError('Resultado de etapa inválido')
                job['results'][stage]=report; self.save(job)
                if stage=='collect' and report['status'] not in ('complete','complete_zero_ads'):
                    job.update(status='partial',error='Captura incompleta. Jev não foi iniciado; revise a evidência antes de classificar separadamente.'); break
                if stage=='collect' and report['status']=='complete_zero_ads':
                    job['results']['analyze']={'status':'skipped_empty','calls':0}; break
                if stage=='analyze' and report['status']!='complete':
                    job.update(status='partial',error='Classificação parcial. Confira pendências, custo estimado e reservas antes de repetir.'); break
            else: job['status']='complete'
            if job['status']=='running': job['status']='complete'
        except asyncio.CancelledError:
            job.update(status='failed',error='Servidor interrompido; confira evidências e reservas antes de repetir.')
            raise
        except Exception:
            # Never return exception strings: subprocess/provider output can contain secrets.
            job.update(status='failed',error='Execução falhou. Verifique doctor, chave configurada e evidências locais; não houve repetição automática.')
        finally:
            job['finished_at']=now(); self.save(job)

    async def run_cli(self,stage,job):
        argv=[sys.executable,str(ROOT/'scripts'/'lab.py'),'--data-dir',str(self.store.root.resolve()),stage,'--page-id',job['page_id']]
        if stage=='collect': argv+=['--max-scrolls','100','--timeout','120']
        else: argv+=['--budget',job['budget'],'--run-id','web-'+job['id']]
        process=subprocess.Popen(argv,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,encoding='utf-8',errors='replace',shell=False)
        output=asyncio.create_task(asyncio.to_thread(process.communicate,timeout=420))
        try:
            stdout,_=await asyncio.shield(output)
        except (asyncio.CancelledError,subprocess.TimeoutExpired):
            process.kill()
            try: await output
            except subprocess.TimeoutExpired: await asyncio.to_thread(process.communicate)
            raise
        if process.returncode: raise RuntimeError('Falha na etapa executada pela linha de comando')
        def parse():
            raw=json.loads(stdout)
            # Keep evidence/count/cost identifiers, never untrusted exception/provider text.
            fields={'status','page_id','capture_id','ads','run_id','total_ads','unique_creatives','analyzed_ads','unanalyzed_ads','calls','charged_or_reserved_usd','reported_cost_usd','reserved_unknown_usd','budget_usd','model','images'}
            report={k:v for k,v in raw.items() if k in fields}
            report['error_count']=len(raw.get('errors',[]))
            self.store.set_meta(('collection' if stage=='collect' else 'analysis')+':'+job['page_id'],report)
            return report
        return await asyncio.to_thread(parse)
