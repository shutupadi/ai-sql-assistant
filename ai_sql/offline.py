"""Offline fallback: a simple keyword-rule SQL generator, so the app works without an API key.

It recognises the common retail questions (revenue, top customers / products, by month / category /
city, low stock, order status) and fills in filters it finds in the question (city, category, status,
"top N"). It is deliberately simple, and the benchmark shows where it is wrong.
"""
import re

CITIES = ["jaipur", "delhi", "mumbai", "bengaluru", "pune", "hyderabad", "chennai", "kolkata"]
CATEGORIES = {"electronics": "Electronics", "home": "Home & Kitchen", "kitchen": "Home & Kitchen",
              "fashion": "Fashion", "grocery": "Grocery", "beauty": "Beauty"}
STATUSES = {"cancelled": "CANCELLED", "canceled": "CANCELLED", "delivered": "DELIVERED",
            "shipped": "SHIPPED", "placed": "PLACED", "pending": "PLACED"}
NOT_CANCELLED = "o.status <> 'CANCELLED'"


def _top_n(q, default=5):
    match = re.search(r"\b(\d+)\b", q)
    return int(match.group(1)) if match else default


def _filters(q, revenue=True):
    """WHERE conditions for any city / category / status mentioned in the question."""
    where = []
    status = next((s for word, s in STATUSES.items() if word in q), None)
    if status:
        where.append(f"o.status = '{status}'")
    elif revenue:
        where.append(NOT_CANCELLED)                    # cancelled orders are never revenue
    city = next((c for c in CITIES if c in q), None)
    if city:
        where.append(f"c.city = '{city.title()}'")
    category = next((cat for word, cat in CATEGORIES.items() if word in q), None)
    return where, city, category


def _where(conditions):
    return ("WHERE " + " AND ".join(conditions)) if conditions else ""


def offline_sql(question):
    q = question.lower()
    where, city, category = _filters(q)
    has = lambda *words: any(w in q for w in words)      # noqa: E731

    if has("stock", "reorder"):
        return ("SELECT p.name, p.category, i.quantity_on_hand, i.reorder_level\n"
                "FROM inventory i JOIN products p ON p.product_id = i.product_id\n"
                "WHERE i.quantity_on_hand <= i.reorder_level\n"
                "ORDER BY i.quantity_on_hand")

    if has("status"):
        return ("SELECT status, COUNT(*) AS orders\nFROM orders\nGROUP BY status\nORDER BY orders DESC")

    if has("month", "monthly", "trend"):
        return ("SELECT strftime('%Y-%m', o.order_date) AS month, ROUND(SUM(o.total_amount), 2) AS revenue\n"
                "FROM orders o JOIN customers c ON c.customer_id = o.customer_id\n"
                f"{_where(where)}\nGROUP BY month\nORDER BY month")

    if has("customer") and has("top", "best", "most", "highest", "biggest"):
        return ("SELECT c.name, c.city, COUNT(o.order_id) AS orders, ROUND(SUM(o.total_amount), 2) AS total_spend\n"
                "FROM customers c JOIN orders o ON o.customer_id = c.customer_id\n"
                f"{_where(where)}\nGROUP BY c.customer_id, c.name, c.city\n"
                f"ORDER BY total_spend DESC\nLIMIT {_top_n(q)}")

    if has("product") and has("top", "best", "most", "highest", "selling"):
        if category:
            where.append(f"p.category = '{category}'")
        by_units = has("units", "quantity", "sold")
        measure = ("SUM(oi.quantity) AS units_sold" if by_units
                   else "ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue")
        return (f"SELECT p.name, p.category, {measure}\n"
                "FROM order_items oi\nJOIN orders o ON o.order_id = oi.order_id\n"
                "JOIN products p ON p.product_id = oi.product_id\n"
                "JOIN customers c ON c.customer_id = o.customer_id\n"
                f"{_where(where)}\nGROUP BY p.product_id, p.name, p.category\n"
                f"ORDER BY {'units_sold' if by_units else 'revenue'} DESC\nLIMIT {_top_n(q)}")

    if has("category", "categories"):
        return ("SELECT p.category, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue\n"
                "FROM order_items oi\nJOIN orders o ON o.order_id = oi.order_id\n"
                "JOIN products p ON p.product_id = oi.product_id\n"
                "JOIN customers c ON c.customer_id = o.customer_id\n"
                f"{_where(where)}\nGROUP BY p.category\nORDER BY revenue DESC")

    if has("city", "cities"):
        return ("SELECT c.city, COUNT(o.order_id) AS orders, ROUND(SUM(o.total_amount), 2) AS revenue\n"
                "FROM orders o JOIN customers c ON c.customer_id = o.customer_id\n"
                f"{_where(where)}\nGROUP BY c.city\nORDER BY revenue DESC")

    if has("average order", "avg order", "aov"):
        return ("SELECT ROUND(AVG(o.total_amount), 2) AS avg_order_value\n"
                "FROM orders o JOIN customers c ON c.customer_id = o.customer_id\n"
                f"{_where(where)}")

    if has("how many customers", "number of customers", "count of customers"):
        return ("SELECT COUNT(*) AS customers\nFROM customers c\n"
                + (f"WHERE c.city = '{city.title()}'" if city else "")).strip()

    if has("how many orders", "number of orders", "count of orders", "total orders"):
        where, _, _ = _filters(q, revenue=False)
        return ("SELECT COUNT(*) AS orders\n"
                "FROM orders o JOIN customers c ON c.customer_id = o.customer_id\n"
                f"{_where(where)}").strip()

    if has("revenue", "sales", "sold"):
        if category:
            where.append(f"p.category = '{category}'")
            return ("SELECT ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue\n"
                    "FROM order_items oi\nJOIN orders o ON o.order_id = oi.order_id\n"
                    "JOIN products p ON p.product_id = oi.product_id\n"
                    "JOIN customers c ON c.customer_id = o.customer_id\n"
                    f"{_where(where)}")
        return ("SELECT ROUND(SUM(o.total_amount), 2) AS revenue\n"
                "FROM orders o JOIN customers c ON c.customer_id = o.customer_id\n"
                f"{_where(where)}")

    return None                                          # not understood
