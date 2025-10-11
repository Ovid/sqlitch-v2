-- Revert flipr:userflips from sqlite

BEGIN;

DROP VIEW userflips;

COMMIT;
