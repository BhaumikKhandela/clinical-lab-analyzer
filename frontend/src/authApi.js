/**
 * Client for the auth service (port 8085), which owns accounts and issues the
 * tokens every other service trusts.
 *
 * Separate from patientApi.js on purpose: that service verifies tokens and
 * cannot issue them, which is the reason authentication was split out at all.
 */
import { authHeader } from "./auth";

const AUTH_API_BASE =
  import.meta.env.VITE_AUTH_API_BASE || "http://127.0.0.1:8085";

const UNREACHABLE =
  `Cannot reach the auth service at ${AUTH_API_BASE}. Is it running (./mvnw spring-boot:run from authService)?`;

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${AUTH_API_BASE}${path}`, {
      ...options,
      headers: { ...authHeader(), ...(options.headers || {}) },
    });
  } catch {
    throw new Error(UNREACHABLE);
  }

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(
      `${options?.method || "GET"} ${path} failed (HTTP ${response.status}): ${detail.slice(0, 300)}`
    );
  }

  if (response.status === 204) return null;
  return response.json();
}

/** POST /api/auth/login -> { token, tokenType, expiresIn, username, role } */
export function login(username, password) {
  return request("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
}

/**
 * The header the admin passphrase travels in.
 *
 * Sent on every admin call rather than exchanged once for a ticket: the service
 * re-checks it each time, so there is no "unlocked" state on the server that a
 * client could claim to be in.
 */
const PASSPHRASE_HEADER = "X-Admin-Passphrase";

/**
 * POST /api/auth/admin/unlock -> 204, or 403 when the passphrase is wrong.
 *
 * Lets the page check before showing a form instead of after submitting one. It
 * grants nothing: creating an account is checked again.
 */
export function unlockAdmin(passphrase) {
  return request("/api/auth/admin/unlock", {
    method: "POST",
    headers: { [PASSPHRASE_HEADER]: passphrase },
  });
}

/** POST /api/auth/register -> UserResponse. ADMIN token + passphrase. */
export function register({ username, password, role }, passphrase) {
  return request("/api/auth/register", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      [PASSPHRASE_HEADER]: passphrase,
    },
    body: JSON.stringify({ username, password, role }),
  });
}

/** GET /api/auth/users -> UserResponse[]. ADMIN token + passphrase. */
export function listUsers(passphrase) {
  return request("/api/auth/users", { headers: { [PASSPHRASE_HEADER]: passphrase } });
}

/** GET /api/auth/me -> UserResponse. Confirms a stored token is still good. */
export function whoAmI() {
  return request("/api/auth/me");
}
