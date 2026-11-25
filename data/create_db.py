"""Creates retail.db: a sample retail client database (40 customers, 20 products, ~3,000 orders).

Run:  python data/create_db.py            (or: python data/create_db.py --orders 50000 for a bigger dataset)
A fixed random seed means everyone gets exactly the same data, so benchmark results are repeatable.
"""
import argparse
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).parent
DEFAULT_DB = HERE / "retail.db"

CATALOG = {
    "Electronics": [("Wireless Earbuds", 2499), ("Smart Watch", 4999),
                    ("Power Bank", 1299), ("Bluetooth Speaker", 1999)],
    "Home & Kitchen": [("Non-stick Pan", 899), ("Electric Kettle", 1199),
                       ("Dinner Set", 2199), ("Storage Containers", 499)],
    "Fashion": [("Cotton T-Shirt", 599), ("Denim Jeans", 1499),
                ("Running Shoes", 2799), ("Backpack", 1099)],
    "Grocery": [("Basmati Rice 5kg", 649), ("Green Tea", 349),
                ("Dry Fruits Mix", 999), ("Olive Oil", 799)],
    "Beauty": [("Face Wash", 249), ("Sunscreen", 449),
               ("Hair Oil", 199), ("Perfume", 1599)],
}
CITIES = ["Jaipur", "Delhi", "Mumbai", "Bengaluru", "Pune", "Hyderabad", "Chennai", "Kolkata"]
FIRST = ["Aarav", "Diya", "Rohan", "Isha", "Kabir", "Ananya", "Vivaan", "Meera", "Arjun", "Sara"]
LAST = ["Sharma", "Verma", "Gupta", "Iyer"]


def create_db(path=DEFAULT_DB, n_orders=3000, seed=42):
    path = Path(path)
    if path.exists():
        path.unlink()
    rng = random.Random(seed)
    conn = sqlite3.connect(path)
    conn.executescript((HERE / "schema.sql").read_text())

    for i in range(40):
        conn.execute("INSERT INTO customers VALUES (?, ?, ?, ?, ?)",
                     (i + 1, f"{FIRST[i % 10]} {LAST[i // 10]}", f"customer{i + 1}@example.com",
                      rng.choice(CITIES), str(date(2025, 1, 1) + timedelta(days=rng.randint(0, 364)))))

    prices = {}
    pid = 1
    for category, items in CATALOG.items():
        for name, price in items:
            conn.execute("INSERT INTO products VALUES (?, ?, ?, ?, ?)",
                         (pid, f"SKU-{pid:03d}", name, category, price))
            conn.execute("INSERT INTO inventory VALUES (?, ?, ?)",
                         (pid, rng.choice([5, 12, 18] + list(range(30, 200, 10))), 20))
            prices[pid] = price
            pid += 1

    start, days = date(2026, 1, 1), 323            # Jan 1 - Nov 19, 2026
    item_id = 1
    for order_id in range(1, n_orders + 1):
        order_date = start + timedelta(days=int(days * rng.random() ** 0.8))   # business is growing
        status = rng.choices(["DELIVERED", "SHIPPED", "PLACED", "CANCELLED"], [70, 15, 9, 6])[0]
        total = 0
        lines = []
        for product_id in rng.sample(range(1, 21), rng.randint(1, 3)):
            qty = rng.randint(1, 3)
            total += qty * prices[product_id]
            lines.append((item_id, order_id, product_id, qty, prices[product_id]))
            item_id += 1
        conn.execute("INSERT INTO orders VALUES (?, ?, ?, ?, ?)",
                     (order_id, rng.randint(1, 40), str(order_date), status, total))
        conn.executemany("INSERT INTO order_items VALUES (?, ?, ?, ?, ?)", lines)

    conn.commit()
    conn.close()
    print(f"Created {path} with 40 customers, 20 products, {n_orders} orders")
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--orders", type=int, default=3000)
    parser.add_argument("--db", default=str(DEFAULT_DB))
    args = parser.parse_args()
    create_db(args.db, args.orders)
