"""Source-bound analysis ordering, clean summary prose, and patent table layout."""
from copy import deepcopy
import re, unicodedata

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
def section_content_width(section):
    """Usable section width in twips; unknown/multicolumn geometry needs review."""
    if section is None:return None
    size=section.find('w:pgSz',NS);margins=section.find('w:pgMar',NS)
    columns=section.find('w:cols',NS)
    if size is None or margins is None:return None
    if columns is not None and (columns.get(qn('w:num'),'1')!='1' or len(columns.findall('w:col',NS))>1):return None
    try:
        width=int(size.get(qn('w:w')))-sum(int(margins.get(qn('w:'+k),'0')) for k in ('left','right','gutter'))
    except (ValueError,TypeError):return None
    return width if width>0 else None

def table_width_plan(table,available_twips=None):
    """Estimate normal text widths, leaving complex source structures untouched.

    This is a layout estimate, never proof of one-line rendering. Required text,
    paragraphs, manual breaks and native scripts are not rewritten to fit.
    """
    grid=table.find('w:tblGrid',NS);rows=table.findall('w:tr',NS)
    try:old=[int(c.get(qn('w:w'))) for c in grid] if grid is not None else []
    except (ValueError,TypeError):old=[]
    review={'mode':'source_geometry_requires_review','column_widths_twips':old}
    if not old or any(w<=0 for w in old) or not rows:return dict(review,reason='grid_unresolved')
    if table.find('w:tblPr/w:tblpPr',NS) is not None:return dict(review,reason='floating_table')
    n=len(old);cells=[]
    for row in rows:
        current=row.findall('w:tc',NS)
        if len(current)!=n or row.find('w:trPr/w:gridBefore',NS) is not None or row.find('w:trPr/w:gridAfter',NS) is not None:
            return dict(review,reason='nonrectangular_grid')
        for c in current:
            if any(c.find('w:tcPr/w:'+tag,NS) is not None for tag in ('gridSpan','vMerge','hMerge','textDirection')):
                return dict(review,reason='merged_or_rotated_cells')
            if any(node.tag in {qn('w:'+tag) for tag in ('tbl','drawing','pict','object','sym','fldChar','fldSimple','instrText','tab','numPr')} or node.tag.startswith('{'+M+'}') for node in c.iter()):
                return dict(review,reason='rich_or_generated_content')
        cells.append(current)
    available=available_twips if available_twips is not None else sum(old)
    if type(available) is not int or available<n*720:return dict(review,reason='insufficient_or_unknown_width')
    needs=[720]*n
    for row in cells:
        for j,c in enumerate(row):
            # 80-twip padding per side plus a small rendering safety margin.
            lines=[]
            for p in c.findall('w:p',NS):
                extent=0
                for run in p.findall('.//w:r',NS):
                    size=run.find('w:rPr/w:sz',NS)
                    try:em=int(size.get(qn('w:val')))*10 if size is not None else 240
                    except (ValueError,TypeError):em=240
                    for ch in visible(run):
                        if ch.isspace() or unicodedata.combining(ch):continue
                        extent+=em if unicodedata.east_asian_width(ch) in ('W','F') else em*.6
                lines.append(extent)
            needs[j]=max(needs[j],int(max(lines,default=0)+280))
    # Water-fill: satisfy short columns first; long columns share what remains.
    widths=[0]*n;remaining=available;pending=set(range(n))
    while pending:
        short=[j for j in sorted(pending) if needs[j]<=remaining/len(pending)]
        if not short:
            for j in sorted(pending):
                widths[j]=remaining//len(pending);remaining-=widths[j];pending.remove(j)
            break
        for j in short:widths[j]=needs[j];remaining-=needs[j];pending.remove(j)
    if remaining:
        total=sum(needs)
        for j in range(n):
            extra=remaining if j==n-1 else (available-sum(needs))*needs[j]//total
            widths[j]+=extra;remaining-=extra
    return {'mode':'content_balanced','available_width_twips':available,'column_widths_twips':widths,
            'estimated_single_line_twips':needs,'estimated_wrapping_columns':[j for j in range(n) if widths[j]<needs[j]],
            'visual_review_required':True}

