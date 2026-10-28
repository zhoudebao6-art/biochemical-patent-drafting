"""Source-bound benefit introduction, plain auxiliary labels and per-table captions."""
import re

W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
M='http://schemas.openxmlformats.org/officeDocument/2006/math'
NS={'w':W,'m':M}
MAIN_HEADINGS={'技术领域','背景技术','发明内容','附图说明','具体实施方式'}
BENEFIT_INTRO='与现有技术相比，本发明的有益效果在于：'
BENEFIT_LABELS={'有益效果','有益效果：','技术效果','技术效果：'}
OLD_INTRO=re.compile(r'^(?:(?:优化方案|本发明|本方案|本技术)(?:所)?带来的?技术效果(?:如下|在于)|(?:本发明|本方案|本技术)(?:的)?(?:有益效果|技术效果)(?:如下|在于))[:：]?$')
SHARED_TITLE='各实施例与对比例的性能测试结果'
CAPTION=re.compile(r'^表\s*(\d+)(?!\d)\s*[:：、．.]?\s*([^:：、．.\s].*)$')
def qn(n):return '{'+W+'}'+n
def visible(n):return ''.join(t.text or '' for t in n.iter() if t.tag in {qn('t'),'{'+M+'}t'})
def compact(s):return re.sub(r'\s+','',s)
def locators(b):
    return [b['source_body_index']] if 'source_body_index' in b else b.get('source_body_indices',[])

EXAMPLE=re.compile(r'^(实施例|对比例)([0-9一二三四五六七八九十百零〇]+)(?:[：:](.*)|$)')

def canonical_prose(value):
    from bio_scripts import MAP
    value=compact(value)
    for old in ('本产品','本方案','本技术'):value=value.replace(old,'本发明')
    return ''.join(MAP[c][0] if c in MAP else c for c in value)

def example_entries(rows,source=False):
    """Locate source introductions without deriving scientific content from titles."""
    active=False;out=[]
    for pos,row in enumerate(rows):
        value=canonical_prose(row['text'])
        if value.rstrip('：:') in ({'实施方案'} if source else {'具体实施方式'}):active=True;continue
        if value.rstrip('：:') in ({'参考图示','反应文献支撑','参考文献'} if source else MAIN_HEADINGS):active=False
        if not active or row.get('kind','p')!='p':continue
        match=EXAMPLE.fullmatch(value)
        if not match:continue
        key=match[1]+match[2];tail=match[3] or '';indices=[row['location']]
        split=False
        if not tail:
            following=next((r for r in rows[pos+1:] if compact(r['text'])),None)
            if following and re.match(r'^本(?:实施|对比)例',canonical_prose(following['text'])):
                tail=canonical_prose(following['text']);indices.append(following['location']);split=True
        # Only a real source introduction supplies its wording. Bare source
        # labels or direct process text never authorize inventing "preferred".
        intro=(tail.split('。',1)[0]+'。') if '。' in tail else tail
        out.append({'key':key,'introduction':intro,'text':key+('：'+intro if intro else ''),'raw_text':row['text'],'locations':indices,'split':split})
    return out

def compare_examples(expected,actual):
    issues=[]
    for row in expected:
        matches=[x for x in actual if x['key']==row['key']]
        if len(matches)!=1:issues.append({'code':'example_missing_or_duplicate','key':row['key'],'source_locations':row['locations']});continue
        current=matches[0]
        if row['introduction'] and current['introduction']!=row['introduction']:
            issues.append({'code':'example_introduction_changed_or_truncated','key':row['key'],'source_text':row['text'],'actual_text':current['text']})
        if row['introduction'] and current['split']:issues.append({'code':'example_introduction_split','key':row['key']})
    return issues

def validate_example_plan(plan,evidence,preview):
    source=[{'text':r['text'],'kind':r['kind'],'location':r['body_index']} for r in evidence['body']]
    kinds={r['body_index']:r['kind'] for r in evidence['body']}
    actual=[{'text':preview(b,evidence),'location':i,'kind':kinds.get(b.get('source_body_index'),'p')} for i,b in enumerate(plan['sections']['description'])]
    problems=compare_examples(example_entries(source,True),example_entries(actual))
    if problems:raise ValueError('Source example introduction must be complete in the same paragraph: '+str(problems))

