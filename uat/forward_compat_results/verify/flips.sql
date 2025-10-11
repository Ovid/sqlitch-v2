-- Verify flipr:flips on sqlite

BEGIN;

SELECT id, nickname, body, timestamp
FROM flips
WHERE 0;

ROLLBACK;
