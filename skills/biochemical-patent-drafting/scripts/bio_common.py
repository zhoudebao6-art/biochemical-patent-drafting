"""Small shared primitives. None of these functions attest model review."""
from pathlib import Path
from contextlib import contextmanager
import hashlib, json, os, tempfile, time

SKILL = Path(__file__).resolve().parents[1]
CHECKS = ['source_support', 'antecedents', 'claims_alignment', 'chemistry_data', 'figures', 'rendered_pages']
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def write(path, data):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=p.name+'.',dir=p.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8',newline='\n') as f:
            json.dump(data,f,ensure_ascii=False,indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,p)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
def inside(path, root):
    p=Path(path).resolve(); r=Path(root).resolve()
    if not p.is_relative_to(r): raise ValueError('Path escapes work directory: '+str(p))
    return p
@contextmanager
def lock(path):
    p=Path(path)
    try: fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError: raise ValueError('Controller lock exists; verify owner process before recovery: '+str(p))
    os.write(fd,json.dumps({'pid':os.getpid(),'time':time.time()}).encode()); os.close(fd)
    try: yield
    finally: p.unlink()
