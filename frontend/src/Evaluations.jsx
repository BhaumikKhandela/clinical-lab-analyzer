import { useEffect, useState } from 'react';
import './Evaluations.css';

const LABELS = {classification:'Classification',normalization:'Units & aliases',workflow:'Agent workflow',extraction:'Report extraction',chat:'Conversation',explanations:'Explanations',judge_calibration:'Judge calibration',retrieval:'Retrieval'};
const PRESETS = [
  {id:'deterministic',icon:'◇',name:'Core regression',text:'Rules, units, aliases and agent workflows.',tag:'Free · 27 cases'},
  {id:'calibration',icon:'◎',name:'Judge calibration',text:'Check the judge against known good and bad answers.',tag:'Model calls · 12 cases'},
  {id:'language',icon:'✳',name:'Explanations & chat',text:'Grounding, relevance and conversational faithfulness.',tag:'Model calls · 12 cases'},
  {id:'extraction',icon:'▤',name:'Report extraction',text:'From a PDF to every value, unit and reference range.',tag:'Model calls · 11 cases'},
];
const failedMetric=m=>m.status==='error'||(m.gating!==false&&m.score!=null&&m.score<(m.threshold??1));
const status=i=>i.status==='error'?'error':i.status==='skipped'?'skipped':i.metrics?.some(failedMetric)?'failed':'passed';
const title=s=>s.replaceAll('_',' ').replaceAll('-',' ');
const count=(items,key)=>items.filter(i=>status(i)===key).length;
const time=s=>s?`${s.toFixed(1)}s`:'—';
function Badge({value}){return <span className={`ev-badge ${value}`}>{value==='passed'?'✓ ':value==='failed'?'× ':''}{title(value)}</span>}
function Code({value}){return <pre className="ev-code">{JSON.stringify(value??'Not available in this report',null,2)}</pre>}

