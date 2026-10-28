"""Shared claim boundaries, object families and source-bound plan checks.

This is structural evidence, never a semantic decision about protection scope.
"""
import re

FEATURE = '，其特征在于，'
LEAD = re.compile(r'^进一步地[，,]在上述技术方案中[，,]')
OTHER = re.compile(r'^本(?:方案|发明|技术)还提供(?:了)?')
PRIMARY = re.compile(r'^为了解决上述(?:技术)?问题[，,].*?提供(?:了)?')
EXPLAIN = re.compile(r'^(?:具体实施中|针对现有技术中|原理说明|工作原理)')
REF = re.compile(r'权利要求(\d+(?:(?:至|到|[-—–~～、,，或和及])\d+)*)((?:中)?任(?:意)?一项)?所述的?')


def compact(value):
    # Only explicit script glyphs, whitespace and the user's self-reference edits.
    from bio_scripts import MAP as GLYPHS
    value = ''.join(GLYPHS[c][0] if c in GLYPHS else c for c in value)
    for old in ('本方案', '本产品', '本技术'):
        value = value.replace(old, '本发明')
    return re.sub(r'\s+', '', value)


def object_key(value):
    return re.sub(r'^(?:一种)?(?:所述的?)?', '', compact(value))


def candidates(rows):
    """Keep every continuation and explanation locator; do not choose a parent."""
    result = []; active = None; section = None; group = None
    headings = {'技术概括','工作原理','原理说明','产品背景','技术效果','实施方案','参考图示','参考文献','反应文献支撑'}
    for row in rows:
        t = row.get('text', ''); clean = t.strip(); idx = row.get('body_index', row.get('p'))
        if clean.rstrip('：:') in headings:
            section = clean.rstrip('：:'); active = None; continue
        if section not in ('工作原理', '原理说明'):
            continue
        lead = LEAD.match(clean); main = PRIMARY.match(clean); other = OTHER.match(clean)
        if lead or main or other:
            typ = 'dependent' if lead else ('additional_independent' if other else 'independent')
            number = len(result) + 1
            if not lead: group = number
            offset = len(t) - len(t.lstrip())
            feature = t.find(FEATURE)
            start = offset + lead.end() if lead else (feature + len(FEATURE) if feature >= 0 else None)
            active = {'candidate':number,'body_index':idx,'type':typ,'text':t,
                      'source_body_indices':[idx],'segments':[{'body_index':idx,'start':start,'end':len(t)}],
                      'group_candidate':group,'explanation_body_indices':[],
                      'parent':None,'object':None,'status':'needs_semantic_mapping'}
            if not lead and feature >= 0:
                active['source_object'] = t[offset + (main or other).end():feature].strip()
            elif lead and group:
                active['source_object'] = result[group-1].get('source_object')
            result.append(active)
        elif EXPLAIN.match(clean):
            if result: result[-1]['explanation_body_indices'].append(idx)
            active = None
        elif clean and active is not None:
            active['source_body_indices'].append(idx)
            active['segments'].append({'body_index':idx,'start':0,'end':len(t)})
            active['text'] += '\n' + t
        elif clean and result:
            result[-1]['explanation_body_indices'].append(idx)
    return result


def collect(paragraphs):
    claims = []
    for p in paragraphs:
        t = p.get('text', ''); hit = re.match(r'^\s*(\d+)、', t)
        if hit:
            claims.append({'number':int(hit[1]),'text':t,'paragraphs':[p.get('p')],
                           'paragraph_texts':[t], 'manual_breaks':p.get('manual_breaks',0), 'p':p.get('p')})
        elif claims and (t.strip() or p.get('manual_breaks')):
            claims[-1]['text'] += '\n' + t
            claims[-1]['paragraphs'].append(p.get('p'))
            claims[-1]['paragraph_texts'].append(t)
            claims[-1]['manual_breaks']+=p.get('manual_breaks',0)
    return claims


def top_semicolons(value):
    """Do not cut a parenthesized chemical expression or a nested condition."""
    stack=[];pairs={')':'(',']':'[','}':'{','）':'（','】':'【','〕':'〔'}
    for i,ch in enumerate(value):
        if ch in pairs.values():stack.append(ch)
        elif ch in pairs:
            if stack and stack[-1]==pairs[ch]:stack.pop()
        elif ch=='；' and not stack:yield i


