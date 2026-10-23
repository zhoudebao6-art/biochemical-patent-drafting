"""Convert Unicode script glyphs to editable Word run-level sub/superscript.

Only explicit script characters are mapped; ordinary digits, chemical locants,
sample IDs and real OMML structures are never guessed or flattened.
"""
from pathlib import Path
from copy import deepcopy
import hashlib,unicodedata,zipfile,os,tempfile
from lxml import etree as ET
from bio_spacing import selected_parts,fields

W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
M='http://schemas.openxmlformats.org/officeDocument/2006/math'
def q(n):return '{'+W+'}'+n
MAP={}
for c in '¹²³'+''.join(chr(i) for i in range(0x2070,0x20a0)):
    name=unicodedata.name(c,'');decomposition=unicodedata.decomposition(c).split()
    if decomposition and decomposition[0] in ('<super>','<sub>') and ('SUPERSCRIPT' in name or 'SUBSCRIPT' in name):
        normal=''.join(chr(int(x,16)) for x in decomposition[1:]).replace('−','-')
        MAP[c]=(normal,'superscript' if decomposition[0]=='<super>' else 'subscript')

def root_hits(root,part):
    hits=[]
    for node in root.iter():
        if any(a.tag in {q('del'),q('moveFrom')} for a in node.iterancestors()):continue
        for attr,value in fields(node,part):
            for i,c in enumerate(value):
                if c in MAP:hits.append({'code':'unicode_script_glyph','part':part,'path':root.getroottree().getpath(node),'attribute':attr,'offset':i,'character':c,'codepoint':f'U+{ord(c):04X}','plain':MAP[c][0],'script':MAP[c][1],'context':value[max(0,i-14):i+15]})
    return hits

def scan_package(z,artifact_sha,root_reader=None):
    root_reader=root_reader or (lambda name: ET.fromstring(z.read(name)))
    parts=selected_parts(z.namelist());issues=[];native={'subscript':0,'superscript':0}
    for part in parts:
        root=root_reader(part);issues.extend(root_hits(root,part))
        for node in root.iter(q('vertAlign')):
            val=node.get(q('val'))
            if val in native:native[val]+=1
    return {'schema_version':1,'artifact_sha256':artifact_sha,'complete':'word/document.xml' in parts,'issues':issues,'native_word_script_properties':native,
            'scope':'Unicode script glyph scan in editable visible OOXML; native Word scripts and OMML retained. Ordinary digits require source semantic review; images/OLE and complex formula repairs require independent visual/source review.'}

def scan_docx(path):
    with zipfile.ZipFile(path) as z:return scan_package(z,hashlib.sha256(Path(path).read_bytes()).hexdigest())

def normalize_root(root,part):
    changes=[]
    for run in list(root.iter(q('r'))):
        text=''.join(n.text or '' for n in run.findall(q('t')))
        if not any(c in MAP for c in text):continue
        if any(c.tag not in {q('rPr'),q('t')} for c in run) or any(a.tag.startswith('{'+M+'}') for a in run.iterancestors()):
            raise ValueError('Unicode script in complex run/math requires explicit source-supported native editing: '+part)
        pr=run.find(q('rPr'));align=pr.find(q('vertAlign')) if pr is not None else None
        current=align.get(q('val')) if align is not None else None
        segments=[]
        for c in text:
            plain,script=MAP.get(c,(c,None))
            if script and current in ('subscript','superscript') and script!=current:
                raise ValueError('Conflicting nested scripts require native OMML/source review: '+part)
            if segments and segments[-1][1]==script:segments[-1]=(segments[-1][0]+plain,script)
            else:segments.append((plain,script))
        replacements=[]
        for value,script in segments:
            new=ET.Element(q('r'),attrib=dict(run.attrib))
            props=deepcopy(pr) if pr is not None else ET.Element(q('rPr'))
            if script:
                for n in list(props):
                    if n.tag in {q('vertAlign'),q('position')}:props.remove(n)
                ET.SubElement(props,q('vertAlign')).set(q('val'),script)
            if len(props):new.append(props)
            t=ET.SubElement(new,q('t'));t.text=value
            if value[:1].isspace() or value[-1:].isspace():t.set('{http://www.w3.org/XML/1998/namespace}space','preserve')
            replacements.append(new)
        parent=run.getparent();index=parent.index(run)
        for i,new in enumerate(replacements):parent.insert(index+i,new)
        parent.remove(run)
        changes.append({'part':part,'original':text,'segments':[{'text':value,'script':script or 'unchanged'} for value,script in segments]})
    remaining=root_hits(root,part)
    if remaining:raise ValueError('Unicode scripts in unsupported editable fields need native source-supported editing: '+repr(remaining[:2]))
    return changes

def normalize(path):
    from bio_package import normalize as normalize_package
    return normalize_package(path,('native_scripts',))['native_scripts']
