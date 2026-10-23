import { useEffect, useState } from "react";
import Icon from "./components/Icon";
import AddImage from "./components/AddImage";
import AddPatient from "./components/AddPatient";
import AdminUsers from "./components/AdminUsers";
import AddReport from "./components/AddReport";
import ChatPanel from "./components/ChatPanel";
import PatientImages from "./components/PatientImages";
import PatientReports from "./components/PatientReports";
import SendReport from "./components/SendReport";
import LabInput from "./components/LabInput";
import LoadingStatus from "./components/LoadingStatus";
import ResultsDisplay from "./components/ResultsDisplay";
import ReportAnalyze from "./components/ReportAnalyze";
import Login from "./components/Login";
import { analyzeLabs, analyzeReportPdf } from "./api";
import { endSession, getSession, onSessionChange } from "./auth";
import "./App.css";

// Ordered the way the work flows: a patient exists before a report is filed
// against them, and reports exist before there is anything to browse.
const VIEWS = [
  { id: "analyze", label: "Overview & analysis", icon: "overview", title: "A clearer view of your health.", description: "Understand your lab report, one finding at a time." },
  { id: "patient-reports", label: "Report library", icon: "report", title: "Your report library.", description: "Revisit documents and saved analyses for each patient." },
  { id: "add-patient", label: "Add patient", icon: "person", title: "Add a patient.", description: "Create a patient record to keep their documents together." },
  { id: "add-report", label: "Save a report", icon: "upload", title: "Save a lab report.", description: "File a report against a patient to revisit it later." },
  { id: "patient-images", label: "Image library", icon: "image", title: "Your image library.", description: "Browse stored images and available image analyses." },
  { id: "add-image", label: "Save an image", icon: "plus", title: "Save a patient image.", description: "Add an image to a patient’s record." },
  { id: "send-report", label: "Share a report", icon: "send", title: "Share a report.", description: "Email a stored report and its available analysis." },
  { id: "admin", label: "Manage accounts", icon: "shield", adminOnly: true, title: "Your workspace team.", description: "Manage access to your clinical workspace." },
];

