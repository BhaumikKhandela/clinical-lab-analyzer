-- Accounts that may use the system.
--
-- This table lives in the auth service's own database, not alongside the
-- clinical records. The split is the point of the service: patientService can
-- verify who a caller is, and has no way to read or change the credentials that
-- made them that caller.
CREATE TABLE IF NOT EXISTS app_user (
    id            UUID PRIMARY KEY,

    -- Lowercased before storing and before lookup, so "Asha" and "asha" cannot
    -- both be registered.
    username      VARCHAR(64)  NOT NULL UNIQUE,

    -- A BCrypt hash, never a password. Sized for BCrypt's 60 characters with
    -- room for a future algorithm prefix.
    password_hash VARCHAR(100) NOT NULL,

    role          VARCHAR(16)  NOT NULL CHECK (role IN ('ADMIN', 'CLINICIAN')),

    -- Lets an account be switched off without deleting it and losing the record
    -- of what it did.
    enabled       BOOLEAN      NOT NULL DEFAULT TRUE,

    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);
