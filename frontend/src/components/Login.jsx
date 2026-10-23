import { useState } from "react";
import { login } from "../authApi";
import { startSession, takeSignOutReason } from "../auth";

/**
 * The sign-in form, shown instead of the app until there is a session.
 *
 * It renders the whole page rather than a modal over the tabs: every view
 * behind it would be showing empty lists and 401 errors, which looks like a
 * broken app rather than a locked one.
 */
export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  // Read once, on first render: an expired session explains itself here rather
  // than looking like a spontaneous logout.
  const [notice] = useState(takeSignOutReason);

  async function handleSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");

    try {
      const session = await login(username.trim(), password);
      // Nothing else to do: App is subscribed and swaps this screen out.
      startSession(session);
    } catch (err) {
      // The service answers 401 for both a wrong password and an unknown
      // account, on purpose, so there is one message to show for either.
      setError(
        /\b401\b/.test(err.message)
          ? "Invalid username or password."
          : err.message
      );
      setPassword("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="signin-layout"><aside className="signin-story"><span className="eyebrow">HEALTH, IN YOUR OWN WORDS</span><h1>Your health tells<br/>a story.<br/><em>Let’s make it clear.</em></h1><p>A thoughtful space to understand your lab results, see what matters, and prepare for your next conversation.</p><div className="signin-note"><span>01 / UNDERSTAND</span><p>Less searching for answers.<br/>More perspective on your results.</p></div></aside><section className="panel login">
      <span className="eyebrow">WELCOME TO ARAGEN</span><h2 className="panel__title">A clearer picture awaits.</h2>
      <p className="login-intro">Sign in to your clinical workspace.</p>

      {notice && <p className="hint login__notice">{notice}</p>}

      <form onSubmit={handleSubmit}>
        <label className="field">
          <span className="field__label">Username</span>
          <input
            className="field__input"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
            autoFocus
            required
          />
        </label>

        <label className="field">
          <span className="field__label">Password</span>
          <input
            className="field__input"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            required
          />
        </label>

        {error && (
          <div className="alert" role="alert">
            {error}
          </div>
        )}

        <button
          type="submit"
          className="btn btn--primary"
          disabled={busy || !username.trim() || !password}
        >
          {busy ? "Signing in…" : "Sign in to your workspace →"}
        </button>
      </form>
      <p className="login-support">Need access? Contact your workspace administrator.</p>
    </section></div>
  );
}
