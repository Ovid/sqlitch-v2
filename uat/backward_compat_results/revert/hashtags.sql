-- Revert flipr:hashtags from sqlite

BEGIN;

DROP TABLE hashtags;

COMMIT;
