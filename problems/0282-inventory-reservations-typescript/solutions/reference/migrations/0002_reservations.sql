-- Up Migration
-- A reservation holds stock until it is released or its hold runs out. Nothing here changes a
-- product's stock: what is available is the stock minus what active holds keep.
CREATE TABLE reservations (
    order_id text PRIMARY KEY,
    status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'released')),
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE reservation_items (
    order_id text NOT NULL REFERENCES reservations (order_id),
    sku text NOT NULL REFERENCES products (sku),
    quantity integer NOT NULL CHECK (quantity > 0),
    PRIMARY KEY (order_id, sku)
);

CREATE INDEX reservation_items_by_sku ON reservation_items (sku);
CREATE INDEX active_reservations ON reservations (expires_at) WHERE status = 'active';
