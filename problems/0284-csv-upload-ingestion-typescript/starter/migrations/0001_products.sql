-- Up Migration
-- A product's stock: the sum of what every loaded delivery line brought, and the description of
-- the last line loaded for it.
CREATE TABLE products (
  sku text PRIMARY KEY,
  description text NOT NULL,
  quantity bigint NOT NULL CHECK (quantity >= 0)
);
