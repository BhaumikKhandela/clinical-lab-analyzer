-- Accounts that may call this service.
--
-- Deliberately separate from `patient`: a patient is a subject of care, an
-- app_user is someone who operates the system. Conflating them would mean every
-- patient row needed a password column it would never use, and every operator
-- needed a date of birth.
CREATE TABLE IF NOT EXISTS app_user (
    id            UUID PRIMARY KEY,

    -- Case-insensitive in practice: the service lowercases before storing and
    -- before looking up, so "Asha" and "asha" cannot both be registered.
    username      VARCHAR(64)  NOT NULL UNIQUE,

    -- A BCrypt hash, never a password. The column is sized for the 60-character
    -- BCrypt output with room for a future algorithm prefix.
    password_hash VARCHAR(100) NOT NULL,

    -- Mirrors the Role enum, persisted with @Enumerated(EnumType.STRING).
    role          VARCHAR(16)  NOT NULL CHECK (role IN ('ADMIN', 'CLINICIAN')),

    -- Lets an account be switched off without deleting it and losing the audit
    -- trail of what it did.
    enabled       BOOLEAN      NOT NULL DEFAULT TRUE,

    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);
