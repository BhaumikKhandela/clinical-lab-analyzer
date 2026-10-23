"""Independent source/rule verification for the active v2 benchmark.

No network, LLM or application inference. Failure never promotes labels.
"""
import hashlib
import json
import re
import logging
from collections import Counter
from decimal import Decimal
from pathlib import Path

from jsonschema import Draft202012Validator
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'evals/golden/v2'
NAMES = ('extraction','classification','normalization','retrieval',
         'explanations','workflow','chat','judge_calibration')


def read(name):
    return [json.loads(s) for s in (DATA / f'{name}.jsonl').read_text().splitlines()]


def relation(lab):
    try:
        value = Decimal(lab['result'])
        lo, hi = Decimal(str(lab['min_reference'])), Decimal(str(lab['max_reference']))
    except Exception:
        return 'not_comparable'
    return 'below' if value < lo else 'above' if value > hi else 'within'


def check_facts(report, expected):
    for fact in expected.get('required_facts', []):
        source = next(r for r in report if r['test_name'] == fact['test_name'])
        for key, value in fact.items():
            if key == 'relation_to_report_interval':
                assert relation(source) == value
            else:
                assert source[key] == value, (key, source, fact)
    for name in expected.get('absent_tests', []):
        assert name not in {r['test_name'] for r in report}


