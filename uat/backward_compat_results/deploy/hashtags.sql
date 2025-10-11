-- Deploy flipr:hashtags to sqlite
-- requires: flips

BEGIN;

CREATE TABLE hashtags (
    flip_id INTEGER NOT NULL REFERENCES flips(id),
    hashtag TEXT NOT NULL CHECK ( length(hashtag) > 0 ),
    PRIMARY KEY (flip_id, hashtag)
);

COMMIT;
