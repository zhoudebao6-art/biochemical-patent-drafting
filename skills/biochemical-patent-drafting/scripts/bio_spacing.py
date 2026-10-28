"""Visible-content space policy; raw sources, XML syntax and field code stay intact."""
from pathlib import Path
import hashlib, unicodedata, zipfile
from lxml import etree as ET

W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
M='http://schemas.openxmlformats.org/officeDocument/2006/math'
A='http://schemas.openxmlformats.org/drawingml/2006/main'
V='urn:schemas-microsoft-com:vml'
C='http://schemas.openxmlformats.org/drawingml/2006/chart'
TEXT={f'{{{ns}}}t' for ns in (W,M,A)}
PARAGRAPHS={f'{{{W}}}p',f'{{{A}}}p'}
def forbidden(c):
    return unicodedata.category(c)=='Zs' or c in '\t\u200b\ufeff\u2060'
def strip(text):return ''.join(c for c in text if not forbidden(c))
def selected_parts(names):
    return [n for n in names if n.startswith('word/') and n.endswith(('.xml','.vml'))]
def fields(node,part):
    if node.tag in TEXT:return [(None,node.text or '')]
    if node.tag==f'{{{V}}}textpath':return [('string',node.get('string',''))]
    if node.tag==f'{{{A}}}buChar':return [('char',node.get('char',''))]
    if node.tag==f'{{{W}}}lvlText':return [(f'{{{W}}}val',node.get(f'{{{W}}}val',''))]
    if node.tag==f'{{{C}}}v' and '/charts/' in part:return [(None,node.text or '')]
    return []
def root_hits(root,part):
    hits=[]
    def walk(node,path):
        if node.tag in {f'{{{W}}}pPr',f'{{{W}}}rPr',f'{{{W}}}del',f'{{{W}}}moveFrom',f'{{{W}}}instrText'}:return
        for attr,value in fields(node,part):
            for i,c in enumerate(value):
                if forbidden(c):hits.append({'part':part,'path':path+(('/@'+attr.rsplit('}',1)[-1]) if attr else ''),'offset':i,'text':c,'codepoint':f'U+{ord(c):04X}','context':value[max(0,i-18):i+19]})
        if node.tag==f'{{{W}}}tab':hits.append({'part':part,'path':path,'offset':0,'text':'\t','codepoint':'U+0009','context':'literal text tab'})
        counts={}
        for child in node:
            name=child.tag.rsplit('}',1)[-1];counts[name]=counts.get(name,0)+1
            walk(child,path+'/'+name+'['+str(counts[name])+']')
    walk(root,root.tag.rsplit('}',1)[-1])
    return hits
def scan_docx(path):
    hits=[]
    with zipfile.ZipFile(path) as z:
        for part in selected_parts(z.namelist()):
            root=ET.fromstring(z.read(part));hits.extend(root_hits(root,part))
    return {'schema_version':1,'artifact_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),'complete':True,'hits':hits,'scope':'Visible text, headers/footers, tables, equations, drawing/chart labels and numbering definitions; images/OLE still need visual review'}
def ambiguous_boundaries(root,part):
    """Do not silently merge English words, variable products or separate numbers."""
    issues=[]
    def check(full):
        for i,c in enumerate(full):
            if not forbidden(c):continue
            k=i-1
            while k>=0 and forbidden(full[k]):k-=1
            j=i+1
            while j<len(full) and forbidden(full[j]):j+=1
            before=full[k:k+1] if k>=0 else '';after=full[j:j+1]
            latin=lambda x:bool(x and x.isascii() and x.isalpha())
            if latin(before) and latin(after) or before.isdigit() and after.isdigit():
                issues.append({'part':part,'context':full[max(0,i-22):j+22],'reason':'source-bound no-space rewording or native mathematical structure required before generation'})
    for p in root.iter():
        if p.tag not in PARAGRAPHS:continue
        chars=[];math_groups={}
        for n in p.iter():
            # A nested text box has its own paragraph and must not be joined to its host.
            owner=next((a for a in n.iterancestors() if a.tag in PARAGRAPHS),None)
            if owner is not p:continue
            if n.tag==f'{{{M}}}oMath':chars.append('\n')
            elif n.tag==f'{{{M}}}t':
                slots={f'{{{M}}}'+x for x in ('e','num','den','sub','sup','lim','deg','oMath')}
                slot=next((a for a in n.iterancestors() if a.tag in slots),p)
                math_groups.setdefault(slot,[]).extend(n.text or '')
            elif n.tag in TEXT:chars.extend(n.text or '')
            elif n.tag==f'{{{W}}}tab':chars.append('\t')
            elif n.tag in {f'{{{W}}}br',f'{{{W}}}cr'}:chars.append('\n')
        for group in [chars,*math_groups.values()]:
            check(''.join(group))
    for node in root.iter():
        if not any(p.tag in PARAGRAPHS for p in node.iterancestors()):
            for attr,value in fields(node,part):check(value)
    return issues
def normalize_root(root,part):
    hits=root_hits(root,part)
    if not hits:return 0
    ambiguities=ambiguous_boundaries(root,part)
    if ambiguities:
        raise ValueError('No-space conversion needs source-bound rewording; do not join distinct words/numbers: '+repr(ambiguities[:3]))
    for node in list(root.iter()):
        for attr,value in fields(node,part):
            cleaned=strip(value)
            if attr is None:node.text=cleaned
            else:node.set(attr,cleaned)
        if node.tag==f'{{{W}}}tab' and not any(p.tag in {f'{{{W}}}pPr',f'{{{W}}}tabs'} for p in node.iterancestors()):node.getparent().remove(node)
    return len(hits)

def normalize(path):
    from bio_package import normalize as normalize_package
    return normalize_package(path,('spacing',))['spacing']
