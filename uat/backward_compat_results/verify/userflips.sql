-- Verify flipr:userflips on sqlite

BEGIN;

SELECT id, nickname, fullname, twitter, body, timestamp
FROM userflips
WHERE 0;

ROLLBACK;
