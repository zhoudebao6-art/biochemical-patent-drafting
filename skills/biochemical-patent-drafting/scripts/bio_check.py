"""Mechanical preflight. A clean result is never semantic or visual acceptance."""
from pathlib import Path
import argparse, re, zipfile
from docx import Document
from lxml import etree as ET
from bio_common import sha, read, write
from bio_prepare import text
from bio_package import scan_docx
from bio_layout import table_evidence, analysis_evidence
from bio_presentation import evidence as presentation_evidence

def inspect(path,plan=None,evidence=None):
    path=Path(path); d=Document(path); errors=[]; warnings=[]
    scans=scan_docx(path)
    spacing=scans["spacing"];background=scans["background"];scripts=scans["native_scripts"]
    if not scripts['complete'] or scripts['issues']:errors.append('Unicode script glyphs require native script formatting: '+str(scripts['issues']))
    if not background['complete'] or background['issues']:errors.append('Page fill/shading/highlight remains: '+str(background['issues']))
    if spacing['hits']:errors.append('Visible-content spaces/tabs remain: '+str(len(spacing['hits'])))
    with zipfile.ZipFile(path) as z:
        if z.testzip(): errors.append('Damaged ZIP member')
    alltext='\n'.join(text(n) for n in d.element.body)
    parts=[]; current=[]
    for n in d.element.body:
        if ET.QName(n).localname=='sectPr': continue
        current.append(n)
        if n.xpath('./w:pPr/w:sectPr'): parts.append(current); current=[]
    if current: parts.append(current)
    tables_layout=table_evidence(d.element,sha(path))
    presentation=presentation_evidence(d.element,d.styles.element,sha(path))
    description=parts[3] if len(parts)==5 else list(d.element.body)
    analysis=analysis_evidence([{'p':i,'text':text(n),'body_direct':True,'biochemical_role':n.pPr.pStyle.val if n.pPr is not None and n.pPr.pStyle is not None else None} for i,n in enumerate(description) if ET.QName(n).localname=='p'],sha(path))
    errors.extend('Table layout: '+str(i) for i in tables_layout['issues'])
    errors.extend('Analysis layout: '+str(i) for i in analysis['issues'])
    errors.extend('Presentation: '+str(i) for i in presentation['issues'])
    claim_structure=None;claim_source=None
    if len(d.sections)!=5 or len(parts)!=5: errors.append('Expected five logical sections')
    if len(parts)==5:
        claims='\n'.join(text(n) for n in parts[2]); elsewhere='\n'.join(text(n) for part in parts[:2]+parts[3:] for n in part)
        if '其特征在于' in elsewhere: errors.append('Feature phrase outside claims')
        from bio_claims import collect,analyze,source_check
        detected=collect([{'text':text(n),'p':i,'manual_breaks':len(n.xpath('.//w:br | .//w:cr | .//w:tab'))} for i,n in enumerate(parts[2])])
        nums=[c['number'] for c in detected]
        claim_structure=analyze(detected,plan['claim_map'] if plan else None)
        errors.extend(claim_structure['issues'])
        if plan and evidence:
            claim_source=source_check(detected,plan['claim_map'],evidence);errors.extend(claim_source['issues'])
        for h in ['技术领域','背景技术','发明内容','附图说明','具体实施方式']:
            if not any(text(n).strip()==h for n in parts[3]): errors.append('Missing description heading '+h)
        if plan:
            if not any(text(n).strip()==plan['title'] for n in parts[3]): errors.append('Formal title mismatch')
        if any(re.fullmatch(r'\s*图\s*\d+.*',text(n)) for n in parts[1]): errors.append('External caption on abstract figure page')
    for old in ['本产品','本方案','本技术']:
        if old in alltext: errors.append('Unnormalized self-reference: '+old)
    if re.search(r'BIO_SLOT_|\[待填写\]|TODO|FIXME',alltext): errors.append('Unfilled placeholder')
    if d.element.body.xpath('.//w:ins | .//w:del'): errors.append('Tracked changes remain')
    if d.element.body.xpath('.//w:object'): warnings.append('OLE objects require real visual review')
    if d.element.body.xpath('.//w:numPr'): warnings.append('Automatic numbering needs source numbering verification')
    tables=[]
    for t in d.tables: tables.append([[c.text for c in row.cells] for row in t.rows])
    if evidence:
        from bio_presentation import example_entries,compare_examples
        expected=example_entries([{'text':r['text'],'kind':r['kind'],'location':r['body_index']} for r in evidence['body']],True)
        errors.extend('Source example: '+str(i) for i in compare_examples(expected,presentation['examples']))
        source_tables=[r for r in evidence['body'] if r['section']=='实施方案' and r['kind']=='tbl']
        if len(source_tables)!=len(tables): errors.append('Implementation table count differs from source')
        source_scripts=sum(len(r['scripts']) for r in evidence['body'])
        if source_scripts and not d.element.body.xpath('.//w:vertAlign | .//w:position'): errors.append('All source sub/superscript formatting lost')
    r={'schema_version':1,'path':str(path.resolve()),'artifact_sha256':sha(path),'sections':len(d.sections),'claims':len(nums) if len(parts)==5 else 0,'tables':len(tables),'images':len(d.inline_shapes),'native_math':len(d.element.body.xpath('.//m:oMath')),'spacing':spacing,'table_layout':tables_layout,'analysis_layout':analysis,'presentation':presentation,'errors':errors,'warnings':warnings,'status':'mechanical_pass' if not errors else 'mechanical_fail','review':'not_semantically_or_visually_accepted'}
    r['background']=background
    r['native_scripts']=scripts
    r['claim_structure']=claim_structure
    r['claim_source']=claim_source
    return r
def main():
    p=argparse.ArgumentParser(); p.add_argument('docx'); p.add_argument('--plan'); p.add_argument('--evidence'); p.add_argument('--out',required=True); a=p.parse_args()
    r=inspect(a.docx,read(a.plan) if a.plan else None,read(a.evidence) if a.evidence else None); write(a.out,r); print(__import__('json').dumps(r,ensure_ascii=False)); raise SystemExit(bool(r['errors']))
if __name__=='__main__':main()
