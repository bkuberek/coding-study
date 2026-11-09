DROP TABLE members;

CREATE TABLE members (
    id integer PRIMARY KEY,
    name text NOT NULL,
    plan text NOT NULL DEFAULT 'flex'
);

INSERT INTO members (id, name) VALUES (1, 'Ada'), (2, 'Grace');
