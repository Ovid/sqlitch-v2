-- Revert flipr:users from sqlite

BEGIN;

DROP TABLE users;

COMMIT;
