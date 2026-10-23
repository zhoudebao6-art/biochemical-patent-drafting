"""Biochemical normative precheck over the v6.37 read-only OOXML inventory."""
import re

def precheck(result,kind):
    import inspect_docx as core
    body=next(p for p in result['parts'] if p['part']=='word/document.xml')['paragraphs']
    result['domain']='biochemical'
    result['antecedent_occurrences']=core.antecedent_occurrences(result['parts'])
    result['formula_count_status']='unclassified_math_objects_not_source_formula_count'
    result['punctuation_evidence']['scope']='Chemical brackets/nomenclature punctuation retained; final visible-content spaces are prohibited by user rule BIO-21.'
    result['content_spacing_evidence']['scope']='Raw source locations retained; final output requires zero literal visible spaces without changing source facts.'
    result['formula_prose_evidence']['scope']='Raw structural candidates only; no forced single-occurrence, English-symbol substitution, or upright normalization for chemical objects.'
    def add(code,message,loc=None): result['issues'].append({'code':code,'message':message,'locator':loc,'status':'needs_review'})
    if any(any(p['revisions'].values()) for p in result['parts']): add('REVISIONS','Tracked changes require intended-version review')
    for part in result['parts']:
        for p in part['paragraphs']:
            for ref in p['media']:
                if ref.get('missing_relationship'): add('MISSING_REL','Missing source media relationship',f"{part['part']} P{p['p']}")
            if p['font_encoded_symbols']:add('FONT_SYMBOL','Verify original displayed glyphs',f"{part['part']} P{p['p']}")
    if result['embeddings']:add('EMBEDDED_OBJECTS','Preserve and visually verify OLE and preview; text extraction is incomplete')
    if not result['formulas']:add('NO_OMML','Zero native math does not exclude text/image/OLE formulas or chemical superscripts')
    if kind=='proposal':
        for h in ['技术概括','工作原理','产品背景','技术效果','实施方案','参考图示']:
            if not any(p['text'].strip().rstrip('：:')==h for p in body):add('BIO_SOURCE_SECTION','Source heading unresolved: '+h)
        return
    from bio_layout import analysis_evidence
    result['biochemical_analysis_evidence']=analysis_evidence(body,result['sha256'])
    for key in ('biochemical_table_evidence','biochemical_analysis_evidence','biochemical_presentation_evidence','biochemical_background_evidence','biochemical_native_scripts_evidence'):
        ev=result.get(key,{})
        if ev.get('artifact_sha256')!=result['sha256'] or ev.get('complete') is not True:add('BIO_LAYOUT_EVIDENCE','Missing/current layout scan required: '+key)
        for issue in ev.get('issues',[]):add('BIO_LAYOUT',issue.get('code','page_fill_shading_or_highlight'),str(issue))
    spacing=result.get('biochemical_spacing_evidence')
    if not spacing or spacing.get('artifact_sha256')!=result['sha256'] or spacing.get('complete') is not True:add('BIO_SPACING_EVIDENCE','Missing/current no-space scan required')
    elif spacing['hits']:add('BIO_CONTENT_SPACE','Visible-content spaces/tabs remain',str(len(spacing['hits'])))
    headings=['技术领域','背景技术','发明内容','附图说明','具体实施方式']
    anchors={h:next((p['p'] for p in body if p['text'].strip()==h),None) for h in headings}
    for h,n in anchors.items():
        if n is None:add('DRAFT_SECTION','Missing description heading: '+h)
    field=anchors['技术领域'] or len(body)+1
    claim_ps={p['p'] for p in body if any('权利要求书' in re.sub(r'\s+','',h) for h in p.get('section_headers',[]))}
    claims=[]
    for p in body:
        if p['p']>=field:break
        if claim_ps and p['p'] not in claim_ps:continue
        mt=re.match(r'^\s*(\d+)、(.*)',p['text'])
        breaks=int('break_or_tab' in p.get('content_evidence',{}).get('objects',[]))
        if mt:claims.append({'number':int(mt[1]),'p':p['p'],'text':p['text'],'paragraphs':[p['p']],'paragraph_texts':[p['text']],'manual_breaks':breaks})
        elif claims and (p['text'].strip() or breaks):
            claims[-1]['text']+='\n'+p['text'];claims[-1]['paragraphs'].append(p['p']);claims[-1]['paragraph_texts'].append(p['text'])
            claims[-1]['manual_breaks']+=breaks
    nums=[c['number'] for c in claims]
    if nums!=list(range(1,len(nums)+1)) or not nums:add('CLAIM_NUMBERS','Claims absent or not contiguous')
    for c in claims:
        head=c['text'].split('其特征在于')[0];refs,parents,issues=core.parse_parent_references(head)
        c.update(parents_detected=parents,parent_reference_texts=refs,parent_parse_issues=issues,parent_parse_status='structural_only_requires_semantic_dependency_review')
        c['antecedent_count_evidence']={'literal_count':c['text'].count('所述'),'required_valid_minimum':None,'status':'verify_complete_noun_and_actual_ancestor_chain_no_count_threshold'}
        if any(n<1 or n>=c['number'] or n not in nums for n in parents):add('CLAIM_REFERENCE','Invalid future/self/missing parent',f"P{c['p']}")
        if '，其特征在于，' not in c['text'].split('\n')[0]:add('BIO_CLAIM_WORDING','Use exact fixed claim head punctuation',f"P{c['p']}")
    from bio_claims import analyze
    structure=analyze(claims)
    structure['artifact_sha256']=result['sha256']
    result['biochemical_claims_evidence']=structure
    for issue in structure['issues']:add('BIO_CLAIMS_STRUCTURE',issue)
    by_number={c['number']:c for c in structure['claims']}
    for claim in claims:
        if claim['number'] in by_number:
            item=by_number[claim['number']]
            claim.update(kind=item['kind'],group=item['group'],object=item['object'],
                         parents_detected=item['parents'],object_references=item['reference_claims'],
                         inheritance_paths=item['inheritance_paths'],own_limitations=item['own_limitations'])
            claim['paragraph_layout']=item['paragraph_layout']
    result['claims_detected']=claims
    contract=core.document_contract_evidence(body)
    contract['global_word_hits']=[];contract['description_word_hits']=[]
    result['document_contract_evidence']=contract
    result['wording_evidence']={'occurrences':[],'scope':'Only biochemical self-reference and claims-only feature phrase apply'}
    claim_positions={p for c in claims for p in c['paragraphs']}
    alltexts=[{'part':part['part'],'p':p['p'],'text':p['text']} for part in result['parts'] for p in part['paragraphs']]
    hits=[]
    for p in alltexts:
        for old in ['本产品','本方案','本技术']:
            if old in p['text']:hits.append(dict(p,word=old))
        if '其特征在于' in p['text'] and (p['part']!='word/document.xml' or p['p'] not in claim_positions):hits.append(dict(p,word='其特征在于'))
    result['biochemical_evidence']={'schema_version':1,'artifact_sha256':result['sha256'],'headings':anchors,'wording_hits':hits,'claim_count':len(claims),'scope':'Source facts, chemistry, table cells and all figures remain independent semantic review'}
    for hit in hits:add('BIO_WORDING','Unnormalized self-reference or feature phrase outside claims',f"{hit['part']} P{hit['p']}: {hit['word']}")
    if anchors['技术领域']:
        fieldtext=next((p['text'] for p in body if p['p']>field and p['text'].strip()),'')
        abstract=next((p['text'] for p in body if p['text'].strip()),'');first=abstract.split('。')[0]+'。'
        if fieldtext.strip()!=first.strip():add('FIELD_ABSTRACT','Technical field must match complete abstract first sentence')
    result['page_flow_evidence']=core.page_flow_evidence(result,body,claims)
    result['figure_placement_evidence']={'image_occurrences':[{'paragraph':p['p'],'section_headers':p.get('section_headers',[]),'media':p['media']} for p in body if p['media']],'boundary':'Verify all actual figures, main figure identity and captions visually, not only flowcharts'}
