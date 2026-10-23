"""Loopback-only evaluation control plane for the development dashboard."""
import json
import os
import re
import subprocess
import threading
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'evals/results'
SUITES = {
    'deterministic': dict(name='Core regression', datasets=['classification','normalization','workflow'], paid=False),
    'calibration': dict(name='Judge calibration', datasets=['judge_calibration'], paid=True),
    'language': dict(name='Explanations & chat', datasets=['explanations','chat'], paid=True),
    'extraction': dict(name='Report extraction', datasets=['extraction'], paid=True),
}
LOCK = threading.Lock()
ACTIVE = {}


def reports():
    found=[]
    for path in RESULTS.glob('*.json'):
        try:
            report=json.loads(path.read_text())
            if not isinstance(report.get('items'),list) or not report.get('run_id'): continue
            found.append(dict(id=path.stem,updated=path.stat().st_mtime,report=report))
        except (ValueError,OSError,AttributeError): continue
    return sorted(found,key=lambda r:r['updated'],reverse=True)


def launch(payload):
    suite=payload.get('suite')
    if suite not in SUITES: raise ValueError('Choose a supported suite.')
    spec=SUITES[suite]
    model=payload.get('model','qwen/qwen3-30b-a3b-instruct-2507')
    if not isinstance(model,str) or not re.fullmatch(r'[\w./:\-]{1,160}',model):
        raise ValueError('Enter a valid OpenRouter model ID.')
    if spec['paid'] and payload.get('allow_paid') is not True:
        raise ValueError('Model-backed runs require explicit selection of the paid run button.')
    limit=payload.get('limit')
    if limit is not None and (type(limit) is not int or not 1 <= limit <= 100):
        raise ValueError('Limit must be between 1 and 100.')
    with LOCK:
        if ACTIVE.get('process') and ACTIVE['process'].poll() is None:
            raise ValueError('An evaluation is already running. Wait for it to finish.')
        id='studio-'+uuid.uuid4().hex
        RESULTS.mkdir(parents=True,exist_ok=True)
        command=[str(ROOT/'evals/.venv/bin/python'),str(ROOT/'evals/run.py'),
                 '--datasets',*spec['datasets'],'--output',str(RESULTS/f'{id}.json')]
        if suite in ('calibration','language'): command.append('--judge')
        if limit is not None: command.extend(['--limit',str(limit)])
        process=subprocess.Popen(command,cwd=ROOT,env={**os.environ,'EVAL_JUDGE_MODEL':model},
                                 stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        ACTIVE.clear()
        ACTIVE.update(id=id,suite=suite,started=datetime.now(timezone.utc).isoformat(),process=process)
    return id


def active():
    with LOCK:
        if not ACTIVE: return None
        code=ACTIVE['process'].poll()
        return {**{k:v for k,v in ACTIVE.items() if k!='process'},
                'running':code is None,'exit_code':code}


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass

    def send(self,status,data):
        raw=json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json')
        self.send_header('Cache-Control','no-store')
        self.end_headers(); self.wfile.write(raw)

    def local(self):
        host=self.headers.get('Host','').split(':')[0]
        origin=self.headers.get('Origin')
        return host in ('localhost','127.0.0.1') and (origin is None or origin in (
            'http://localhost:5173','http://127.0.0.1:5173',
            'http://localhost:8766','http://127.0.0.1:8766'))

    def do_GET(self):
        if not self.local(): return self.send(403,{'error':'Local access only.'})
        if self.path=='/eval-api/state':
            manifest=json.loads((ROOT/'evals/golden/v2/manifest.json').read_text())
            return self.send(200,dict(suites=SUITES,counts=manifest['counts'],runs=reports(),active=active()))
        if self.path=='/eval-api/golden':
            cases={}
            for path in (ROOT/'evals/golden/v2').glob('*.jsonl'):
                for line in path.read_text().splitlines():
                    i=json.loads(line); cases[path.stem+'/'+i['id']]=i
            return self.send(200,cases)
        self.send(404,{'error':'Not found.'})

    def do_POST(self):
        if not self.local(): return self.send(403,{'error':'Local access only.'})
        if self.path!='/eval-api/run': return self.send(404,{'error':'Not found.'})
        if self.headers.get('Content-Type')!='application/json': return self.send(415,{'error':'JSON required.'})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0 < size <= 4096: raise ValueError('Invalid request size.')
            data=json.loads(self.rfile.read(size))
            if not isinstance(data,dict): raise ValueError('Expected an object.')
            self.send(202,{'id':launch(data)})
        except (ValueError,TypeError) as exc: self.send(400,{'error':str(exc)})
        except OSError: self.send(503,{'error':'Could not start the runner. Check evals/.venv.'})


if __name__=='__main__':
    print('Evaluation control plane: http://127.0.0.1:8766',flush=True)
    ThreadingHTTPServer(('127.0.0.1',8766),Handler).serve_forever()