export default function Evaluations(){
  const [data,setData]=useState(null),[gold,setGold]=useState({}),[error,setError]=useState(''),[selected,setSelected]=useState(null);
  const [suite,setSuite]=useState('deterministic'),[model,setModel]=useState('qwen/qwen3-30b-a3b-instruct-2507');
  const [filter,setFilter]=useState('all'),[query,setQuery]=useState(''),[detail,setDetail]=useState(null),[starting,setStarting]=useState(false),[smoke,setSmoke]=useState(false);
  async function refresh(){
    try{
      const r=await fetch('/eval-api/state');if(!r.ok)throw Error('Evaluation service is unavailable. Start it with: evals/.venv/bin/python evals/dashboard.py');
      const next=await r.json();setData(next);setError('');
      if(next.active?.running)setSelected(next.active.id);
    }catch(e){setError(e.message)}
  }
  useEffect(()=>{void Promise.resolve().then(refresh);fetch('/eval-api/golden').then(r=>r.ok?r.json():{}).then(setGold).catch(()=>{});const timer=setInterval(refresh,2000);return()=>clearInterval(timer)},[]);
  const runs=data?.runs??[], entry=runs.find(r=>r.id===selected)??runs[0],report=entry?.report,items=report?.items??[];
  const running=Boolean(data?.active?.running), pending=running&&entry?.id!==data.active.id;
  const shown=pending?[]:items;
  const passed=count(shown,'passed'), failed=count(shown,'failed'),errors=count(shown,'error'),skipped=count(shown,'skipped');
  const rate=shown.length?Math.round(passed/shown.length*100):0;
  const filtered=shown.filter(i=>(filter==='all'||status(i)===filter)&&(i.id+' '+i.dataset).toLowerCase().includes(query.toLowerCase()));
  const total=report?.total_cases??shown.length;
  async function start(){
    setStarting(true);setError('');setDetail(null);
    try{
      const r=await fetch('/eval-api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({suite,model,allow_paid:suite!=='deterministic',...(smoke?{limit:2}:{})})});
      const value=await r.json();if(!r.ok)throw Error(value.error);setSelected(value.id);setFilter('all');await refresh();
    }catch(e){setError(e.message)}finally{setStarting(false)}
  }
  const current=detail&&shown.find(i=>i.dataset+'/'+i.id===detail);
  return <div className="ev-shell">
    <aside className="ev-sidebar">
      <a className="ev-logo" href="/"><span>✳</span> aragen<span className="ev-logo-dot">.</span></a>
      <div className="ev-workspace">CLINICAL INTELLIGENCE <span>DEV</span></div>
      <div className="ev-nav-label">WORKSPACE</div>
      <a href="/" className="ev-nav">▧ <span>Lab analyzer</span><small>↗</small></a>
      <a href="/evaluations" className="ev-nav active">◈ <span>Evaluation studio</span><small>●</small></a>
      <div className="ev-nav-label ev-history-label">RECENT RUNS <span>{runs.length}</span></div>
      <div className="ev-history">{runs.slice(0,12).map(r=>{
        const good=r.report.items.filter(i=>status(i)==='passed').length;
        return <button key={r.id} className={entry?.id===r.id?'selected':''} onClick={()=>{setSelected(r.id);setDetail(null)}}>
          <span className={`ev-dot ${r.report.items.some(i=>['failed','error'].includes(status(i)))?'warn':''}`}/>
          <span>{r.report.judge_model?'Model evaluation':'Core checks'}<small>{new Date(r.updated*1000).toLocaleString(undefined,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'})}</small></span>
          <em>{good}/{r.report.items.length}</em>
        </button>
      })}{!runs.length&&<p className="ev-history-empty">Your runs will appear here.</p>}</div>
      <div className="ev-sidebar-bottom"><span className={`ev-dot ${error?'warn':''}`}/>{data?'Local workspace connected':'Waiting for local service'}<p>DeepEval · Synthetic benchmark v2</p></div>
    </aside>
    <main className="ev-main">
      <header className="ev-top"><span><a href="/">Workspace</a> <b>/</b> Evaluation studio</span><span className="ev-local">● Local development</span></header>
      <div className="ev-content">
        <div className="ev-heading"><div><span className="ev-eyebrow">MEASURE. UNDERSTAND. IMPROVE.</span><h1>Confidence, measured.</h1><p>A clear view of how your clinical agent performs.</p></div><div className="ev-benchmark"><strong>{Object.values(data?.counts??{}).reduce((a,b)=>a+b,0)||67}</strong><span>golden cases<br/>across 8 datasets</span></div></div>
        {error&&<div className="ev-error" role="alert">{error}</div>}
        {data?.active&&!running&&selected===data.active.id&&(!runs.some(r=>r.id===selected)||report?.running)&&<div className="ev-error" role="alert">The runner stopped before it could finish. Check the evaluation environment and credentials, then start a new run.</div>}
        <section className="ev-launch"><div className="ev-section-title"><h2>Choose your evaluation</h2><span>01 — CONFIGURE</span></div>
          <div className="ev-presets">{PRESETS.map(p=><button key={p.id} aria-pressed={suite===p.id} className={suite===p.id?'chosen':''} onClick={()=>setSuite(p.id)}><span className="ev-preset-icon">{p.icon}</span><span className="ev-radio"/><h3>{p.name}</h3><p>{p.text}</p><small>{p.tag}</small></button>)}</div>
          <div className="ev-runbar"><div className="ev-model">{suite!=='deterministic'&&<><label htmlFor="judge-model">{suite==='extraction'?'Judge model not used':'OpenRouter judge model'}</label>{suite!=='extraction'?<input id="judge-model" value={model} onChange={e=>setModel(e.target.value)} spellCheck="false"/>:<span>Uses the application extraction model</span>}</>}{suite==='deterministic'&&<><span className="ev-free-icon">✓</span><span>No model calls. No API cost.</span></>}</div>
            <label className="ev-smoke"><input type="checkbox" checked={smoke} onChange={e=>setSmoke(e.target.checked)}/> Smoke test <small>2 per dataset</small></label>
            <button className="ev-run" disabled={running||starting||!data} onClick={start}>{running?<><span className="ev-spinner"/> Evaluation running</>:starting?'Starting…':<>{suite==='deterministic'?'Run evaluation':'Run with model calls'} <span>↗</span></>}</button>
          </div>
        </section>
        <div className="ev-results-heading"><div><h2>{running?'Evaluation in progress':report?'Run overview':'Ready for your first run'} <span className="ev-version">v2</span></h2><p>{running?`${pending?0:shown.length} of ${pending?'…':total} cases completed · results update automatically`:entry?new Date(entry.updated*1000).toLocaleString():'Start a suite to see real results here.'}</p></div><div className="ev-run-actions">{runs.length>0&&<select aria-label="Run history" disabled={running} value={entry?.id??''} onChange={e=>{setSelected(e.target.value);setDetail(null)}}>{runs.map(r=><option key={r.id} value={r.id}>{r.report.judge_model?'Model':'Core'} · {new Date(r.updated*1000).toLocaleString()}</option>)}</select>}{entry&&!pending&&<button className="ev-download" onClick={()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=`eval-${report.run_id}.json`;a.click();URL.revokeObjectURL(url)}}>↓ Export JSON</button>}</div></div>
        {running&&<div className="ev-progress" aria-label="Evaluation progress"><div style={{width:`${pending?0:total?shown.length/total*100:0}%`}}/></div>}
        <div className="ev-stats"><div className="ev-stat ev-rate"><div className="ev-ring" style={{'--rate':`${rate}%`}}><span>{shown.length?rate:'—'}<small>{shown.length?'%':''}</small></span></div><div><span>Pass rate</span><p>{running?'Completed cases only':'Of executed cases'}</p></div></div>{[['Passed',passed,'passed','Correct outcomes'],['Failed',failed,'failed','Quality regressions'],['Errors',errors,'error','Execution problems'],['Skipped',skipped,'skipped','Not evaluated']].map(([label,n,s,hint])=><button key={s} className={`ev-stat ${s}`} onClick={()=>setFilter(s)}><span>{label}</span><strong>{shown.length?n:'—'}</strong><p>{hint}</p></button>)}</div>
        <section className="ev-cases"><div className="ev-section-title"><h2>Case results <span className="ev-count">{shown.length}</span></h2><span>02 — EXPLORE</span></div><div className="ev-toolbar"><div className="ev-tabs">{['all','failed','passed','error','skipped'].map(f=><button className={filter===f?'on':''} onClick={()=>setFilter(f)} key={f}>{f==='all'?'All cases':title(f)}</button>)}</div><input className="ev-search" aria-label="Search cases" placeholder="⌕  Search cases or datasets" value={query} onChange={e=>setQuery(e.target.value)}/></div>
          <div className="ev-table-wrap"><table className="ev-table"><thead><tr><th>TEST CASE</th><th>DATASET</th><th>RESULT</th><th>DURATION</th><th/></tr></thead><tbody>{filtered.map(i=><tr key={i.dataset+'/'+i.id} onClick={()=>setDetail(i.dataset+'/'+i.id)}><td><button className="ev-case-name" onClick={()=>setDetail(i.dataset+'/'+i.id)}>{title(i.id)}</button><small>{i.metrics?.length??0} metrics evaluated</small></td><td><span className="ev-dataset">{LABELS[i.dataset]??title(i.dataset)}</span></td><td><Badge value={status(i)}/></td><td className="ev-duration">{time(i.duration_seconds)}</td><td>↗</td></tr>)}</tbody></table></div>
          {!filtered.length&&<div className="ev-empty"><span>◎</span><h3>{shown.length?'No matching cases':'Nothing measured. Yet.'}</h3><p>{shown.length?'Try a different filter or search.':'Choose a suite above and start your first evaluation.'}</p></div>}
          <footer className="ev-table-footer"><span>{filtered.length} of {shown.length} cases</span><span>Expected failures in calibration are scored on judge agreement.</span></footer>
        </section>
        <p className="ev-footnote">SOURCE-VERIFIED FACTS · EXPLICIT SOFTWARE RULES · SYNTHETIC DATA ONLY <span>Clinical correctness is outside this benchmark’s scope.</span></p>
      </div>
    </main>
    {current&&<div className="ev-overlay" onClick={()=>setDetail(null)}><aside className="ev-detail" role="dialog" aria-modal="true" aria-label="Case details" onClick={e=>e.stopPropagation()}><button className="ev-close" aria-label="Close details" onClick={()=>setDetail(null)}>×</button><span className="ev-eyebrow">CASE INSPECTOR</span><h2>{title(current.id)}</h2><Badge value={status(current)}/><p className="ev-detail-sub">{LABELS[current.dataset]} · {time(current.duration_seconds)}</p>
      {current.error_type&&<div className="ev-error">Execution error: {current.error_type}</div>}{current.reason&&<p>{current.reason}</p>}
      <h3>Metric breakdown</h3>{current.metrics?.map((m,n)=><div className="ev-metric" key={n}><div><strong>{title(m.metric)}</strong><Badge value={m.status==='error'?'error':m.gating===false?'advisory':failedMetric(m)?'failed':'passed'}/></div><span className="ev-metric-score">{m.score==null?'—':`${Math.round(m.score*100)}%`} <small>threshold {Math.round((m.threshold??1)*100)}%</small></span><div className="ev-metric-bar"><i style={{width:`${Math.max(0,Math.min(100,(m.score??0)*100))}%`}}/></div>{m.reason&&<p>{m.reason}</p>}{m.error_type&&<p>{m.error_type}</p>}</div>)}
      <h3>Expected outcome</h3><Code value={gold[current.dataset+'/'+current.id]?.expected_output}/><h3>Actual output</h3><Code value={current.actual}/><details><summary>Input & provenance</summary><Code value={gold[current.dataset+'/'+current.id]}/></details>
    </aside></div>}
  </div>
}