def apply_table_widths(table,available_twips):
    plan=table_width_plan(table,available_twips)
    if plan['mode']!='content_balanced':return plan
    widths=plan['column_widths_twips'];tp=table.find('w:tblPr',NS)
    set_prop(tp,'tblW',w=sum(widths),type='dxa');set_prop(tp,'tblLayout',type='fixed')
    for col,width in zip(table.find('w:tblGrid',NS),widths):col.set(qn('w:w'),str(width))
    for row in table.findall('w:tr',NS):
        for cell,width in zip(row.findall('w:tc',NS),widths):
            pr=cell.find('w:tcPr',NS)
            set_prop(pr,'tcW',w=width,type='dxa')
            for tag in ('noWrap','tcFitText'):set_prop(pr,tag,val='0')
    return plan

def table_format(table,header_rows=None,available_twips=None):
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
    width_plan=apply_table_widths(table,available_twips)
    return {'header_rows':header_rows,'data_rows':len(rows)-header_rows,'cell_content_changed':False,'mode':'centered_no_indent_natural_spacing_repeated_own_header','width_plan':width_plan}
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
    body=root.find('w:body',NS);section_widths={};width=None
    if body is not None:
        for node in reversed(list(body)):
            section=node if node.tag==qn('w:sectPr') else node.find('w:pPr/w:sectPr',NS)
            if section is not None:width=section_content_width(section)
            if node.tag==qn('w:tbl'):section_widths[node]=width
    for i,t in enumerate(root.findall('.//w:tbl',NS),1):
        rows=t.findall('w:tr',NS);headers=[]
        width_plan=table_width_plan(t,section_widths.get(t))
        if width_plan['mode']=='content_balanced':
            actual=[int(c.get(qn('w:w'))) for c in t.find('w:tblGrid',NS)]
            if t in section_widths and section_widths[t] and sum(actual)>section_widths[t]:
                issues.append({'table':i,'code':'table_exceeds_section_width'})
            preferred=t.find('w:tblPr/w:tblW',NS)
            if preferred is not None and preferred.get(qn('w:type'))=='dxa' and preferred.get(qn('w:w'))!=str(sum(actual)):
                issues.append({'table':i,'code':'table_grid_width_mismatch'})
            for row in rows:
                for j,cell in enumerate(row.findall('w:tc',NS)):
                    cell_width=cell.find('w:tcPr/w:tcW',NS)
                    if cell_width is None or cell_width.get(qn('w:type'))!='dxa' or cell_width.get(qn('w:w'))!=str(actual[j]):
                        issues.append({'table':i,'cell':j,'code':'cell_grid_width_mismatch'})
                    for tag in ('noWrap','tcFitText'):
                        flag=cell.find('w:tcPr/w:'+tag,NS)
                        if flag is not None and flag.get(qn('w:val'),'1') not in ('0','false','off'):
                            issues.append({'table':i,'cell':j,'code':'forced_cell_text_fit','property':tag})
            width_plan['actual_widths_twips']=actual
            width_plan['avoidable_wrap_review_columns']=[j for j,need in enumerate(width_plan['estimated_single_line_twips'])
                if actual[j]<need<=width_plan['column_widths_twips'][j]]
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
        tables.append({'number':i,'rows':len(rows),'header_rows':headers,'header_texts':[[visible(c) for c in rows[j].findall('w:tc',NS)] for j in headers],'width_plan':width_plan})
    return {'schema_version':1,'artifact_sha256':artifact_sha,'complete':True,'width_contract_version':1,'tables':tables,'issues':issues,'scope':'Width estimates are not proof of rendered line counts; source field/unit/merged header meaning and every continued page need review'}
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
