"""Source-bound analysis ordering, clean summary prose, and patent table layout."""
from copy import deepcopy
import re

W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
M='http://schemas.openxmlformats.org/officeDocument/2006/math'
NS={'w':W,'m':M}
def qn(name):
    prefix,local=name.split(':');return '{'+NS[prefix]+'}'+local
def OxmlElement(name):
    from docx.oxml import OxmlElement as create
    return create(name)
def visible(n):return ''.join(t.text or '' for t in n.iter() if t.tag in {qn('w:t'),qn('m:t')})
SUMMARY=re.compile(r'^\s*技术总结(?:\s*[:：]\s*|\s*$)')
RESULT=re.compile(r'^\s*结果分析(?:\s*[:：]\s*|\s*$)')
FIGURE=re.compile(r'^\s*(?:由|从|根据|结合|参见|如)?图\s*\d+')
MISSING=re.compile(r'^(?:以|通过|采用|利用|经由|经过|经|将|在|结合|根据|按照|基于|首先|先|能够|可以|可|适用|用于)')
def preview(block,evidence):
    if 'source_body_index' in block:
        row=next(r for r in evidence['body'] if r['body_index']==block['source_body_index']);text=row['text']
        if 'slice' in block:text=text[slice(*block['slice'])]
        text=block.get('prefix','')+text
        for old,new in block.get('replace',[]):text=text.replace(old,new)
        return text
    return block.get('text',''.join(r['text'] for r in block.get('runs',[])))
def normalize_plan(plan,evidence):
    plan=deepcopy(plan);changes=[];blocks=plan.get('sections',{}).get('description',[])
    figure_ids={i for f in evidence.get('figures',[]) for i in f.get('explanation_body_indices',[])}
    pending_summary=False;tagged=[]
    for b in blocks:
        value=preview(b,evidence);raw=None
        if 'source_body_index' in b:raw=next(r['text'] for r in evidence['body'] if r['body_index']==b['source_body_index'])
        label=SUMMARY.match(value)
        if label and not value[label.end():].strip():
            pending_summary=True;changes.append({'kind':'remove_summary_label_only','source':b.get('source_body_index')});continue
        if label or raw and SUMMARY.match(raw) or pending_summary and value.strip():
            b['role']='technical_summary';pending_summary=False
        if b.get('role')!='technical_summary' and (b.get('role')=='figure_analysis' or b.get('source_body_index') in figure_ids):b['role']='figure_analysis'
        tagged.append(b)
    analyses=[b for b in tagged if b.get('role')=='figure_analysis']
    if analyses:
        remaining=[b for b in tagged if b.get('role')!='figure_analysis']
        index=next((i for i,b in enumerate(remaining) if RESULT.match(preview(b,evidence)) or b.get('role')=='results_analysis_heading'),None)
        if index is None:raise ValueError('Figure explanations require a source-bound results-analysis heading before generation')
        heading=remaining[index];value=preview(heading,evidence);mt=RESULT.match(value)
        if mt and value[mt.end():].strip():
            if 'source_body_index' not in heading or heading.get('prefix'):raise ValueError('Inline results heading needs explicit source-bound heading/content blocks')
            start,end=heading.get('slice',[0,len(next(r['text'] for r in evidence['body'] if r['body_index']==heading['source_body_index']))])
            first=deepcopy(heading);rest=deepcopy(heading);first['slice']=[start,start+mt.end()];rest['slice']=[start+mt.end(),end]
            first['replace']=[(o,n) for o,n in heading.get('replace',[]) if o in value[:mt.end()]]
            rest['replace']=[(o,n) for o,n in heading.get('replace',[]) if o in value[mt.end():]]
            remaining[index:index+1]=[first,rest]
        remaining[index]['role']='results_analysis_heading'
        for b in analyses:b['role']='figure_analysis'
        tagged=remaining[:index+1]+analyses+remaining[index+1:]
        changes.append({'kind':'figure_analyses_first_in_results','source_body_indices':[b.get('source_body_index') for b in analyses],'count':len(analyses)})
    plan['sections']['description']=tagged
    from bio_presentation import normalize as presentation_normalize
    plan,presentation_changes=presentation_normalize(plan,evidence,preview);changes.extend(presentation_changes)
    from bio_presentation import validate_example_plan
    validate_example_plan(plan,evidence,preview)
    return plan,changes
