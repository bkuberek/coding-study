-- Up Migration
-- The shop's catalog as it stands, and the problem's: leave this file as it is and add your own
-- migrations after it. Grading loads more products into this table before your migrations run.
CREATE TABLE products (
    sku text PRIMARY KEY,
    name text NOT NULL,
    stock integer NOT NULL
);

INSERT INTO products (sku, name, stock) VALUES
    ('lamp', 'Desk lamp', 3),
    ('desk', 'Standing desk', 2),
    ('chair', 'Office chair', 40),
    ('mug', 'Coffee mug', 40);
