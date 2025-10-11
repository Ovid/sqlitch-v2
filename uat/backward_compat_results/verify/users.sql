-- Verify flipr:users on sqlite

BEGIN;

SELECT nickname, password, fullname, twitter
FROM users
WHERE 0;

ROLLBACK;