def set_prop(parent,name,**attrs):
    for old in list(parent.findall(qn('w:'+name))):parent.remove(old)
    child=OxmlElement('w:'+name)
    for key,val in attrs.items():child.set(qn('w:'+key),str(val))
    parent.append(child);return child
def table_format(table,header_rows=None):
    rows=table.findall(qn('w:tr'))
    if not rows:raise ValueError('Empty source table')
    if header_rows is None:
        count=0
        for row in rows:
            h=row.find('./'+qn('w:trPr')+'/'+qn('w:tblHeader'))
            if h is None or h.get(qn('w:val'),'1') in ('0','false','off'):break
            count+=1
        header_rows=count or 1
    if type(header_rows) is not int or not 1<=header_rows<=len(rows):raise ValueError('Explicit contiguous table header row count required')
    tp=table.find(qn('w:tblPr'))
    if tp is None:tp=OxmlElement('w:tblPr');table.insert(0,tp)
    set_prop(tp,'jc',val='center');set_prop(tp,'tblInd',w='0',type='dxa')
    for i,row in enumerate(rows):
        rp=row.find(qn('w:trPr'))
        if rp is None:rp=OxmlElement('w:trPr');row.insert(0,rp)
        for h in list(rp.findall(qn('w:trHeight'))):rp.remove(h)
        set_prop(rp,'tblHeader',val='1' if i<header_rows else '0')
        set_prop(rp,'cantSplit',val='1')
        for cell in row.findall(qn('w:tc')):
            pr=cell.find(qn('w:tcPr'))
            if pr is None:pr=OxmlElement('w:tcPr');cell.insert(0,pr)
            set_prop(pr,'vAlign',val='center')
            margins=set_prop(pr,'tcMar')
            for side in ('top','bottom','left','right'):set_prop(margins,side,w='80',type='dxa')
            for p in cell.findall('.//'+qn('w:p')):
                pp=p.get_or_add_pPr();set_prop(pp,'jc',val='center')
                set_prop(pp,'ind',firstLine='0',firstLineChars='0',left='0',right='0',leftChars='0',rightChars='0')
                set_prop(pp,'spacing',before='0',after='0',line='240',lineRule='auto')
                for name in ('snapToGrid','keepNext','keepLines','pageBreakBefore','widowControl','autoSpaceDE','autoSpaceDN'):set_prop(pp,name,val='1' if name=='keepNext' and i<header_rows else '0')
    return {'header_rows':header_rows,'data_rows':len(rows)-header_rows,'cell_content_changed':False,'mode':'centered_no_indent_natural_spacing_repeated_own_header'}
def summary_format(node,block,replace):
    value=visible(node);label=SUMMARY.match(value)
    if label:replace(node,value[:label.end()],'',required=True)
    value=visible(node).strip()
    if not value:return {'label_removed':bool(label),'subject':'empty_label_only'}
    choice=block.get('summary_subject')
    if choice not in (None,'present','missing'):raise ValueError('summary_subject must be present or missing')
    explicit=re.match(r'^(?:本发明|该方法|该材料|该工艺|本实施例|本方法|本材料|所得材料)',value)
    add=choice=='missing' or choice is None and MISSING.match(value) and not explicit
    if add and not value.startswith('本发明'):
        r=OxmlElement('w:r');t=OxmlElement('w:t');t.text='本发明';r.append(t);node.insert(1 if node.pPr is not None else 0,r)
    return {'label_removed':bool(label),'subject':'added_本发明' if add else 'present' if explicit or choice=='present' else 'requires_semantic_subject_review','technical_content_deleted':False}
