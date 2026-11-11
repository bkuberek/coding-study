-- A feed is known by its name, and its reject report is replaced each time it is loaded.
CREATE TABLE feeds (
    name text PRIMARY KEY
);

CREATE TABLE feed_rejects (
    feed   text NOT NULL REFERENCES feeds (name),
    line   integer NOT NULL,
    reason text NOT NULL,
    PRIMARY KEY (feed, line)
);