def paragraph_spans(value, kind):
    """Layout only: never infer a parent, invent steps or rewrite a limitation.

    Numbered methods split at explicit S labels; their internal semicolons stay.
    Unnumbered methods use top-level operation separators. Dependent items stay
    one paragraph even when their limitation contains a preparation procedure.
    """
    if kind!='independent' or FEATURE not in value:return [(0,len(value))]
    start=value.index(FEATURE)+len(FEATURE)
    intro=re.match(r'包括(?:以下|如下)步骤[：:]',value[start:])
    if not intro:return [(0,len(value))]
    start+=intro.end();cuts=[0,start]
    separators=list(top_semicolons(value[start:]))
    boundaries=[start+i+1 for i in separators]
    numbered=re.match(r'\s*S\d+[、，,:：.]',value[start:])
    for pos in boundaries:
        tail=value[pos:]
        if not tail.strip():continue
        if not numbered or re.match(r'\s*S\d+[、，,:：.]',tail):cuts.append(pos)
    cuts=sorted(set(cuts+[len(value)]))
    return [(a,b) for a,b in zip(cuts,cuts[1:]) if value[a:b].strip()]


def paragraph_check(claim,kind):
    actual=claim.get('paragraph_texts',claim['text'].split('\n'))
    flat=''.join(claim['text'].split('\n'))
    expected=[flat[a:b] for a,b in paragraph_spans(flat,kind)]
    valid=[compact(t) for t in actual]==[compact(t) for t in expected]
    # A manual line break inside one w:p is not a natural paragraph boundary.
    if claim.get('manual_breaks') or any('\n' in t or '\r' in t for t in actual):valid=False
    return {'actual_count':len(actual),'expected_count':len(expected),
            'manual_breaks':claim.get('manual_breaks',0),'valid':valid}


def references(head):
    result = []; errors = []
    for m in REF.finditer(compact(head)):
        expr = m[1]; nums = []
        for token in re.split(r'[、,，或和及]', expr):
            ends = re.split(r'至|到|[-—–~～]', token)
            if len(ends) == 1: nums.append(int(ends[0]))
            elif len(ends) == 2 and 0 < int(ends[0]) <= int(ends[1]) <= 10000:
                nums.extend(range(int(ends[0]), int(ends[1]) + 1))
            else: errors.append('Invalid reference range: ' + token)
        result.append({'text':m[0],'numbers':nums,'alternative':bool(m[2]),'start':m.start(),'end':m.end()})
    if compact(head).count('权利要求') != len(result): errors.append('Unresolved claim reference')
    numbers=[n for r in result for n in r['numbers']]
    if len(numbers)!=len(set(numbers)): errors.append('Duplicate claim reference')
    return result, errors


def related_object_claims(obj, previous):
    """Exact named object links only; never infer a scope from title keywords."""
    key=object_key(obj)
    for suffix in ('的应用','的用途','的制备方法'):
        if key.endswith(suffix):
            target=key[:-len(suffix)]
            return [n for n,item in previous.items() if object_key(item['object'])==target]
    return []


def independent_reference_head(obj, numbers, number):
    """Assemble fixed wording from explicit decisions; never choose references."""
    if (type(number) is not int or not isinstance(numbers,list) or not numbers
            or any(type(n) is not int or not 0<n<number for n in numbers)
            or numbers!=sorted(set(numbers))):
        raise ValueError('Explicit ordered distinct prior reference_claims required')
    name=object_key(obj)
    if not name or '权利要求' in name or '其特征在于' in name:
        raise ValueError('Complete plain protection object required')
    if len(numbers)>1 and numbers==list(range(numbers[0],numbers[-1]+1)):
        expr=f'{numbers[0]}-{numbers[-1]}'
    else:
        expr='、'.join(map(str,numbers))
    return '一种根据权利要求'+expr+('任意一项' if len(numbers)>1 else '')+'所述'+name


def expected_head(c):
    if c.get('head'): return c['head']
    if c.get('reference_claims') and c.get('parent') is None and not c.get('parents'):
        return independent_reference_head(c['object'],c['reference_claims'],c['number'])
    return (f"根据权利要求{c['parent']}所述的" if c.get('parent') is not None else '') + c['object']


