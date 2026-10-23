import { useState } from "react";
import Icon from "./Icon";
import LevelChart from "./LevelChart";
import SeverityBadge, { severityKey } from "./SeverityBadge";

const SECTIONS = [
  { key: "critical", title: "Critical", blurb: "Needs urgent attention" },
  { key: "warning", title: "Warning", blurb: "Outside the reference range" },
  { key: "unknown", title: "Unknown", blurb: "No reference range available" },
  { key: "normal", title: "Normal", blurb: "Within the reference range" },
];

function ResultCard({ result }) {
  const key = severityKey(result.status);
  const isAbnormal = key === "critical" || key === "warning";

  return (
    <article className={`card card--${key}`}>
      <header className="card__head">
        <div>
          <h3 className="card__title">
            {result.test_name}
            {result.test_name_original && (
              <span className="card__original"> ({result.test_name_original})</span>
            )}
          </h3>
          <p className="card__value">
            <strong>
              {result.value} {result.unit}
            </strong>
            {result.reference_range && (
              <span className="card__ref"> · reference {result.reference_range}</span>
            )}
          </p>
        </div>
        <SeverityBadge status={result.status} />
      </header>

      {/* Explainable AI: show the measurable reason before the narrative. */}
      {result.deviation && <p className="card__deviation">Why flagged: {result.deviation}</p>}

      <details className="finding-details" open={key === "critical"}>
      <summary>Explanation & next steps <Icon name="chevron" size={15}/></summary>
      {result.explanation && (
        <div className="card__block">
          <h4>AI explanation</h4>
          <p>{result.explanation}</p>
        </div>
      )}

      {result.next_steps && (
        <div className="card__block card__block--action">
          <h4>Suggested next step</h4>
          <p>{result.next_steps}</p>
        </div>
      )}

      {isAbnormal && result.sources?.length > 0 && (
        <details className="card__sources">
          <summary>
            Grounded in {result.sources.length} source{result.sources.length === 1 ? "" : "s"}
            {result.source_type ? ` (${result.source_type})` : ""}
          </summary>
          <ul>
            {result.sources.map((source, i) => (
              <li key={i}>
                {source.url ? (
                  <a href={source.url} target="_blank" rel="noreferrer">
                    {source.title || source.url}
                  </a>
                ) : (
                  source.title
                )}
              </li>
            ))}
          </ul>
        </details>
      )}

      {(result.source_status || result.source_comment) && (
        <p className="card__source-note">
          Source record:{" "}
          {result.source_status && <span>status “{result.source_status}”</span>}
          {result.source_status && result.source_comment && " · "}
          {result.source_comment}
        </p>
      )}
      </details>
    </article>
  );
}

export default function ResultsDisplay({ data, reportName, analyzedAt }) {
  const [filter, setFilter] = useState("all");
  if (!data) return null;
  const { summary = {}, results = {}, errors = [] } = data;
  const total = SECTIONS.reduce((sum, s) => sum + (results[s.key]?.length || 0), 0);

  return (
    <section className="results" aria-label="Report analysis">
      <header className="report-heading"><div><span className="eyebrow">YOUR REPORT, EXPLAINED</span><h2>{reportName || "Your laboratory analysis"}</h2><p>{total} measurements reviewed{analyzedAt ? ` · Analyzed ${analyzedAt.toLocaleString(undefined, {month:"short", day:"numeric",hour:"2-digit",minute:"2-digit"})}` : ""}</p></div><Icon name="report" size={30}/></header>
      {(results.critical?.length || 0) > 0 && <div className="attention-note"><span>!</span><div><strong>{results.critical.length} result{results.critical.length === 1 ? " requires" : "s require"} urgent attention</strong><p>The analyzer marked these results as critical. Review the findings and their suggested next steps with a clinician.</p></div></div>}
      <div className="summary">
        {SECTIONS.map(({ key, title }) => (
          <div className={`summary__tile summary__tile--${key}`} key={key}>
            <span className="summary__count">{summary[key] ?? 0}</span>
            <span className="summary__label">{title}</span>
          </div>
        ))}
      </div>

      {total === 0 && !errors.length && <p className="empty">No results to display.</p>}

      <div className="findings-toolbar"><h2>What your results say</h2><div className="finding-filters" role="group" aria-label="Filter findings">{["all", ...SECTIONS.map(s => s.key)].map(key => <button type="button" key={key} className={filter === key ? "selected" : ""} onClick={() => setFilter(key)} aria-pressed={filter === key}>{key === "all" ? "All findings" : SECTIONS.find(s => s.key === key)?.title}</button>)}</div></div>
      <details className="chart-disclosure"><summary>See values against their reference ranges <Icon name="chevron" size={15}/></summary><LevelChart data={data}/></details>

      {SECTIONS.map(({ key, title, blurb }) => {
        const items = results[key] || [];
        if (!items.length || (filter !== "all" && filter !== key)) return null;
        return (
          <div className="section" key={key}>
            <h2 className="section__title">
              {title} <span className="section__blurb">— {blurb}</span>
            </h2>
            {items.map((result, i) => (
              <ResultCard key={`${result.test_name}-${i}`} result={result} />
            ))}
          </div>
        );
      })}

      {filter !== "all" && !(results[filter]?.length) && <p className="empty">No findings in this category.</p>}
      {errors.length > 0 && (
        <div className="section">
          <h2 className="section__title">
            Skipped rows <span className="section__blurb">— could not be analyzed</span>
          </h2>
          <ul className="errors">
            {errors.map((err, i) => (
              <li key={i}>
                <strong>{err.test_name || "(unnamed row)"}</strong>: {err.error}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