def source_examples_from_report(report):
    body=next(p for p in report['parts'] if p['part']=='word/document.xml')['paragraphs']
    return example_entries([{'text':p['text'],'kind':'p','location':p['p']} for p in body if p.get('body_direct',True)],True)

def figure_description_entries(root):
    """Expected terminal mark by position within each actual description list."""
    body=root.find('w:body',NS);active=False;pending=[];entries=[]
    def finish():
        entries.extend((i,p,'。' if pos==len(pending)-1 else '；')
                       for pos,(i,p) in enumerate(pending))
        pending.clear()
    for i,n in enumerate(body if body is not None else []):
        if n.tag!=qn('p'):continue
        value=compact(visible(n))
        if value.rstrip('：:') in MAIN_HEADINGS:
            finish()
            active=value.rstrip('：:')=='附图说明';continue
        if active and re.match(r'^图\d+(?!\d).+',value):pending.append((i,n))
    finish()
    return entries

def figure_description_nodes(root):
    """Compatibility view containing only located list paragraphs."""
    for i,p,_ in figure_description_entries(root):yield i,p

def normalize_figure_description_endings(root):
    """Change only the list-entry terminal mark, never flatten rich text/math."""
    from lxml import etree as ET
    changes=[]
    for i,p,ending in figure_description_entries(root):
        before=visible(p)
        if before.rstrip().endswith(ending):continue
        nodes=[n for n in p.iter() if n.tag in {qn('t'),'{'+M+'}t'} and (n.text or '').strip()]
        last=nodes[-1] if nodes else None
        if last is not None and last.tag==qn('t') and last.text.rstrip().endswith(('。','.',';','；')):
            value=last.text.rstrip();last.text=value[:-1]+ending+last.text[len(value):]
        else:
            run=ET.SubElement(p,qn('r'));props=ET.SubElement(run,qn('rPr'))
            ET.SubElement(props,qn('vertAlign')).set(qn('val'),'baseline')
            ET.SubElement(props,qn('position')).set(qn('val'),'0')
            ET.SubElement(run,qn('t')).text=ending
        changes.append({'body_index':i,'before':before,'after':visible(p),
                        'kind':'figure_description_terminal_full_stop' if ending=='。' else 'figure_description_terminal_semicolon',
                        'expected_ending':ending})
    return changes