def analyze(claims, mapping=None):
    errors = []; rows = []; by_number = {}
    numbers = [c['number'] for c in claims]
    if not numbers or numbers != list(range(1, len(numbers)+1)): errors.append('Claim numbering not contiguous')
    if mapping is not None and [c.get('number') for c in mapping] != numbers: errors.append('Claim count/number differs from plan')
    plans = {c['number']:c for c in mapping or []}
    for claim in claims:
        n = claim['number']; first = claim['text'].split('\n')[0]; raw = re.sub(r'^\s*\d+、', '', first)
        if FEATURE not in raw:
            errors.append(f'Claim {n} fixed wording invalid'); continue
        error_start=len(errors)
        head = raw.split(FEATURE)[0]; refs, issues = references(head); errors.extend(issues)
        referenced = sorted({i for r in refs for i in r['numbers']})
        if any(i < 1 or i >= n or i not in numbers for i in referenced): errors.append(f'Invalid claim parent/reference {n}')
        # This fixed leading grammar declares a dependent claim. A wrong object
        # must be reported, not silently reclassified as a new independent item.
        dependent_head = re.match(r'^根据' + REF.pattern, compact(head))
        obj = compact(head)[dependent_head.end():] if dependent_head else compact(head)
        kind = 'dependent' if dependent_head else 'independent'
        if dependent_head and (not referenced or any(object_key(obj)!=object_key(by_number.get(i,{}).get('object','')) for i in referenced)):
            errors.append(f'Dependent protection object differs from parent {n}')
        if kind == 'independent':
            obj = REF.sub('', compact(head)).replace('根据','').replace('所述的','')
        if kind == 'independent':
            if referenced and not re.match(r'^一种根据' + REF.pattern, compact(head)):
                errors.append(f'Independent reference head requires complete fixed prefix 一种根据权利要求 {n}')
            if not object_key(obj):
                errors.append(f'Independent reference head requires complete protection object {n}')
            related=related_object_claims(obj,by_number)
            # User drafting convention: every independent item after the first
            # needs an explicit earlier reference, irrespective of its category.
            # The author/reviewer chooses the supported technical relationship.
            if any(item['kind']=='independent' for item in rows) and not referenced:
                errors.append(f'Later independent claim must reference prior claims {n}')
            if related and referenced and not set(referenced).issubset(related):
                errors.append(f'Independent object reference crosses a different object family {n}')
            if len(referenced)>1 and not all(r['alternative'] for r in refs):
                errors.append(f'Multiple independent object references need alternative wording {n}')
        parents = referenced if kind == 'dependent' else []
        group = by_number.get(parents[0],{}).get('group') if parents else n
        if parents and any(by_number.get(i,{}).get('group') != group for i in parents): errors.append(f'Cross-family dependent claim {n}')
        if parents and len(parents)>1 and not all(r['alternative'] for r in refs): errors.append(f'Multiple parents need alternative wording {n}')
        if not claim['text'].rstrip().endswith('。'): errors.append(f'Claim {n} must end with a full stop')
        layout=paragraph_check(claim,kind)
        if not layout['valid']:errors.append(f'Claim {n} paragraph layout differs: independent lead/steps or single dependent paragraph required')
        p = plans.get(n)
        if p:
            if compact(head) != compact(expected_head(p)): errors.append(f'Claim object/dependency mismatch {n}')
            wanted = p.get('kind', 'dependent' if p.get('parent') is not None or p.get('parents') else 'independent')
            pparents = p.get('parents', [p['parent']] if p.get('parent') is not None else [])
            if wanted not in ('dependent','independent') or wanted != kind: errors.append(f'Claim kind/object mismatch {n}')
            if pparents != parents: errors.append(f'Claim parent mismatch {n}')
            if wanted == 'independent' and p.get('reference_claims',[]) != referenced: errors.append(f'Independent object references must be explicit {n}')
            if p.get('group', group) != group: errors.append(f'Claim group mismatch {n}')
            if not p.get('object') or not p.get('source_body_indices'): errors.append(f'Claim source/object missing {n}')
            if parents and not p.get('dependency_reason'): errors.append(f'Semantic dependency reason required {n}')
            # Remove the reference grammar for an independently referenced object.
            plain = REF.sub('', compact(head)).replace('根据','').replace('所述的','')
            if wanted == 'independent' and object_key(plain) != object_key(p['object']): errors.append(f'Independent protection object mismatch {n}')
        paths = [[n]+path for i in parents if i in by_number
                 for path in by_number[i]['inheritance_paths']] if parents else [[n]]
        row = {'number':n,'head':head,'object':obj,'kind':kind,'group':group,
               'parents':parents,'reference_claims':referenced if not parents else [],
               'references':refs,'text':claim['text'],'inheritance_paths':paths,
               'paragraph_layout':layout,
               'own_limitations':claim['text'].split(FEATURE,1)[-1]}
        if kind=='independent' and any(item['kind']=='independent' for item in rows):
            row['reference_head_check']={'required':True,'complete':not errors[error_start:],
                'reference_claims':referenced,'object':obj,'issues':errors[error_start:],
                'scope':'Full fixed wording and explicit range; source object and technical relationship still require source-bound review.'}
        rows.append(row); by_number[n] = row
    return {'schema_version':1,'complete':True,'claims':rows,'independent_count':sum(r['kind']=='independent' for r in rows),
            'issues':errors,'scope':'Structural evidence; protected objects, combined restrictions and antecedents require semantic review'}


