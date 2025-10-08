CREATE TABLE projects (
    project         TEXT PRIMARY KEY,
    uri             TEXT,
    created_at      TEXT NOT NULL,
    creator_name    TEXT NOT NULL,
    creator_email   TEXT NOT NULL
);

CREATE TABLE changes (
    change_id       TEXT PRIMARY KEY,
    script_hash     TEXT,
    "change"        TEXT NOT NULL,
    project         TEXT NOT NULL,
    note            TEXT NOT NULL,
    committed_at    TEXT NOT NULL,
    committer_name  TEXT NOT NULL,
    committer_email TEXT NOT NULL,
    planned_at      TEXT NOT NULL,
    planner_name    TEXT NOT NULL,
    planner_email   TEXT NOT NULL
);

INSERT INTO projects (project, uri, created_at, creator_name, creator_email)
VALUES (
    'flipr',
    'https://github.com/sqitchers/sqitch-sqlite-intro/',
    '2013-12-31T00:00:00Z',
    'Marge N. O’Vera',
    'marge@example.com'
);

INSERT INTO changes (
    change_id,
    script_hash,
    "change",
    project,
    note,
    committed_at,
    committer_name,
    committer_email,
    planned_at,
    planner_name,
    planner_email
) VALUES (
    'f30fe47f5f99501fb8d481e910d9112c5ac0a676',
    'f30fe47f5f99501fb8d481e910d9112c5ac0a676',
    'users',
    'flipr',
    '',
    '2013-12-31 10:26:59 -0800',
    'Marge N. O’Vera',
    'marge@example.com',
    '2013-12-31 10:26:59 -0800',
    'Marge N. O’Vera',
    'marge@example.com'
);
