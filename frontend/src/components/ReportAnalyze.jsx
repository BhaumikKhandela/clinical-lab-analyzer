import { useRef, useState } from 'react';
import Icon from './Icon';

const MAX_BYTES = 10 * 1024 * 1024;
export default function ReportAnalyze({ onAnalyzeFile, loading }) {
  const [file,setFile]=useState(null), [error,setError]=useState(''),[dragging,setDragging]=useState(false);
  const input=useRef(null);
  function choose(picked){
    if(!picked)return;
    if(!picked.name.toLowerCase().endsWith('.pdf')){setError('Choose a PDF report. Word documents and images cannot be analyzed here.');setFile(null);return}
    if(picked.size>MAX_BYTES){setError('This report is larger than 10 MB. Choose a smaller PDF.');setFile(null);return}
    setFile(picked);setError('');
  }
  return <section className="panel upload-panel">
    <div className="upload-heading"><span className="eyebrow">START WITH YOUR REPORT</span><h2>Make sense of<br/>your lab report.</h2><p>Bring your lab results. We’ll help make them easier to read.</p></div>
    <div className={`report-drop ${dragging?'is-dragging':''} ${file?'has-file':''}`} onDragOver={e=>{e.preventDefault();if(!loading)setDragging(true)}} onDragLeave={()=>setDragging(false)} onDrop={e=>{e.preventDefault();setDragging(false);if(!loading)choose(e.dataTransfer.files?.[0])}}>
      <input ref={input} id="report-file" type="file" accept=".pdf,application/pdf" onChange={e=>choose(e.target.files?.[0])} hidden disabled={loading}/>
      <span className="upload-icon"><Icon name={file?'report':'upload'} size={27}/></span>
      <h3>{file?file.name:'A clearer picture starts here'}</h3>
      <p>{file?`${(file.size/1024).toFixed(0)} KB · Ready to analyze`:'Drop your lab report here, or choose a file below.'}</p>
      <button type="button" className="btn btn--ghost" onClick={()=>input.current?.click()} disabled={loading}>{file?'Choose a different file':'Choose a PDF'}<Icon name="plus" size={15}/></button>
      <span className="upload-spec">PDF · Up to 10 MB · Text-based reports</span>
    </div>
    {error&&<p className="alert" role="alert">{error}</p>}
    <div className="upload-action"><p><Icon name="clock" size={15}/> A full panel usually takes a minute or two.</p><button type="button" className="btn btn--primary" onClick={()=>onAnalyzeFile(file)} disabled={!file||loading}>{loading?'Understanding your report…':'Analyze report'}<Icon name="arrow" size={16}/></button></div>
    <p className="upload-note">Scanned or image-only PDFs aren’t supported yet. Results are informational and should be discussed with a clinician.</p>
  </section>
}
