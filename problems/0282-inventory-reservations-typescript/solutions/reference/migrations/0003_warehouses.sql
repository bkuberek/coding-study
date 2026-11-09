-- Up Migration
-- Stock moves from one number per product to one per warehouse. Every product's stock today goes
-- to main, north starts empty, and every hold already taken was taken from main. One transaction,
-- as node-pg-migrate runs each file, so a failure leaves the old schema whole.
CREATE TABLE warehouses (
    code text PRIMARY KEY
);

INSERT INTO warehouses (code) VALUES ('main'), ('north');

CREATE TABLE warehouse_stock (
    warehouse text NOT NULL REFERENCES warehouses (code),
    sku text NOT NULL REFERENCES products (sku),
    on_hand integer NOT NULL CHECK (on_hand >= 0),
    PRIMARY KEY (warehouse, sku)
);

INSERT INTO warehouse_stock (warehouse, sku, on_hand)
SELECT warehouses.code, products.sku, CASE WHEN warehouses.code = 'main' THEN products.stock ELSE 0 END
FROM warehouses CROSS JOIN products;

ALTER TABLE reservation_items
    ADD COLUMN warehouse text NOT NULL DEFAULT 'main' REFERENCES warehouses (code);

CREATE INDEX reservation_items_by_place ON reservation_items (warehouse, sku);

ALTER TABLE products DROP COLUMN stock;
