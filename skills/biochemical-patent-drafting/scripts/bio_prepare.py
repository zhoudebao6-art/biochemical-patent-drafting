"""Read-only biochemical evidence inventory and section/claim/figure candidates."""
from pathlib import Path
import argparse, re, subprocess, zipfile
from docx import Document
from lxml import etree as ET
from bio_common import sha, write

HEADINGS=['技术概括','工作原理','原理说明','产品背景','技术效果','实施方案','参考图示','反应文献支撑','参考文献']
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
M='http://schemas.openxmlformats.org/officeDocument/2006/math'
def text(n): return ''.join(n.xpath('.//w:t/text() | .//m:t/text()'))
def prepare(source, out, soffice=None):
    source=Path(source).resolve(); out=Path(out).resolve()
    if out.exists() and any(out.iterdir()): raise ValueError('Evidence directory must be new/empty')
    out.mkdir(parents=True,exist_ok=True)
    original_sha=sha(source); current=source; converted=False
    if not zipfile.is_zipfile(source):
        if source.suffix.lower()!='.doc' or not soffice: raise ValueError('Binary DOC needs --soffice; renaming is not conversion')
        cv=out/'converted'; cv.mkdir()
        r=subprocess.run([str(soffice),'-env:UserInstallation='+(out/'lo-profile').as_uri(),'--headless','--convert-to','docx','--outdir',str(cv),str(source)],capture_output=True,timeout=120)
        current=cv/(source.stem+'.docx'); converted=True
        if r.returncode or not current.is_file(): raise ValueError('DOC conversion failed: '+r.stdout.decode(errors='replace'))
    d=Document(current); rows=[]; section=None; sections={}; claims=[]; figures=[]; figure=None; issues=[]
    for i,node in enumerate(d.element.body):
        kind=ET.QName(node).localname
        if kind=='sectPr': continue
        t=text(node); heading=t.strip().rstrip('：:')
        if heading in HEADINGS: section=heading
        xml=ET.tostring(node,encoding='unicode')
        row={'body_index':i,'locator':f'word/document.xml/body/*[{i+1}]','kind':kind,'text':t,'section':section,'xml':xml,'math':node.xpath('.//m:oMath'),'relationships':[]}
        row['math']=[ET.tostring(x,encoding='unicode') for x in row['math']]
        row['scripts']=[{'text':text(r),'vertAlign':r.xpath('./w:rPr/w:vertAlign/@w:val'),'position':r.xpath('./w:rPr/w:position/@w:val')} for r in node.xpath('.//w:r') if r.xpath('./w:rPr/w:vertAlign | ./w:rPr/w:position')]
        from bio_scripts import root_hits as script_glyph_hits
        row['unicode_script_glyphs']=script_glyph_hits(node,'word/document.xml')
        for n in node.iter():
            for key,val in n.attrib.items():
                if key.startswith('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'):
                    rel=d.part.rels.get(val)
                    row['relationships'].append({'id':val,'type':rel.reltype if rel else None,'target':str(rel.target_ref) if rel else None,'sha256':None if not rel or rel.is_external else __import__('hashlib').sha256(rel.target_part.blob).hexdigest()})
        rows.append(row); sections.setdefault(section or 'metadata',[]).append(i)
        if section=='参考图示':
            mt=re.match(r'^\s*(?:[（(]主图[）)]\s*)?图\s*(\d+)\s*[:：](.*)',t)
            if mt:
                figure={'number':int(mt[1]),'name':mt[2].strip().rstrip('。'),'main':'主图' in t[:mt.start(2)],'caption_body_index':i,'image_body_indices':[],'explanation_body_indices':[]}; figures.append(figure)
                # Most supplied books have image immediately BEFORE its caption.
                if len(rows)>1 and not rows[-2]['text'].strip() and rows[-2]['relationships']:
                    figure['image_body_indices'].append(rows[-2]['body_index'])
                elif len(rows)>1 and rows[-2]['relationships']:
                    issues.append(f'Figure {mt[1]} previous image paragraph also contains text; inspect exact boundary')
            elif figure and t.strip(): figure['explanation_body_indices'].append(i)
            elif figure and row['relationships']:
                # Do not attach a following image to the prior caption automatically.
                pass
    for h in ['技术概括','产品背景','技术效果','实施方案','参考图示']:
        if h not in sections: issues.append('Missing source heading: '+h)
    if len([f for f in figures if f['main']])!=1: issues.append('Main figure must be identified from source, not guessed')
    for f in figures:
        if not f['image_body_indices']: issues.append('Image association unresolved for figure '+str(f['number']))
    if any(n.xpath('.//w:object') for n in d.element.body): issues.append('OLE objects present; retain binary/preview and inspect visually')
    if any(n.xpath('.//w:numPr') for n in d.element.body): issues.append('Source automatic numbering present; verify numbering definitions when importing')
    title_row=next((r for r in rows if r['text'].startswith('产品名称')),None)
    if title_row:
        title=title_row['text'].removeprefix('产品名称').strip('：: \n'); title_basis='explicit_product_name'
        if not title:
            pos=rows.index(title_row)
            following=rows[pos+1] if pos+1<len(rows) else None
            if following and following['section'] is None and following['text'].strip():
                title_row=following;title=following['text'].strip();title_basis='paragraph_after_product_name_label'
    else:
        cover=[r for r in rows if r['section'] is None and re.match(r'^一种\S',r['text'].strip())]
        title_row=cover[0] if len(cover)==1 else None
        title=title_row['text'].strip() if title_row else None;title_basis='unique_cover_name_needs_semantic_confirmation'
    if not title:issues.append('Formal title unresolved; inspect cover and abstract, do not derive it from filename alone')
    from bio_claims import candidates
    claims=candidates(rows)
    evidence={'schema_version':1,'source':{'path':str(source),'sha256':original_sha},'working_source':{'path':str(current),'sha256':sha(current),'converted':converted},'title_candidate':title,'title_evidence':{'body_index':title_row['body_index'] if title_row else None,'basis':title_basis,'status':'candidate_needs_semantic_confirmation'},'sections':sections,'claim_candidates':claims,'figures':figures,'body':rows,'issues':issues,'approval':'not_reviewed'}
    write(out/'evidence.json',evidence)
    (out/'content.txt').write_text('\n'.join(f"[{r['body_index']}] ({r['section']}) {r['text']}" for r in rows),encoding='utf-8')
    if sha(source)!=original_sha: raise ValueError('Original changed during extraction')
    return evidence
def main():
    p=argparse.ArgumentParser(); p.add_argument('source'); p.add_argument('--out',required=True); p.add_argument('--soffice'); a=p.parse_args()
    e=prepare(a.source,a.out,a.soffice); print(__import__('json').dumps({'title':e['title_candidate'],'claims':len(e['claim_candidates']),'figures':len(e['figures']),'issues':e['issues']},ensure_ascii=False))
if __name__=='__main__':main()