def normalize(plan,evidence,preview):
    rows={r['body_index']:r for r in evidence['body']};changes=[];blocks=[];benefit_added=False
    for b in plan['sections']['description']:
        value=compact(preview(b,evidence));ids=locators(b)
        if value in BENEFIT_LABELS:
            changes.append({'kind':'remove_extra_benefit_heading','source_body_indices':ids});continue
        if OLD_INTRO.fullmatch(value) or value==BENEFIT_INTRO:
            if not benefit_added:
                blocks.append({'text':BENEFIT_INTRO,'role':'benefit_intro','source_body_indices':ids});benefit_added=True
            changes.append({'kind':'single_standard_benefit_intro','source_body_indices':ids});continue
        if not benefit_added and any(rows.get(i,{}).get('section')=='技术效果' for i in ids) and value:
            blocks.append({'text':BENEFIT_INTRO,'role':'benefit_intro','source_body_indices':ids});benefit_added=True
            changes.append({'kind':'standard_benefit_intro_before_source_effects','source_body_indices':ids})
        blocks.append(b)
    def is_table(b):return rows.get(b.get('source_body_index'),{}).get('kind')=='tbl'
    def meaningful(b):
        row=rows.get(b.get('source_body_index'),{})
        return bool(preview(b,evidence).strip() or is_table(b) or b.get('role')=='image' or row.get('relationships') or row.get('math') or row.get('has_content_object') or re.search(r'<(?:w:(?:drawing|pict|object|fldChar)|m:oMath)\b',row.get('xml','')))
    def next_nonempty(i):
        return next((j for j in range(i+1,len(blocks)) if meaningful(blocks[j])),None)
    out=[];number=0;group=None;group_ids=[];group_stop=None;known={}
    for i,b in enumerate(blocks):
        if group_stop is not None and i>=group_stop:group=None;group_ids=[];group_stop=None
        value=compact(preview(b,evidence));nxt=next_nonempty(i)
        if value.rstrip('：:')==SHARED_TITLE:
            stop=next((j for j in range(i+1,len(blocks)) if compact(preview(blocks[j],evidence)).startswith('结果分析') or compact(preview(blocks[j],evidence)).rstrip('：:')==SHARED_TITLE),len(blocks))
            count=sum(is_table(x) for x in blocks[i+1:stop])
            if not count:raise ValueError('Shared performance title has no following source table')
            group=SHARED_TITLE;group_ids=locators(b);group_stop=stop
            first=number+1;last=number+count;ref=f'表{first}' if count==1 else f'表{first}至表{last}'
            out.append({'text':f'测试结果如{ref}所示。','role':'body','source_body_indices':group_ids})
            changes.append({'kind':'shared_heading_to_table_reference','source_body_indices':group_ids,'tables':count});continue
        match=CAPTION.fullmatch(value)
        if b.get('role')=='table_caption' or match and nxt is not None and is_table(blocks[nxt]):
            if not match or nxt is None or not is_table(blocks[nxt]):raise ValueError('A descriptive numbered table caption must directly precede its own table')
            if int(match[1])!=number+1:raise ValueError('Table renumbering requires an explicit source-supported reference update')
            b=dict(b,role='table_caption');out.append(b)
            known[blocks[nxt]['source_body_index']]=(match[2],locators(b))
            continue
        if is_table(b):
            number+=1
            previous=next((j for j in range(len(out)-1,-1,-1) if meaningful(out[j])),None)
            prev=out[previous] if previous is not None else None
            if prev is not None and prev.get('role')=='table_caption' and previous<len(out)-1:
                changes.append({'kind':'remove_pure_blank_between_caption_and_table','source_table_body_index':b['source_body_index']});del out[previous+1:]
            if prev is None or prev.get('role')!='table_caption':
                title=group+str(number) if group else None;ids=group_ids
                if title is None and b['source_body_index'] in known:title,ids=known[b['source_body_index']]
                if title is None:
                    # A numbered caption supplied in the source remains usable
                    # when a plan accidentally omitted that source paragraph.
                    prior=next((rows[j] for j in sorted(rows,reverse=True) if j<b['source_body_index'] and rows[j]['text'].strip()),None)
                    raw=CAPTION.fullmatch(compact(prior['text'])) if prior and prior.get('kind')=='p' else None
                    if raw:
                        if int(raw[1])!=number:raise ValueError('Table renumbering requires an explicit source-supported reference update')
                        title=raw[2];ids=[prior['body_index']]
                if title is None:raise ValueError(f'Table {number} needs a source-bound descriptive caption; no metric title will be invented')
                out.append({'text':f'表{number}{title}','role':'table_caption','source_body_indices':list(dict.fromkeys(ids+[b['source_body_index']]))})
                changes.append({'kind':'own_numbered_table_caption','number':number,'source_table_body_index':b['source_body_index'],'source_title_body_indices':ids})
            b=dict(b,table_number=number)
        out.append(b)
    plan['sections']['description']=out
    return plan,changes

def paragraph_role(requested,value,slot,title):
    if slot!='description':return requested
    if value.strip()==title:return 'title'
    if value.strip() in MAIN_HEADINGS:return 'heading'
    if value.strip().rstrip('：:') in ('制备工艺','配方','测试方法'):return 'auxiliary_label'
    if requested in ('heading','title'):return 'body'
    return requested

