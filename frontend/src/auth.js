/**
 * The signed-in session: the bearer token patientService issues, and who it
 * belongs to.
 *
 * Kept in localStorage so a reload does not sign you out. The trade-off is that
 * script running on this origin can read it, which an httpOnly cookie would
 * prevent — but a cookie would then be attached to every request automatically,
 * which is what CSRF protection exists to undo. A bearer token in storage is
 * the usual choice for an API like this one, and it is only as safe as the app
 * is free of XSS.
 */

const TOKEN_KEY = "lab-analyzer.token";
const USER_KEY = "lab-analyzer.user";

// Storage throws in private mode and in some embedded browsers, and returns
// nothing when site data has been cleared. Every access is guarded so a failure
// signs the user out rather than breaking the page.
function read(key) {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key, value) {
  try {
    if (value === null) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, value);
  } catch {
    /* A session that cannot be persisted still works until the tab closes. */
  }
}

/**
 * Reads `exp` out of a token without verifying it.
 *
 * This is for the interface only — so a visibly dead token sends the user to
 * the login form instead of showing an app that 401s on every click. The
 * server verifies properly; nothing here is a security check.
 */
function expiryOf(token) {
  try {
    const [, payload] = token.split(".");
    const json = JSON.parse(
      atob(payload.replace(/-/g, "+").replace(/_/g, "/"))
    );
    return typeof json.exp === "number" ? json.exp * 1000 : null;
  } catch {
    return null;
  }
}

let session = load();
const listeners = new Set();

function load() {
  const token = read(TOKEN_KEY);
  if (!token) return null;

  const expiresAt = expiryOf(token);
  if (expiresAt !== null && expiresAt <= Date.now()) {
    write(TOKEN_KEY, null);
    write(USER_KEY, null);
    return null;
  }

  let user = {};
  try {
    user = JSON.parse(read(USER_KEY) || "{}");
  } catch {
    user = {};
  }
  return { token, expiresAt, username: user.username, role: user.role };
}

function announce() {
  for (const listener of listeners) listener(session);
}

/** The current session, or null when signed out. */
export function getSession() {
  return session;
}

export function getToken() {
  return session?.token ?? null;
}

/** `Authorization` header for an authenticated call, or {} when signed out. */
export function authHeader() {
  return session ? { Authorization: `Bearer ${session.token}` } : {};
}

/** Stores a LoginResponse from patientService. */
export function startSession({ token, username, role }) {
  session = { token, username, role, expiresAt: expiryOf(token) };
  write(TOKEN_KEY, token);
  write(USER_KEY, JSON.stringify({ username, role }));
  announce();
  return session;
}

/**
 * Signs out. `reason` is shown on the login form, so an expired session
 * explains itself instead of looking like a random logout.
 */
export function endSession(reason = "") {
  session = null;
  write(TOKEN_KEY, null);
  write(USER_KEY, null);
  lastReason = reason;
  announce();
}

let lastReason = "";

/** Why the last sign-out happened; cleared once it has been shown. */
export function takeSignOutReason() {
  const reason = lastReason;
  lastReason = "";
  return reason;
}

/** Subscribe to sign-in and sign-out. Returns an unsubscribe function. */
export function onSessionChange(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