def dependency_check(claims, mapping, evidence):
    """Verify declared inherited limitations against source and actual paths.

    The author identifies the technical needs; this check never infers them from
    noun occurrence, proximity, or sample numbering. Every alternative is separate.
    """
    structure=analyze(claims);actual={c['number']:c for c in structure['claims']}
    plans={c['number']:c for c in mapping};source={r['body_index']:r for r in evidence['body']}
    errors=[];records=[]
    for n,item in actual.items():
        if item['kind']!='dependent':continue
        plan=plans.get(n,{});basis=plan.get('dependency_basis')
        if not isinstance(basis,list) or not basis:
            errors.append(f'Claim {n} needs source-bound dependency_basis, not only a reason');continue
        valid=[]
        for b in basis:
            if not isinstance(b,dict):errors.append(f'Invalid dependency basis {n}');continue
            required=b.get('claim');loc=b.get('body_index');quote=b.get('quote');current=b.get('current_quote');via=b.get('via')
            if type(required) is not int or required not in actual or not 0<required<n or (via is not None and via not in item['parents']):
                errors.append(f'Invalid required claim/via in dependency basis {n}');continue
            if type(loc) is not int or loc not in plans.get(required,{}).get('source_body_indices',[]) or loc not in source or not isinstance(quote,str) or not quote.strip() or quote not in source[loc]['text']:
                errors.append(f'Invalid source-bound inherited quote {n}');continue
            if compact(quote) not in compact(actual[required]['own_limitations']):
                errors.append(f'Inherited quote is not a limitation of claim {required} for {n}');continue
            if not isinstance(current,str) or not current.strip() or compact(current) not in compact(item['own_limitations']):
                errors.append(f'Current refinement quote missing from claim {n}');continue
            valid.append(b)
        paths=item['inheritance_paths'];branches=[]
        for path in paths:
            parent=path[1];relevant=[b for b in valid if b.get('via') in (None,parent)]
            required={b['claim'] for b in relevant}
            missing=sorted(required-set(path[1:]))
            if not relevant:errors.append(f'Claim {n} branch via {parent} lacks dependency basis')
            if missing:errors.append(f'Claim {n} branch {path} does not inherit required claims {missing}')
            branches.append({'path':path,'required_claims':sorted(required),'missing':missing,
                'inherited_limitations':[{'claim':i,'text':actual[i]['own_limitations']} for i in path[1:]]})
            # Apply the same test to EVERY actual branch, including an alternative
            # inherited through another dependent item. Never union branch needs.
            if relevant and not missing:
                for offset in range(2,len(path)):
                    if required<=set(path[offset:]):
                        errors.append(f'Claim {n} has unexplained extra inheritance via {parent} on {path}; declared needs already covered by claim {path[offset]}')
                        break
        records.append({'number':n,'parents':item['parents'],'dependency_reason':plan.get('dependency_reason'),
                        'basis':valid,'branches':branches,'semantic_review_required':True,
                        'review_scope':'Verify the chosen needs, all inherited ranges/conditions and unwanted restrictions; noun-first-use wording is a separate check.'})
    return {'schema_version':1,'records':records,'issues':errors,
            'scope':'Source and path consistency of declared needs; not autonomous technical parent selection or semantic acceptance.'}