def table_evidence(root,artifact_sha):
    tables=[];issues=[]
    for i,t in enumerate(root.findall('.//w:tbl',NS),1):
        rows=t.findall('w:tr',NS);headers=[]
        for j,row in enumerate(rows):
            h=row.find('w:trPr/w:tblHeader',NS)
            if h is not None and h.get(qn('w:val'),'1') not in ('0','false','off'):headers.append(j)
            height=row.find('w:trPr/w:trHeight',NS)
            if height is not None and height.get(qn('w:hRule'))=='exact':issues.append({'table':i,'row':j,'code':'fixed_row_height'})
            for k,c in enumerate(row.findall('w:tc',NS)):
                va=c.find('w:tcPr/w:vAlign',NS)
                if va is None or va.get(qn('w:val'))!='center':issues.append({'table':i,'row':j,'cell':k,'code':'cell_not_vertically_centered'})
                for p in c.findall('.//w:p',NS):
                    jc=p.find('w:pPr/w:jc',NS);ind=p.find('w:pPr/w:ind',NS);sp=p.find('w:pPr/w:spacing',NS)
                    if jc is None or jc.get(qn('w:val'))!='center':issues.append({'table':i,'row':j,'cell':k,'code':'cell_paragraph_not_centered'})
                    if ind is None or any(ind.get(qn('w:'+x),'0')!='0' for x in ('firstLine','firstLineChars','left','right','hanging','hangingChars')):issues.append({'table':i,'row':j,'cell':k,'code':'cell_has_body_indent'})
                    if sp is None or sp.get(qn('w:lineRule'))=='exact' or any(sp.get(qn('w:'+x),'0')!='0' for x in ('before','after')):issues.append({'table':i,'row':j,'cell':k,'code':'cell_has_body_spacing'})
                    keep=p.find('w:pPr/w:keepNext',NS)
                    if j in headers and (keep is None or keep.get(qn('w:val'),'1') in ('0','false','off')):issues.append({'table':i,'row':j,'code':'header_can_orphan_from_first_data_row'})
        if not headers or headers!=list(range(len(headers))):issues.append({'table':i,'code':'own_contiguous_repeated_header_missing'})
        tables.append({'number':i,'rows':len(rows),'header_rows':headers,'header_texts':[[visible(c) for c in rows[j].findall('w:tc',NS)] for j in headers]})
    return {'schema_version':1,'artifact_sha256':artifact_sha,'complete':True,'tables':tables,'issues':issues,'scope':'Mechanical layout only; source field/unit/merged header meaning and every continued page need review'}
def analysis_evidence(paragraphs,artifact_sha):
    rows=[p for p in paragraphs if p.get('body_direct')]
    if any(p.get('section_headers') for p in rows):
        rows=[p for p in rows if '说明书' in [re.sub(r'\s+','',h) for h in p.get('section_headers',[])]]
    issues=[];start=None;figures=[];summaries=[]
    marked=any(p.get('biochemical_role')=='BioFigureAnalysis' for p in rows)
    def is_figure(p):
        value=p['text'].strip()
        return p.get('biochemical_role')=='BioFigureAnalysis' if marked else bool(FIGURE.match(value) and not re.fullmatch(r'图\d+',value))
    for p in rows:
        value=p['text'].strip()
        if RESULT.match(value):start=p['p']
        if SUMMARY.match(value):issues.append({'paragraph':p['p'],'code':'technical_summary_label_remains'})
        if p.get('biochemical_role')=='BioTechnicalSummary':summaries.append({'paragraph':p['p'],'text':value,'subject_status':'explicit_本发明' if value.startswith('本发明') else 'requires_semantic_subject_review'})
        if start is not None and p['p']>start and is_figure(p):figures.append(p['p'])
    if figures and start is not None:
        between=[p for p in rows if start<p['p']<figures[0] and p['text'].strip()]
        if between:issues.append({'paragraph':between[0]['p'],'code':'figure_analysis_not_first_in_results'})
        lo,hi=min(figures),max(figures)
        if any(lo<p['p']<hi and p['text'].strip() and not is_figure(p) for p in rows):issues.append({'paragraph':lo,'code':'figure_analyses_interleaved_with_general_results'})
    return {'schema_version':1,'artifact_sha256':artifact_sha,'complete':True,'results_heading':start,'figure_analysis_paragraphs':figures,'technical_summaries':summaries,'detection':'explicit_generation_roles' if marked else 'text_pattern_candidates','issues':issues,'scope':'Source coverage and summary subject require semantic review; generation roles locate multi-paragraph analyses without adding visible labels'}
