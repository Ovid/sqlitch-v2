-- Deploy flipr:flips to sqlite
-- requires: users

BEGIN;

CREATE TABLE flips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nickname TEXT NOT NULL REFERENCES users(nickname),
    body TEXT NOT NULL DEFAULT '' CHECK ( length(body) <= 180 ),
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMIT;
