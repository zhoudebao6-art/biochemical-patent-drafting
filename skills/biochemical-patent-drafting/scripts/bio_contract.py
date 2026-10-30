"""Final biochemical mechanical checks on an already sealed v6.37 inspection."""
import re
import batch_tool as b
def check(report,title,findings=(),source_reports=None,require_example_sources=False):
    spacing=report.get('biochemical_spacing_evidence',{})
    if spacing.get('schema_version')!=1 or spacing.get('complete') is not True or spacing.get('artifact_sha256')!=report.get('sha256') or spacing.get('hits'):
        raise b.BatchError('Biochemical no-space evidence missing, stale or contains visible-content spaces')
    for key in ('biochemical_table_evidence','biochemical_analysis_evidence','biochemical_presentation_evidence','biochemical_background_evidence','biochemical_native_scripts_evidence','biochemical_claims_evidence'):
        ev=report.get(key,{})
        if ev.get('schema_version')!=1 or ev.get('complete') is not True or ev.get('artifact_sha256')!=report.get('sha256') or ev.get('issues'):
            raise b.BatchError('Biochemical format evidence missing, stale or has layout issues: '+key)
    presentation=report['biochemical_presentation_evidence']
    if report['biochemical_table_evidence'].get('width_contract_version')!=1:
        raise b.BatchError('Biochemical table width evidence missing')
    if presentation.get('prose_flow_contract_version')!=1 or not isinstance(presentation.get('prose_flow_checked_body_indices'),list):
        raise b.BatchError('Biochemical continuous prose flow evidence missing')
    if presentation.get('examples_contract_version')!=1 or not isinstance(presentation.get('examples'),list):
        raise b.BatchError('Biochemical example introduction evidence missing')
    if require_example_sources and source_reports is None:
        raise b.BatchError('Verified source reports required for example sentence comparison')
    if source_reports is not None:
        from bio_presentation import source_examples_from_report,compare_examples,compact
        if require_example_sources and not any(compact(p['text']).rstrip('：:')=='实施方案'
                for source in source_reports for part in source['parts'] if part['part']=='word/document.xml'
                for p in part['paragraphs'] if p.get('body_direct',True)):
            raise b.BatchError('Source implementation scope unresolved for example sentence comparison')
        for source in source_reports:
            problems=compare_examples(source_examples_from_report(source),presentation['examples'])
            if problems:raise b.BatchError('Source example introduction changed or missing: '+str(problems))
    c=report.get('document_contract_evidence',{});bio=report.get('biochemical_evidence',{})
    if bio.get('schema_version')!=1 or bio.get('artifact_sha256')!=report.get('sha256'):raise b.BatchError('Missing/stale biochemical inspection')
    if not c.get('description_scope_resolved') or (c.get('title') or {}).get('text')!=title:raise b.BatchError('Biochemical title/scope mismatch')
    if bio['wording_hits']:raise b.BatchError('Biochemical wording contract failed')
    claims=report.get('claims_detected',[])
    if not claims or [x['number'] for x in claims]!=list(range(1,len(claims)+1)):raise b.BatchError('Biochemical claims are not contiguous')
    if any(v is None for v in bio['headings'].values()):raise b.BatchError('Required description heading missing')
    for claim in claims:
        if '，其特征在于，' not in claim['text'].split('\n')[0]:raise b.BatchError('Invalid biochemical claim wording')
        if any(n<1 or n>=claim['number'] for n in claim.get('parents_detected',[])):raise b.BatchError('Invalid biochemical parent reference')
    blocked={'REVISIONS','MISSING_REL','FIELD_ABSTRACT','CLAIM_NUMBERS','DRAFT_SECTION','BIO_WORDING','BIO_CLAIM_WORDING','CLAIM_REFERENCE'}
    if any(i['code'] in blocked for i in report['issues']):raise b.BatchError('Biochemical mechanical precheck contains blocking issues')
    # Chemical brackets, name punctuation and fewer than three
    # 所述 are deliberately legal here. Technical sufficiency is the six-check review.
    return {'mode':'biochemical_v1','artifact_sha256':report['sha256'],'document_title':title,'delivery_filename':title+'.docx','title_paragraph':(c.get('title') or {}).get('paragraph'),'scope':'Biochemical six-check evidence required; no soft-tech wording rules'}
