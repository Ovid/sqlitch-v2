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
    committer_email TEXT NOT NULL
);

INSERT INTO events (
    event,
    change_id,
    change,
    project,
    note,
    requires,
    conflicts,
    tags,
    committed_at,
    committer_name,
    committer_email
) VALUES
    (
        'revert',
        'f30fe47f5f99501fb8d481e910d9112c5ac0a676',
        'users',
        'flipr',
        'Creates table to track our users.',
        '',
        '',
        '',
        '2013-12-31 10:54:13 -0800',
        'Marge N. O’Vera',
        'marge@example.com'
    ),
    (
        'fail',
        'e6ce0812f4cf51382d43903b564274f080ff5e7a',
        'flips',
        'flipr',
        'Adds flips table.',
        'users',
        '',
        '',
        '2013-12-31 10:54:12 -0800',
        'Marge N. O’Vera',
        'marge@example.com'
    ),
    (
        'deploy',
        'f30fe47f5f99501fb8d481e910d9112c5ac0a676',
        'users',
        'flipr',
        'Creates table to track our users.',
        '',
        '',
        '',
        '2013-12-31 10:26:59 -0800',
        'Marge N. O’Vera',
        'marge@example.com'
    );
