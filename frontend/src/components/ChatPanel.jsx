import { useEffect, useRef, useState } from "react";
import Icon from "./Icon";
import { chatSocketUrl } from "../api";

const SUGGESTIONS = [
  "Which result is most urgent?",
  "What does the reference range mean?",
  "What should I do next?",
];

export default function ChatPanel({ threadId }) {
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [status, setStatus] = useState("connecting");
  const [pending, setPending] = useState(false);
  const [open, setOpen] = useState(false);
  const [connectionAttempt, setConnectionAttempt] = useState(0);
  const socketRef = useRef(null);
  const endRef = useRef(null);

  // Escape closes the panel, as expected for a drawer.
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  useEffect(() => {
    if (!threadId) return undefined;

    const socket = new WebSocket(chatSocketUrl(threadId));
    socketRef.current = socket;

    socket.onopen = () => setStatus("open");
    socket.onclose = () => { setStatus("closed"); setPending(false); };
    socket.onerror = () => { setStatus("error"); setPending(false); };
    socket.onmessage = (event) => {
      let payload;
      try {
        payload = JSON.parse(event.data);
      } catch {
        return;
      }
      if (payload.type === "status") return;
      setPending(false);
      setMessages((prev) => [
        ...prev,
        { role: payload.type === "error" ? "error" : "assistant", content: payload.content },
      ]);
    };

    return () => {
      socket.onopen = null; socket.onclose = null; socket.onerror = null; socket.onmessage = null;
      socket.close();
    };
  }, [threadId, connectionAttempt]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages, pending]);

  function send(text) {
    const question = text.trim();
    if (!question || pending || status !== "open") return;
    socketRef.current?.send(JSON.stringify({ question }));
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setDraft("");
    setPending(true);
  }

  if (!threadId) return null;

  return (
    <>
      {/* Launcher — only rendered while the panel is closed. */}
      {!open && (
        <button type="button" className="chat__launcher" onClick={() => setOpen(true)}>
          <Icon name="chat" size={19}/> Discuss this report
        </button>
      )}

      {/* Backdrop is only interactive on narrow screens, where the panel overlays. */}
      <div
        className={`chat__scrim${open ? " chat__scrim--on" : ""}`}
        onClick={() => setOpen(false)}
        aria-hidden="true"
      />

      <aside
        className={`chat chat--panel${open ? " chat--open" : ""}`}
        aria-label="Follow-up chat"
        aria-hidden={!open}
        inert={!open ? true : undefined}
      >
        <header className="chat__head">
          <div><span className="eyebrow">YOUR REPORT COMPANION</span><h2>A little more clarity.</h2></div>
          <div className="chat__head-right">
            <span className={`chat__status chat__status--${status}`}>
              {status === "open"
                ? "connected"
                : status === "connecting"
                  ? "connecting…"
                  : "disconnected"}
            </span>
            <button
              type="button"
              className="chat__close"
              onClick={() => setOpen(false)}
              aria-label="Close chat"
            >
              ×
            </button>
          </div>
        </header>

      {(status === "closed" || status === "error") && <div className="chat__connection-error" role="status"><p>The conversation is disconnected. Reconnect to keep asking about this report.</p><button className="btn btn--ghost" onClick={() => { setStatus("connecting"); setConnectionAttempt(n => n + 1); }}>Reconnect</button></div>}
      <div className="chat__log" role="log" aria-label="Report conversation" aria-live="polite">
        {/* Rendered locally rather than sent by the server: it is a greeting,
            not part of the conversation the agent reasons over. */}
        <div className="bubble bubble--assistant">
          Let’s make sense of your report. Ask about a value, a reference range, or a suggested next step.
        </div>

        {messages.length === 0 && (
          <div className="chat__empty">
            <p>I already have this panel in context — ask me a follow-up question.</p>
            <div className="chat__suggestions">
              {SUGGESTIONS.map((s) => (
                <button key={s} type="button" className="chat__chip" disabled={pending || status !== "open"} onClick={() => send(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((message, i) => (
          <div key={i} className={`bubble bubble--${message.role}`}>
            {message.content}
          </div>
        ))}

        {pending && (
          <div className="bubble bubble--assistant bubble--pending">
            <span className="dot" />
            <span className="dot" />
            <span className="dot" />
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form
        className="chat__form"
        onSubmit={(e) => {
          e.preventDefault();
          send(draft);
        }}
      >
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={status === "open" ? "What would you like to understand?" : "Connection unavailable…"}
          disabled={status !== "open" || pending}
          aria-label="Your question"
        />
        <button type="submit" className="btn btn--primary" disabled={!draft.trim() || pending || status !== "open"}>
          <Icon name="arrow" size={18}/><span className="sr-only">Send question</span>
        </button>
      </form>
      </aside>
    </>
  );
}
