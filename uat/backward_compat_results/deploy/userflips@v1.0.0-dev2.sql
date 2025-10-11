-- Deploy flipr:userflips to sqlite
-- requires: users
-- requires: flips

BEGIN;

CREATE VIEW userflips AS
SELECT f.id, u.nickname, u.fullname, f.body, f.timestamp
FROM users u
JOIN flips f ON u.nickname = f.nickname;

COMMIT;
