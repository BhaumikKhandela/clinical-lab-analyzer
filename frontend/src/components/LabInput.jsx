import { useState } from "react";

const EMPTY_ROW = { Test_Name: "", Result: "", Unit: "", Min_Reference: "", Max_Reference: "" };

/**
 * Manual entry of lab values. Reports arrive as documents now, so the former
 * CSV upload tab was removed — ReportAnalyze handles files.
 */
export default function LabInput({ onAnalyze, loading }) {
  const [rows, setRows] = useState([{ ...EMPTY_ROW }]);

  function updateRow(index, key, value) {
    setRows((prev) => prev.map((row, i) => (i === index ? { ...row, [key]: value } : row)));
  }

  function submit(event) {
    event.preventDefault();
    const filled = rows.filter((row) => row.Test_Name.trim() && String(row.Result).trim());
    if (filled.length) onAnalyze(filled);
  }

  const canSubmit =
    !loading && rows.some((row) => row.Test_Name.trim() && String(row.Result).trim());

  return (
    <form className="panel manual-panel" onSubmit={submit}>
      <h2 className="panel__title">Enter your lab values</h2>

      <div className="manual">
        <div className="manual__head">
          <span>Test name</span>
          <span>Result</span>
          <span>Unit</span>
          <span>Ref min</span>
          <span>Ref max</span>
          <span />
        </div>
        {rows.map((row, index) => (
          <div className="manual__row" key={index}>
            <label className="manual-cell"><span>Test name</span><input
              value={row.Test_Name}
              onChange={(e) => updateRow(index, "Test_Name", e.target.value)}
              placeholder="Hemoglobin"
              aria-label="Test name"
            /></label>
            <label className="manual-cell"><span>Result</span><input
              value={row.Result}
              onChange={(e) => updateRow(index, "Result", e.target.value)}
              placeholder="8.2"
              aria-label="Result"
            /></label>
            <label className="manual-cell"><span>Unit</span><input
              value={row.Unit}
              onChange={(e) => updateRow(index, "Unit", e.target.value)}
              placeholder="g/dL"
              aria-label="Unit"
            /></label>
            <label className="manual-cell"><span>Reference minimum</span><input
              value={row.Min_Reference}
              onChange={(e) => updateRow(index, "Min_Reference", e.target.value)}
              placeholder="12"
              aria-label="Reference minimum"
            /></label>
            <label className="manual-cell"><span>Reference maximum</span><input
              value={row.Max_Reference}
              onChange={(e) => updateRow(index, "Max_Reference", e.target.value)}
              placeholder="15"
              aria-label="Reference maximum"
            /></label>
            <button
              type="button"
              className="btn btn--icon"
              aria-label="Remove row"
              onClick={() => setRows((prev) => prev.filter((_, i) => i !== index))}
              disabled={rows.length === 1}
            >
              ×
            </button>
          </div>
        ))}
        <button
          type="button"
          className="btn btn--ghost"
          onClick={() => setRows((prev) => [...prev, { ...EMPTY_ROW }])}
        >
          + Add another test
        </button>
      </div>

      <button type="submit" className="btn btn--primary" disabled={!canSubmit}>
        {loading ? "Analyzing…" : "Analyze results"}
      </button>
    </form>
  );
}
