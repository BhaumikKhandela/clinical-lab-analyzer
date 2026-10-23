"""JSON subprocess bridge, executed with the existing backend Python environment."""
import asyncio
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'Analyzer Service/backend'))
import app.config  # load existing local credentials without printing them
from app import mcp_server as tools
from app.pdf_extract import extract_text, extract_report
from app.units import check_compatibility
from app.reference_ranges import canonical_key


async def task(dataset, item, evidence):
    inp = item['input']
    if dataset == 'classification':
        r = inp['lab']
        result=tools.classify_lab_result(r['test_name'], float(r['result']), r['unit'], r['min_reference'], r['max_reference'])
        bounds=re.match(r'([+-]?[\d.]+)-([+-]?[\d.]+)',result.get('reference_range') or '')
        if bounds: result.update(normal_low=float(bounds[1]),normal_high=float(bounds[2]))
        return result
    if dataset == 'normalization':
        if 'alias_contract' in inp:
            return {'canonical_test': canonical_key(inp['test_name'])}
        status, factor, _ = check_compatibility(inp['test_name'], inp['observed_unit'], inp['expected_unit'])
        return dict(compatibility=status, factor=factor,
                    converted_value=float(inp['value'])*factor if factor is not None else None)
    if dataset == 'extraction':
        text = extract_text((ROOT/inp['fixture_path']).read_bytes())
        result = extract_report(text).model_dump()
        return dict(outcome='complete', **result)
    if dataset == 'explanations':
        r = inp['lab']
        interval=(f"{r['min_reference']} - {r['max_reference']} {r['unit']}"
                  if r['min_reference'] is not None and r['max_reference'] is not None else 'not supplied')
        result = tools.explain_result(r['test_name'],r['result'],r['unit'],'Unknown',
            interval, '\n'.join(evidence[e]['snippet'] for e in inp['evidence_ids']))
        return {'actual_output':result['explanation'], 'degraded':result.get('source') != 'llm'}
    if dataset == 'chat':
        turns = inp['turns']
        result = tools.answer_followup(turns[-1]['content'],json.dumps(inp['report']),json.dumps(turns[:-1]))
        return {'actual_output':result['answer'], 'degraded':result.get('source') != 'llm'}
    if dataset == 'workflow':
        from app.graph import build_graph
        from langgraph.checkpoint.memory import MemorySaver
        class StubClient:
            def __init__(self): self.calls=[]
            async def call_tool(self, name, args):
                self.calls.append(dict(name=name,arguments=args))
                if any(f['tool']==name for f in inp.get('faults',[])): raise TimeoutError('injected')
                stubs=inp['tool_stubs']
                if name == 'classify_lab_result' and 'classify_lab_result_by_test' in stubs:
                    return stubs['classify_lab_result_by_test'][args['test_name']]
                if name in stubs: return dict(stubs[name])
                if name=='translate_to_english': return {'translations':args['texts']}
                if name=='search_clinical_context': return {'found':False,'results':[]}
                if name=='check_unit_compatibility': return {'status':'unknown','factor':1}
                if name=='explain_result': return {'explanation':'Controlled explanation.'}
                if name=='get_next_steps': return {'next_steps':'Controlled next step.'}
                raise ValueError('Unexpected tool '+name)
        client=StubClient()
        graph=build_graph(client,MemorySaver())
        nodes=[]; state=None
        async for update in graph.astream({'raw_labs':inp['labs'],'run_id':item['id']},
                {'configurable':{'thread_id':item['id']}},stream_mode='updates'):
            nodes.extend(k for k in update if k != '__interrupt__')
        state=await graph.aget_state({'configurable':{'thread_id':item['id']}})
        return dict(response=state.values['response'],tools_called=client.calls,nodes=nodes)
    raise ValueError('No application adapter for '+dataset)


if __name__ == '__main__':
    request=json.load(sys.stdin)
    try:
        result=asyncio.run(task(**request))
    except ValueError as exc:
        if request['dataset']=='extraction' and ('PDF' in str(exc) or 'scan' in str(exc)):
            result={'outcome':'rejected','labs':[],'error_type':type(exc).__name__}
        else: raise
    print(json.dumps(result))