# A cached lastRenderedPageBreak is not an authored break. Do not flatten
# runs: Word script properties, inline math and other objects must survive.
FLOW_ROLES={'body','figure_analysis','technical_summary'}
FLOW_BOUNDARY=re.compile(r'^(?:S\d+[、.．：:]|(?:实施例|对比例)\d+[:：]|图\d+为|表\d+|(?:技术领域|背景技术|发明内容|附图说明|具体实施方式)$)')
def prose_breaks(p):
    tokens=[]
    def owned(node):
        for child in node:
            if child.tag==qn('p'):continue
            yield child
            yield from owned(child)
    for n in owned(p):
        if n.tag in (qn('t'),'{'+M+'}t'):tokens.append(('text',n,n.text or ''))
        elif n.tag in (qn('br'),qn('cr')):tokens.append(('break',n,''))
    result=[]
    rich=any(p.find('.//'+tag,NS) is not None for tag in ('w:drawing','w:pict','w:object','w:tab','m:oMathPara','w:fldChar','w:fldSimple'))
    for i,(kind,n,value) in enumerate(tokens):
        if kind!='break':continue
        before=''.join(x[2] for x in tokens[:i]).rstrip()
        after=''.join(x[2] for x in tokens[i+1:]).lstrip()
        typ=n.get(qn('type'),'textWrapping') if n.tag==qn('br') else 'carriageReturn'
        safe=(not rich and typ in ('textWrapping','page','carriageReturn')
              and n.get(qn('clear'),'none')=='none' and before.endswith(('，',',','、'))
              and bool(after) and not FLOW_BOUNDARY.match(compact(after)))
        result.append((n,typ,safe))
    return result

def normalize_prose_flow(p,role,slot):
    if slot!='description' or role not in FLOW_ROLES:return []
    breaks=prose_breaks(p)
    literal=any('\n' in (n.text or '') or '\r' in (n.text or '') for n in p.iter(qn('t')))
    if literal or any(not safe for _,_,safe in breaks):
        raise ValueError('Ambiguous manual prose break: use source-bound natural paragraphs; do not drop text or objects')
    before=visible(p);changes=[]
    for node,typ,_ in breaks:
        node.getparent().remove(node);changes.append({'removed_manual_break':typ,'reason':'continuous_prose_after_comma'})
    assert visible(p)==before,'Prose flow normalization must preserve all text'
    return changes

def _on(node):return node is not None and node.get(qn('val'),'1') not in ('0','false','off')
def bold_reader(styles):
    definitions={s.get(qn('styleId')):s for s in styles.findall('w:style',NS)} if styles is not None else {}
    defaults=styles.find('w:docDefaults/w:rPrDefault/w:rPr',NS) if styles is not None else None
    def from_style(style_id,key,seen=None):
        seen=set() if seen is None else seen
        if not style_id or style_id in seen:return None
        seen.add(style_id);s=definitions.get(style_id)
        if s is None:return None
        item=s.find('w:rPr/w:'+key,NS)
        if item is not None:return _on(item)
        base=s.find('w:basedOn',NS)
        return from_style(base.get(qn('val')),key,seen) if base is not None else None
    def read(p,r):
        for key in ('b','bCs'):
            direct=r.find('w:rPr/w:'+key,NS)
            if direct is not None:
                if _on(direct):return True
                continue
            char=r.find('w:rPr/w:rStyle',NS);para=p.find('w:pPr/w:pStyle',NS)
            val=from_style(char.get(qn('val')),key) if char is not None else None
            if val is None:val=from_style(para.get(qn('val')),key) if para is not None else None
            if val is None and defaults is not None:val=_on(defaults.find('w:'+key,NS))
            if val:return True
        return False
    return read