export default function App() {
  // Seeded from storage, so a reload does not sign you out, and kept in step
  // with the API client: a 401 anywhere ends the session, and this is how the
  // interface finds out.
  const [session, setSession] = useState(getSession);
  useEffect(() => onSessionChange(setSession), []);

  const [view, setView] = useState("analyze");
  // Bumped whenever a patient is added. Every view stays mounted, so without
  // this the patient dropdowns would keep showing the list they fetched at
  // startup and a new patient would be unselectable until a page reload.
  const [patientsVersion, setPatientsVersion] = useState(0);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [reportName, setReportName] = useState("");
  const [analyzedAt, setAnalyzedAt] = useState(null);
  const [entryMode, setEntryMode] = useState("file");
  const page = VIEWS.find(item => item.id === view) || VIEWS[0];

  async function handleAnalyze(labs) {
    setLoading(true);
    setError("");
    try {
      setData(await analyzeLabs(labs));
      setReportName("Entered laboratory results");
      setAnalyzedAt(new Date());
    } catch (err) {
      setError(err.message);
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  /** Document path: the analyzer extracts the values from the PDF itself. */
  async function handleAnalyzeFile(file) {
    if (!file) return;
    setLoading(true);
    setError("");
    try {
      setData(await analyzeReportPdf(file));
      setReportName(file.name);
      setAnalyzedAt(new Date());
    } catch (err) {
      setError(err.message);
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={`app ${session ? "app--workspace" : "app--signed-out"}`}>
      <a className="skip-link" href="#main-content">Skip to content</a>
      {session && <aside className="health-nav">
        <a className="health-wordmark" href="/" aria-label="Aragen home"><span className="health-emblem">a</span>aragen<span className="wordmark-dot">.</span></a>
        <p className="nav-caption">A CLEARER PICTURE OF HEALTH</p>
        <span className="nav-group-label">YOUR WORKSPACE</span>
        <nav aria-label="Primary">{VIEWS.filter(v => !v.adminOnly || session.role === "ADMIN").map(v => <button key={v.id} className={`health-nav-item ${view === v.id ? "is-active" : ""}`} aria-current={view === v.id ? "page" : undefined} onClick={() => setView(v.id)}><Icon name={v.icon} size={18}/><span>{v.label}</span>{view === v.id && <span className="nav-active-dot"/>}</button>)}</nav>
        <div className="health-nav-bottom"><a href="/evaluations"><Icon name="shield" size={16}/> Evaluation Studio <span>↗</span></a><div className="nav-person"><span className="person-initial">{(session.username || "A").slice(0,1).toUpperCase()}</span><div><strong>{session.username}</strong><small>{session.role?.toLowerCase() || "Workspace member"}</small></div><button onClick={endSession} aria-label="Sign out" title="Sign out"><Icon name="logout" size={17}/></button></div></div>
      </aside>}
      <div className="health-workspace">
      <header className="health-topbar">
        {session ? <><span className="health-breadcrumb">Your workspace <span>/</span> {page.label}</span><span className="health-topnote"><span/> Thoughtful care starts with understanding</span></> : <><a className="health-wordmark" href="/"><span className="health-emblem">a</span>aragen.</a><a className="quiet-link" href="/evaluations">Evaluation Studio ↗</a></>}
      </header>
      <main className="app__main" id="main-content">
        {session && <header className="page-intro"><div><p className="eyebrow">{view === "analyze" ? "YOUR HEALTH, BETTER UNDERSTOOD" : "YOUR CLINICAL WORKSPACE"}</p><h1>{data && view === "analyze" ? "Your report, made clear." : page.title}</h1><p className="page-description">{page.description}</p></div><span className="intro-edition">ARAGEN<br/>HEALTH WORKSPACE</span></header>}
      {/*
        Every view stays mounted and is merely hidden, rather than being
        swapped in and out. Unmounting threw away whatever the view was doing:
        an analysis running on another tab had its result delivered to a dead
        component, and finished results disappeared on the way back.
      */}

        {/*
          Signed out, the views are not rendered at all — not merely hidden.
          `hidden` only hides: the component still mounts and still fires its
          requests, which signed out means a row of 401s behind the form. The
          views stay mounted once signed in, which is what protects work in
          progress; before that there is no work to protect.
        */}
        {!session ? (
          <Login />
        ) : (
          <>
        <div hidden={view !== "analyze"}>
          <div className="analysis-start">
            <section className="analysis-input"><div className="input-tabs" role="group" aria-label="Analysis input method"><button className={entryMode === "file" ? "selected" : ""} onClick={() => setEntryMode("file")}><Icon name="report" size={16}/> Upload a report</button><button className={entryMode === "manual" ? "selected" : ""} onClick={() => setEntryMode("manual")}>Enter values manually</button></div><div hidden={entryMode !== "file"}><ReportAnalyze onAnalyzeFile={handleAnalyzeFile} loading={loading}/></div><div hidden={entryMode !== "manual"}><LabInput onAnalyze={handleAnalyze} loading={loading}/></div></section>
            <aside className="analysis-guide"><span className="eyebrow">A LITTLE GUIDANCE</span><h2>From numbers<br/>to understanding.</h2><ol><li><span>01</span><div><strong>Bring your report</strong><p>Upload a text-based PDF or enter your lab values.</p></div></li><li><span>02</span><div><strong>See what stands out</strong><p>Review your values alongside their reference ranges.</p></div></li><li><span>03</span><div><strong>Ask a better question</strong><p>Explore the explanation and ask about your results.</p></div></li></ol><button className="text-link" onClick={() => setView("patient-reports")}>Browse saved reports <Icon name="arrow" size={16}/></button></aside>
          </div>
          {!data && !loading && <section className="workspace-continuity"><Icon name="report" size={25}/><div><h3>Already have a report on file?</h3><p>Open the report library to revisit a patient’s documents and saved analysis.</p></div><button className="btn btn--ghost" onClick={() => setView("patient-reports")}>Open report library <Icon name="arrow" size={16}/></button></section>}

          {error && (
            <div className="alert" role="alert">
              {error}
            </div>
          )}

          {loading && <LoadingStatus />}

          {!loading && <ResultsDisplay data={data} reportName={reportName} analyzedAt={analyzedAt} />}
          {!loading && data?.thread_id && <ChatPanel threadId={data.thread_id} />}
        </div>

        <div hidden={view !== "add-patient"}>
          <AddPatient onCreated={() => setPatientsVersion((version) => version + 1)} />
        </div>

        <div hidden={view !== "add-report"}>
          <AddReport patientsVersion={patientsVersion} />
        </div>

        <div hidden={view !== "add-image"}>
          <AddImage patientsVersion={patientsVersion} />
        </div>

        <div hidden={view !== "patient-reports"}>
          <PatientReports patientsVersion={patientsVersion} />
        </div>

        <div hidden={view !== "patient-images"}>
          <PatientImages patientsVersion={patientsVersion} />
        </div>

        <div hidden={view !== "send-report"}>
          <SendReport patientsVersion={patientsVersion} />
        </div>

        {/*
          Mounted only for an administrator, and only while that tab is open:
          leaving it mounted would keep the passphrase in component state after
          the user had moved on.
        */}
        {session?.role === "ADMIN" && view === "admin" && <AdminUsers />}
          </>
        )}
      </main>

      <footer className="app__footer"><span>aragen. <span>Clarity for the next conversation.</span></span><p>Clinical decision support. Informational only, not a diagnosis.</p></footer>
      </div>
    </div>
  );
}