def source_check(claims, mapping, evidence):
    """Compare complete selected source limitations, not just claim headers/counts."""
    errors = []; rows = {r['body_index']:r for r in evidence['body']}
    cs = candidates(evidence['body']); covered = []; records = []
    actual = {c['number']:c for c in claims}
    structure={c['number']:c for c in analyze(claims)['claims']}
    for p in mapping:
        n = p['number']; ids = p.get('source_body_indices',[])
        if any(type(i) is not int or i not in rows for i in ids):
            errors.append(f'Invalid source locator {n}'); continue
        chosen = [c for c in cs if c['body_index'] in ids]
        if len(chosen)!=1:
            errors.append(f'Claim {n} needs exactly one complete source candidate; inspect boundaries'); continue
        c = chosen[0]; covered.append(c['candidate'])
        source_object=c.get('source_object')
        if not source_object or object_key(p.get('object',''))!=object_key(source_object):
            errors.append(f'Claim {n} protection object differs from source group')
        if structure.get(n,{}).get('group')!=c['group_candidate']:
            errors.append(f'Claim {n} actual object group differs from source group')
        if not set(c['source_body_indices']).issubset(ids): errors.append(f'Missing continuation locator {n}')
        if any(s['start'] is None for s in c['segments']):
            errors.append(f'Unresolved source feature boundary {n}'); continue
        expected = ''.join(rows[s['body_index']]['text'][s['start']:s['end']] for s in c['segments'])
        edits = p.get('source_text_edits',[])
        for edit in edits:
            old = edit.get('old'); new = edit.get('new')
            if not old or not isinstance(new,str) or not new or not edit.get('reason') or expected.count(old)!=1:
                errors.append(f'Unresolved explicit source wording edit {n}'); continue
            if re.findall(r'\d+(?:\.\d+)?',compact(old)) != re.findall(r'\d+(?:\.\d+)?',compact(new)):
                errors.append(f'Source wording edit changes numeric limitations {n}'); continue
            # Preserve numeric notation, attached units and chemical letter tokens.
            # This is a guard, not proof that a Chinese wording edit is equivalent.
            tokens=lambda t:re.findall(r'[A-Za-z0-9µμΩ°℃%‰]+(?:[./·^+−-][A-Za-z0-9µμΩ°℃%‰]+)*',compact(t))
            if tokens(old)!=tokens(new):
                errors.append(f'Source wording edit changes unit/chemical tokens {n}');continue
            expected = expected.replace(old,new,1)
        body = actual.get(n,{}).get('text','').split(FEATURE,1)[-1]
        # Only the attested independent final-condition transition is implicit.
        # Other wording changes need an explicit, independently reviewed edit.
        wanted = p.get('kind','dependent' if p.get('parent') is not None or p.get('parents') else 'independent')
        expected_norm=compact(expected);body_norm=compact(body)
        tail_transition=False
        if wanted=='independent' and expected_norm!=body_norm:
            cuts=list(top_semicolons(expected_norm))
            if cuts:
                pos=cuts[-1]+1
                tail_transition=body_norm==expected_norm[:pos]+'其中，'+expected_norm[pos:]
        if expected_norm!=body_norm and not tail_transition: errors.append(f'Claim {n} source limitations changed/missing/duplicated')
        wanted = p.get('kind','dependent' if p.get('parent') is not None or p.get('parents') else 'independent')
        if (c['type']=='dependent') != (wanted=='dependent'): errors.append(f'Claim {n} source object boundary mismatch')
        records.append({'number':n,'candidate':c['candidate'],'source_body_indices':c['source_body_indices'],
                        'source_object':source_object,'source_group':c['group_candidate'],
                        'final_condition_transition':tail_transition,
                        'explicit_wording_edits':edits,'semantic_review_required':True})
    if sorted(covered)!=list(range(1,len(cs)+1)): errors.append('Source claim candidates missing/duplicated; do not add or omit objects to fit a count')
    elif covered!=list(range(1,len(cs)+1)):errors.append('Source claim candidate order changed; retain the supplied technical sequence')
    dependencies=dependency_check(claims,mapping,evidence);errors.extend(dependencies['issues'])
    return {'schema_version':1,'source_sha256':evidence['source']['sha256'],'records':records,'issues':errors,'dependencies':dependencies,
            'scope':'Full candidate text comparison; explicit wording edits remain unaccepted until independent review'}


def validate_plan(claims, plan, evidence):
    structural = analyze(claims,plan['claim_map']); source = source_check(claims,plan['claim_map'],evidence)
    errors = structural['issues'] + source['issues']
    if errors: raise ValueError('Biochemical claim plan: ' + '; '.join(errors))
    return {'structure':structural,'source':source}
