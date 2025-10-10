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

CREATE TABLE events (
    event           TEXT NOT NULL,
    change_id       TEXT NOT NULL,
    change          TEXT NOT NULL,
    project         TEXT NOT NULL,
    note            TEXT NOT NULL,
    requires        TEXT NOT NULL,
    conflicts       TEXT NOT NULL,
    tags            TEXT NOT NULL,
    committed_at    TEXT NOT NULL,
    committer_name  TEXT NOT NULL,
    committer_email TEXT NOT NULL,
    planned_at      TEXT NOT NULL,
    planner_name    TEXT NOT NULL,
    planner_email   TEXT NOT NULL,
    PRIMARY KEY (change_id, committed_at)
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
) VALUES
    (
        '96d76eb96cac55a27d7d4117e96af312a29d1738',
        '96d76eb96cac55a27d7d4117e96af312a29d1738',
        'users',
        'flipr',
        'Creates table to track our users.',
        '2013-12-31 10:26:59 -0800',
        'Marge N. O’Vera',
        'marge@example.com',
        '2013-12-31 10:26:59 -0800',
        'Marge N. O’Vera',
        'marge@example.com'
    ),
    (
        'b5ee95a49f8226b33a535fba8c2b834f97044730',
        'b5ee95a49f8226b33a535fba8c2b834f97044730',
        'flips',
        'flipr',
        'Adds table for storing flips.',
        '2013-12-31 11:05:44 -0800',
        'Marge N. O’Vera',
        'marge@example.com',
        '2013-12-31 11:05:44 -0800',
        'Marge N. O’Vera',
        'marge@example.com'
    );
