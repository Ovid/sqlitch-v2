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

-- No rows: deploy failed and all changes were reverted.