def evidence(root,styles,artifact_sha):
    body=root.find('w:body',NS);nodes=list(body) if body is not None else []
    text_by_node={}
    def node_text(node):
        if node not in text_by_node:text_by_node[node]=visible(node)
        return text_by_node[node]
    is_bold=bold_reader(styles);issues=[];captions=[];intro=[];labels=[];table_count=0
    field=next((i for i,n in enumerate(nodes) if n.tag==qn('p') and node_text(n).strip()=='技术领域'),None)
    title=next((node_text(n).strip() for n in reversed(nodes[:field]) if n.tag==qn('p') and node_text(n).strip()),None) if field is not None else None
    for i,n in enumerate(nodes):
        if n.tag==qn('tbl'):
            table_count+=1
            previous=next(((j,nodes[j]) for j in range(i-1,-1,-1) if nodes[j].tag!=qn('p') or node_text(nodes[j]).strip()),None)
            prev=previous[1] if previous is not None else None
            mt=CAPTION.fullmatch(compact(node_text(prev))) if prev is not None and prev.tag==qn('p') else None
            if not mt:issues.append({'body_index':i,'table':table_count,'code':'descriptive_table_caption_missing'});continue
            if int(mt[1])!=table_count:issues.append({'body_index':i,'table':table_count,'code':'table_caption_number_mismatch'})
            jc=prev.find('w:pPr/w:jc',NS);ind=prev.find('w:pPr/w:ind',NS)
            if jc is None or jc.get(qn('val'))!='center' or ind is None or any(ind.get(qn(k),'0')!='0' for k in ('firstLine','firstLineChars','left','right','hanging','hangingChars')):issues.append({'table':table_count,'code':'table_caption_alignment'})
            if not _on(prev.find('w:pPr/w:keepNext',NS)):issues.append({'table':table_count,'code':'table_caption_can_orphan'})
            captions.append({'table':table_count,'body_index':previous[0],'text':node_text(prev)})
        if n.tag!=qn('p') or field is None or i<field:continue
        value=compact(node_text(n))
        if value in BENEFIT_LABELS or OLD_INTRO.fullmatch(value):issues.append({'body_index':i,'code':'extra_benefit_heading_or_intro'})
        if value==BENEFIT_INTRO:intro.append(i)
        if value not in MAIN_HEADINGS and value!=compact(title or ''):
            if any(node_text(r).strip() and is_bold(n,r) for r in n.findall('.//w:r',NS)):issues.append({'body_index':i,'code':'non_main_text_bold','text':node_text(n)[:90]})
            style=n.find('w:pPr/w:pStyle',NS);sid=style.get(qn('val'),'') if style is not None else ''
            outline=n.find('w:pPr/w:outlineLvl',NS)
            if re.fullmatch(r'Heading\d+',sid,re.I) or outline is not None and int(outline.get(qn('val'),'9'))<9:issues.append({'body_index':i,'code':'extra_outline_heading','text':node_text(n)[:90]})
            if value in ('制备工艺','制备工艺：') or CAPTION.fullmatch(value):labels.append({'body_index':i,'text':node_text(n),'format':'plain'})
    if len(intro)>1:issues.append({'code':'duplicate_benefit_introductions','body_indices':intro})
    descriptions=[]
    for i,p,ending in figure_description_entries(root):
        value=node_text(p).rstrip();descriptions.append({'body_index':i,'text':value,'expected_ending':ending})
        if not value.endswith(ending):
            issues.append({'code':'figure_description_terminal_not_full_stop' if ending=='。' else 'figure_description_terminal_not_semicolon',
                           'body_index':i,'text':value,'expected_ending':ending})
    # Geometry is role-specific. Tables and tall rich objects retain their own
    # layout checks; abstract/claims and figure appendix are outside this span.
    end=next((i for i in range(field or 0,len(nodes)) if nodes[i].find('w:pPr/w:sectPr',NS) is not None),len(nodes)-1)
    definitions={s.get(qn('styleId')):s for s in styles.findall('w:style',NS)} if styles is not None else {}
    def prop(p,name):
        # OOXML paragraph properties inherit individual attributes. A direct
        # right=0 does not discard firstLineChars from the paragraph style.
        values={}
        default=styles.find('w:docDefaults/w:pPrDefault/w:pPr/w:'+name,NS) if styles is not None else None
        if default is not None:values.update(default.attrib);values.setdefault(qn('val'),'1')
        sid=p.find('w:pPr/w:pStyle',NS);sid=sid.get(qn('val')) if sid is not None else 'Normal';seen=set()
        inherited=[]
        while sid and sid not in seen:
            seen.add(sid);style=definitions.get(sid)
            if style is None:break
            item=style.find('w:pPr/w:'+name,NS)
            if item is not None:inherited.append(item)
            base=style.find('w:basedOn',NS);sid=base.get(qn('val')) if base is not None else None
        for item in reversed(inherited):
            values.update(item.attrib)
            if name in ('keepNext','keepLines','pageBreakBefore','widowControl'):values[qn('val')]=item.get(qn('val'),'1')
        direct=p.find('w:pPr/w:'+name,NS)
        if direct is not None:
            values.update(direct.attrib)
            if name in ('keepNext','keepLines','pageBreakBefore','widowControl'):values[qn('val')]=direct.get(qn('val'),'1')
        return values
    if field is not None:
        for i in range(field,end+1):
            n=nodes[i];value=compact(node_text(n))
            if (n.tag!=qn('p') or not value or value in MAIN_HEADINGS or value==compact(title or '') or CAPTION.fullmatch(value)
                or any(n.find('.//'+tag,NS) is not None for tag in ('m:oMath','w:drawing','w:pict','w:object'))):continue
            spacing=prop(n,'spacing');indent=prop(n,'ind')
            if spacing.get(qn('lineRule'),'auto')!='auto' or spacing.get(qn('line'))!='312':
                issues.append({'body_index':i,'code':'description_body_line_spacing'})
            if (spacing.get(qn('before'),'0')!='100' or spacing.get(qn('after'),'0')!='0' or
                any(spacing.get(qn(k),'0') not in ('0','false','off') for k in ('beforeAutospacing','afterAutospacing')) or
                not (indent.get(qn('firstLineChars'))=='200' or qn('firstLineChars') not in indent and indent.get(qn('firstLine'))=='480') or
                any(indent.get(qn(k),'0')!='0' for k in ('left','right','leftChars','rightChars','start','end','startChars','endChars','hanging','hangingChars'))):
                issues.append({'body_index':i,'code':'description_body_paragraph_geometry'})
    flow_checked=[]
    figure_entries={entry['body_index'] for entry in descriptions}
    def prose(i):
        n=nodes[i];value=compact(node_text(n))
        return (n.tag==qn('p') and bool(value) and value not in MAIN_HEADINGS
                and value!=compact(title or '') and not CAPTION.fullmatch(value)
                and i not in figure_entries and value not in ('制备工艺','配方','测试方法','结果分析') and not value.endswith(('：',':'))
                and value!=BENEFIT_INTRO)
    if field is not None:
        for i in range(field,end+1):
            n=nodes[i]
            if n.tag!=qn('p'):continue
            breaks=prose_breaks(n)
            if breaks or any('\n' in (t.text or '') or '\r' in (t.text or '') for t in n.iter(qn('t'))):
                issues.append({'body_index':i,'code':'description_manual_break','types':[x[1] for x in breaks]})
            if not prose(i):continue
            # Inline math is allowed to flow with the sentence. Standalone
            # pictures/equations keep their separate object-specific layout.
            if any(n.find('.//'+tag,NS) is not None for tag in ('w:drawing','w:pict','w:object','m:oMathPara')):continue
            flow_checked.append(i)
            for name in ('keepNext','keepLines','pageBreakBefore','widowControl'):
                if prop(n,name).get(qn('val'),'0') not in ('0','false','off'):
                    issues.append({'body_index':i,'code':'description_prose_forced_pagination','property':name})
            # Suspected split paragraphs require source review; never merge
            # across a table, heading, section or a new numbered step by guess.
            j=i+1
            while (j<=end and nodes[j].tag==qn('p') and not compact(node_text(nodes[j]))
                   and not any(nodes[j].find('.//'+tag,NS) is not None for tag in ('w:sectPr','w:drawing','w:pict','w:object','m:oMath'))):
                j+=1
            if (j<=end and n.find('w:pPr/w:sectPr',NS) is None
                and compact(node_text(n)).endswith(('，',',','、')) and prose(j)
                and not FLOW_BOUNDARY.match(compact(node_text(nodes[j])))):
                issues.append({'body_index':i,'next_body_index':j,'code':'description_prose_split_after_comma'})
    examples=example_entries([{'text':node_text(n),'kind':'p' if n.tag==qn('p') else 'tbl','location':i} for i,n in enumerate(nodes)])
    for row in examples:
        if row['split']:issues.append({'code':'example_introduction_split','key':row['key']})
    return {'schema_version':1,'artifact_sha256':artifact_sha,'complete':True,'examples_contract_version':1,'prose_flow_contract_version':1,'prose_flow_checked_body_indices':flow_checked,'examples':examples,'tables':table_count,'captions':captions,'benefit_intro_body_indices':intro,'plain_labels':labels,'figure_descriptions':descriptions,'issues':issues,'scope':'Source caption meanings, preserved technical facts, allowed headings and actual page pairing require independent semantic/visual review; screenshot annotations are not document elements'}
