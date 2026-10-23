-- Accounts moved to the auth service, which owns its own database.
--
-- V6 created this table here, when this service both issued and verified
-- tokens. It now only verifies them, and holding credentials it never reads
-- would be a copy of the account store with no owner — the kind that drifts and
-- then leaks. V6 is left in place so the applied history still validates.
DROP TABLE IF EXISTS app_user;