def verify(require_verified=True, check_manifest=True):
    schema = Draft202012Validator(json.loads((DATA / 'item.schema.json').read_text()))
    datasets = {name: read(name) for name in NAMES}
    for name, items in datasets.items():
        assert items, f'Empty dataset {name}'
        assert len({i['id'] for i in items}) == len(items), name
        for i in items:
            schema.validate(i)
            assert i['metadata']['clinical_review_required'] is False
            assert i['metadata']['evaluation_scope'] == 'software_correctness_only'
            if require_verified:
                assert i['metadata']['label_status'] == 'machine_verified'
            assert not ({'expected_output','verdict','required_facts'} & i['input'].keys())

    for i in datasets['extraction']:
        p = (ROOT / i['input']['fixture_path']).resolve()
        assert p.is_relative_to(ROOT)
        expected = i['expected_output']
        if expected['outcome'] == 'rejected':
            assert expected['labs'] == []
            logger=logging.getLogger('pypdf._reader')
            previous=logger.disabled
            try:
                logger.disabled=True
                PdfReader(p)
            except Exception:
                continue
            finally:
                logger.disabled=previous
            raise AssertionError('Invalid fixture was readable')
        pdf = PdfReader(p)
        text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
        if expected['outcome'] == 'unsupported_without_ocr':
            assert expected['labs'] == []
            assert not text.strip()
            assert pdf.pages[0]['/Resources']['/XObject']
            continue
        if expected['outcome'] == 'incomplete_or_rejected':
            assert text.index('Tail Assay') > 12000
            assert expected['must_disclose_incomplete'] is True
            for r in expected['full_document_labs']:
                line = ' '.join([r['test_name'], r['result'], r['unit'], r['reference_range']])
                assert line in {' '.join(s.split()) for s in text.splitlines()}
            continue
        lines = Counter(' '.join(line.split()) for line in text.splitlines())
        assert expected['row_count'] == len(expected['labs'])
        for r in expected['labs']:
            fields = [r['test_name'], r['result'], r['unit'] or '-']
            if r['reference_range'] is not None:
                fields.append(r['reference_range'])
            elif not i['input']['fixture_path'].startswith('Analyzer Service/'):
                fields.append('(not supplied)')
            line = ' '.join(map(str, fields))
            assert lines[line] > 0, (i['id'], line)
            lines[line] -= 1
            if r['min_reference'] is not None:
                bounds = r['reference_range'].split(' - ')
                assert [Decimal(s) for s in bounds] == [Decimal(str(r['min_reference'])), Decimal(str(r['max_reference']))]
        # Detect omitted authored rows, not just confirm expected rows exist.
        all_lines = text.splitlines()
        start = next(n for n, s in enumerate(all_lines) if 'Test Name' in s or 'Test name' in s) + 1
        table = []
        for s in all_lines[start:]:
            if s.startswith(('Comments:', 'UNTRUSTED NOTE:', 'Assay Y range')):
                break
            if re.match(r'^[A-Za-z].*\s{2,}(?:[<>]?\d|Negative)', s):
                table.append(s)
        assert len(table) == expected['row_count'], (i['id'], 'unaccounted table row')

    policy = json.loads((DATA / 'policy.json').read_text())
    assert policy['applies_to'] == 'Synthetic Assay A only'
    assert (policy['normal_low'],policy['normal_high'],policy['critical_low'],policy['critical_high']) == (10,20,5,25)
    for i in datasets['classification']:
        source = i['input']['lab']
        assert source['test_name'] == 'Synthetic Assay A'
        value = Decimal(source['result'])
        if source['min_reference'] is None:
            label = 'Unknown'
        else:
            lo, hi = Decimal(str(source['min_reference'])), Decimal(str(source['max_reference']))
            half = (hi-lo)/2
            label = 'Critical' if value < lo-half or value > hi+half else 'Warning' if value < lo or value > hi else 'Normal'
        assert i['expected_output']['status'] == label, i['id']

    for i in datasets['normalization']:
        inp, exp = i['input'], i['expected_output']
        if 'alias_contract' in inp:
            assert exp['canonical_test'] == inp['alias_contract'][inp['test_name']]
            continue
        src, dst = inp['observed_unit'], inp['expected_unit']
        assert (src,dst) in {('%','g/dL'),('g/L','g/dL'),('10^9/L','10^3/uL'),('mmol/L','mEq/L')}
        if (src,dst) == ('%','g/dL'):
            assert exp['compatibility'] == 'mismatch' and exp['factor'] is None and exp['converted_value'] is None
            continue
        # Independent SI quantity definitions, in g/L or count/L respectively.
        scales = {'g/L': Decimal('1'), 'g/dL': Decimal('10'),
                  '10^9/L': Decimal('1e9'), '10^3/uL': Decimal('1e9')}
        factor = scales[src]/scales[dst] if src in scales and dst in scales else Decimal('1')
        if src == 'mmol/L':
            assert inp['test_name'] == 'potassium' and dst == 'mEq/L'  # valence +1
        assert factor == Decimal(exp['factor'])
        assert Decimal(inp['value'])*factor == Decimal(exp['converted_value'])
        assert exp['compatibility'] == ('match' if factor == 1 else 'convertible')

    evidence = {e['id']: e for e in json.loads((DATA / 'evidence.json').read_text())}
    for i in datasets['retrieval']:
        inp = i['input']
        relevant = [id for id in inp['candidate_evidence_ids'] if evidence[id]['topic'] == inp['topic']]
        assert i['expected_output']['relevant_evidence_ids'] == relevant
    for i in datasets['explanations']:
        assert set(i['input']['evidence_ids']) <= evidence.keys()
        check_facts([i['input']['lab']], i['expected_output'])
        assert i['expected_output']['permitted_evidence_ids'] == [e for e in i['input']['evidence_ids'] if evidence[e]['topic'] != 'instruction_injection']
    for i in datasets['chat']:
        check_facts(i['input']['report'], i['expected_output'])
    chats = {i['id']: i for i in datasets['chat']}
    assert chats['session-a']['input']['session_key'] != chats['session-b']['input']['session_key']
    assert chats['session-a']['input']['report'] != chats['session-b']['input']['report']

    for i in datasets['workflow']:
        inp, exp = i['input'], i['expected_output']
        assert inp.get('tool_stubs'), 'Workflow needs controlled classifier state'
        if 'summary' in exp:
            status = inp['tool_stubs']['classify_lab_result']['status']
            assert exp['summary'][status.lower()] == 1
            assert ('critical_alert' in exp.get('required_nodes', [])) == (status == 'Critical')
            assert sum(exp['summary'].values()) == 1
            if status == 'Normal':
                assert set(exp['forbidden_calls']) == {'search_clinical_context','get_next_steps'}
                assert exp['forbidden_nodes'] == ['critical_alert']
            else:
                assert set(exp['required_tools']) == {'search_clinical_context','explain_result','get_next_steps'}
        valid = [r for r in inp['labs'] if str(r.get('result','')).strip()]
        failed = any(f['tool'] == 'classify_lab_result' for f in inp.get('faults', []))
        count = 0 if failed else len(valid)
        if 'result_count' in exp:
            assert exp['result_count'] == count, i['id']
        if 'error_count' in exp:
            assert exp['error_count'] == len(inp['labs']) - count, i['id']
        for call in exp.get('required_calls', []):
            r = inp['labs'][0]
            args = call['arguments']
            assert args['test_name'] == r['test_name']
            if call['name'] == 'classify_lab_result':
                assert Decimal(str(args['value'])) == Decimal(str(r['result']))
            else:
                assert args['value'] == r['result']
            assert args['unit'] == r['unit']
            if call['name'] == 'classify_lab_result':
                assert Decimal(str(args['min_ref'])) == Decimal(str(r['min_reference']))
                assert Decimal(str(args['max_ref'])) == Decimal(str(r['max_reference']))
            else:
                assert args['reference'] == r['reference_range']
        if 'faults' in inp:
            assert exp.get('must_terminate', True)
        if i['id'] == 'parallel-rows':
            assert set(inp['tool_stubs']['classify_lab_result_by_test']) == {r['test_name'] for r in inp['labs']}
            assert exp['global_call_order'] == 'unconstrained_across_rows'
            assert exp['per_row_order'] == ['classify_lab_result','explain_result']
        if i['id'] == 'lookup-missing':
            assert inp['tool_stubs']['reference_range_lookup']['found'] is False
            assert exp['status'] == 'Unknown' and exp['required_tools'] == ['reference_range_lookup']
        if i['id'] == 'search-failure':
            assert exp['sources'] == []

    for i in datasets['judge_calibration']:
        inp, exp = i['input'], i['expected_output']
        text, predicate, witness = inp['candidate_answer'].lower(), exp['predicate'], exp['witness']
        context = inp['criterion'].lower()
        if predicate == 'numeric_value':
            assert Decimal(witness) in [Decimal(n) for n in re.findall(r'\d+(?:\.\d+)?', context)]
            verdict = Decimal(witness) in [Decimal(n) for n in re.findall(r'\d+(?:\.\d+)?', text)]
        elif predicate == 'range_relation':
            value, lo, hi = map(Decimal,re.findall(r'\d+(?:\.\d+)?', context))
            assert lo <= value <= hi and witness == 'within'
            verdict = 'within' in text
        elif predicate == 'absent_fact':
            assert 'only reported test is hemoglobin' in context
            verdict = 'b12 is not reported' in text
        elif predicate == 'less_than':
            assert '<'+witness in context
            verdict = 'less than '+witness in text and 'exactly' not in text
        else:
            assert predicate == 'topic_present' and witness in context
            verdict = witness in text
        assert exp['verdict'] == ('pass' if verdict else 'fail'), i['id']
    assert Counter(i['expected_output']['verdict'] for i in datasets['judge_calibration']) == {'pass':6,'fail':6}
    if check_manifest:
        manifest = json.loads((DATA / 'manifest.json').read_text())
        assert manifest['counts'] == {name:len(items) for name,items in datasets.items()}
        assert set(manifest['completed_datasets']) == set(NAMES)
        for f in manifest['files']:
            path = (ROOT / f['path']).resolve()
            assert path.is_relative_to(ROOT)
            assert hashlib.sha256(path.read_bytes()).hexdigest() == f['sha256'], f['path']
    print(f"Verified {sum(map(len,datasets.values()))} high-confidence software cases across all {len(NAMES)} datasets.")


def finalize():
    items = {name: read(name) for name in NAMES}
    fixtures = {ROOT / i['input']['fixture_path'] for i in items['extraction']}
    files = [*sorted(DATA.glob('*.jsonl')), DATA/'policy.json', DATA/'evidence.json', DATA/'item.schema.json',
             ROOT/'evals/curate_golden.py', ROOT/'evals/verify_golden.py', *sorted(fixtures)]
    manifest = dict(version='v2', status='machine_verified_software_scope',
        counts={name:len(rows) for name,rows in items.items()}, completed_datasets=list(NAMES),
        clinical_validation=False, files=[dict(path=str(p.relative_to(ROOT)),
            sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files])
    (DATA/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__ == '__main__':
    verify()
