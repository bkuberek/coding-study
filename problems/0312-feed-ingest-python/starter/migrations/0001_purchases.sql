-- The shop's purchases, as the loyalty program keeps them. The constraints are part of the
-- contract: a row that breaks one can never be stored.
CREATE TABLE categories (
    code text PRIMARY KEY
);

INSERT INTO categories (code) VALUES ('grocery'), ('dining'), ('fuel'), ('travel'), ('other');

CREATE TABLE purchases (
    id           text PRIMARY KEY CHECK (id <> ''),
    member       text NOT NULL CHECK (member <> ''),
    purchased_on date NOT NULL,
    category     text NOT NULL REFERENCES categories (code),
    amount_cents bigint NOT NULL CHECK (amount_cents >= 0)
);

CREATE INDEX purchases_by_member ON purchases (member);
