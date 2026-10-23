import { useState } from "react";
import { listUsers, register, unlockAdmin } from "../authApi";

const ROLES = [
  { id: "CLINICIAN", label: "Clinician — read and write patient records" },
  { id: "ADMIN", label: "Administrator — can also create accounts" },
];

const MIN_PASSWORD = 12;

function formatWhen(createdAt) {
  if (!createdAt) return "";
  const when = new Date(createdAt);
  return Number.isNaN(when.getTime()) ? "" : when.toLocaleString();
}

/**
 * Creates accounts on the auth service.
 *
 * Two gates. Being signed in as an administrator is the first; this page's
 * passphrase is the second, and it is checked by the auth service on every
 * call, not here — a value compared in the browser is one anybody can read out
 * of the bundle.
 *
 * The passphrase is held in component state only: never in localStorage, and
 * gone as soon as the tab is closed or the page is locked again.
 */
export default function AdminUsers() {
  const [passphrase, setPassphrase] = useState("");
  const [unlocked, setUnlocked] = useState(false);
  const [checking, setChecking] = useState(false);

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [role, setRole] = useState("CLINICIAN");

  const [users, setUsers] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [created, setCreated] = useState(null);

  function describe(err) {
    if (/\b403\b/.test(err.message)) return "That admin passphrase is wrong.";
    if (/\b409\b/.test(err.message)) return "That username is already taken.";
    return err.message;
  }

  async function handleUnlock(event) {
    event.preventDefault();
    setChecking(true);
    setError("");

    try {
      await unlockAdmin(passphrase);
      setUnlocked(true);
      // Worth showing straight away: the usual reason to open this page is to
      // find out who already has an account.
      setUsers(await listUsers(passphrase));
    } catch (err) {
      setError(describe(err));
      setPassphrase("");
    } finally {
      setChecking(false);
    }
  }

  function lock() {
    setUnlocked(false);
    setPassphrase("");
    setUsers([]);
    setCreated(null);
    setError("");
  }

  async function handleCreate(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setCreated(null);

    try {
      const user = await register({ username: username.trim(), password, role }, passphrase);
      setCreated(user);
      setUsername("");
      setPassword("");
      setConfirm("");
      setUsers(await listUsers(passphrase));
    } catch (err) {
      setError(describe(err));
    } finally {
      setBusy(false);
    }
  }

  if (!unlocked) {
    return (
      <section className="panel login">
        <h2 className="panel__title">Admin</h2>
        <p className="hint">
          Creating accounts needs the admin passphrase as well as an administrator sign-in. It is
          checked by the auth service, and is not stored anywhere in this page.
        </p>

        <form onSubmit={handleUnlock}>
          <label className="field">
            <span className="field__label">Admin passphrase</span>
            <input
              className="field__input"
              type="password"
              value={passphrase}
              onChange={(event) => setPassphrase(event.target.value)}
              autoComplete="off"
              required
            />
          </label>

          {error && (
            <div className="alert" role="alert">
              {error}
            </div>
          )}

          <button type="submit" className="btn btn--primary" disabled={checking || !passphrase}>
            {checking ? "Checking…" : "Unlock"}
          </button>
        </form>
      </section>
    );
  }

  const tooShort = password.length > 0 && password.length < MIN_PASSWORD;
  const mismatch = confirm.length > 0 && password !== confirm;
  const ready =
    username.trim().length >= 3 && password.length >= MIN_PASSWORD && password === confirm;

  return (
    <>
      <section className="panel">
        <div className="panel__head">
          <h2 className="panel__title">Create an account</h2>
          <button type="button" className="btn btn--ghost" onClick={lock}>
            Lock
          </button>
        </div>

        <form onSubmit={handleCreate}>
          <label className="field">
            <span className="field__label">Username</span>
            <input
              className="field__input"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              // Matches the server's pattern, so the field rejects what the
              // service would reject anyway.
              pattern="[A-Za-z0-9._\-]{3,64}"
              title="3–64 characters: letters, digits, dot, dash or underscore"
              autoComplete="off"
              required
            />
            <span className="hint">
              Stored lowercase, so <code>Asha</code> and <code>asha</code> are the same account.
            </span>
          </label>

          <label className="field">
            <span className="field__label">Password</span>
            <input
              className="field__input"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="new-password"
              minLength={MIN_PASSWORD}
              required
            />
            <span className="hint">
              At least {MIN_PASSWORD} characters. Length is the only rule: composition rules push
              people toward predictable substitutions.
            </span>
          </label>

          <label className="field">
            <span className="field__label">Confirm password</span>
            <input
              className="field__input"
              type="password"
              value={confirm}
              onChange={(event) => setConfirm(event.target.value)}
              autoComplete="new-password"
              required
            />
          </label>

          <label className="field">
            <span className="field__label">Role</span>
            <select
              className="field__input"
              value={role}
              onChange={(event) => setRole(event.target.value)}
            >
              {ROLES.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          {tooShort && <p className="hint">Password is under {MIN_PASSWORD} characters.</p>}
          {mismatch && <p className="hint">The two passwords do not match.</p>}

          {error && (
            <div className="alert" role="alert">
              {error}
            </div>
          )}

          <button type="submit" className="btn btn--primary" disabled={busy || !ready}>
            {busy ? "Creating…" : "Create account"}
          </button>
        </form>

        {created && (
          <p className="saved" role="status">
            Created <strong>{created.username}</strong> as {created.role}. Give them the password
            you just typed — it is stored only as a hash and cannot be read back.
          </p>
        )}
      </section>

      <section className="panel">
        <h2 className="panel__title">Accounts ({users.length})</h2>
        {users.length === 0 ? (
          <p className="hint">No accounts yet.</p>
        ) : (
          <ul className="reports">
            {users.map((user) => (
              <li className="reports__item" key={user.id}>
                <div className="reports__meta">
                  <span className="reports__name">{user.username}</span>
                  <span className="reports__when">
                    {user.role} · added {formatWhen(user.createdAt)}
                    {user.enabled ? "" : " · disabled"}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
