-- Retail database used by the SQL assistant (same model as the order-analytics project).
-- customers 1---* orders 1---* order_items *---1 products 1---1 inventory

CREATE TABLE customers (
    customer_id  INTEGER PRIMARY KEY,
    name         TEXT NOT NULL,
    email        TEXT NOT NULL UNIQUE,
    city         TEXT NOT NULL,
    signup_date  TEXT NOT NULL            -- YYYY-MM-DD
);

CREATE TABLE products (
    product_id   INTEGER PRIMARY KEY,
    sku          TEXT NOT NULL UNIQUE,
    name         TEXT NOT NULL,
    category     TEXT NOT NULL,
    unit_price   REAL NOT NULL CHECK (unit_price > 0)
);

CREATE TABLE inventory (
    product_id        INTEGER PRIMARY KEY REFERENCES products(product_id),
    quantity_on_hand  INTEGER NOT NULL CHECK (quantity_on_hand >= 0),
    reorder_level     INTEGER NOT NULL
);

CREATE TABLE orders (
    order_id      INTEGER PRIMARY KEY,
    customer_id   INTEGER NOT NULL REFERENCES customers(customer_id),
    order_date    TEXT NOT NULL,           -- YYYY-MM-DD
    status        TEXT NOT NULL,           -- PLACED, SHIPPED, DELIVERED, CANCELLED
    total_amount  REAL NOT NULL
);

CREATE TABLE order_items (
    order_item_id  INTEGER PRIMARY KEY,
    order_id       INTEGER NOT NULL REFERENCES orders(order_id),
    product_id     INTEGER NOT NULL REFERENCES products(product_id),
    quantity       INTEGER NOT NULL CHECK (quantity > 0),
    unit_price     REAL NOT NULL           -- price at the time of sale
);

-- Feedback loop: every thumbs up / down from the app is stored here.
CREATE TABLE query_feedback (
    feedback_id  INTEGER PRIMARY KEY,
    question     TEXT NOT NULL,
    sql          TEXT NOT NULL,
    rating       INTEGER NOT NULL CHECK (rating IN (1, -1)),   -- 1 = good, -1 = bad
    comment      TEXT,
    source       TEXT,                     -- openai / offline / approved
    created_at   TEXT NOT NULL
);
