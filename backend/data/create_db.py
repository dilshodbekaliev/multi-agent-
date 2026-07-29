"""
Creates a small mock company database for the Text-to-SQL agent (F5).
Tables: customers, orders, products.
Realistic enough to answer questions like:
  - "How many customers churned last quarter?"
  - "What's the average order value?"
  - "Which product category had the most revenue?"

Run:
    python create_db.py
"""
import sqlite3
import random
from datetime import date, timedelta

DB_PATH = "company.db"

random.seed(42)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.executescript("""
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS products;

CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    country TEXT NOT NULL,
    signup_date TEXT NOT NULL,
    is_churned INTEGER NOT NULL DEFAULT 0,   -- 1 = churned
    churn_date TEXT
);

CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    unit_price REAL NOT NULL
);

CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    order_date TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);
""")

countries = ["Uzbekistan", "Kazakhstan", "Kyrgyzstan", "Tajikistan", "Turkey", "Russia"]
categories = {
    "Electronics": ["Wireless Mouse", "Mechanical Keyboard", "USB-C Hub", "Webcam", "Monitor Stand"],
    "Software": ["Analytics Suite License", "Cloud Backup Plan", "Design Toolkit License"],
    "Furniture": ["Office Chair", "Standing Desk", "Desk Lamp"],
    "Accessories": ["Laptop Sleeve", "Cable Organizer", "Phone Stand"],
}

# products
product_id = 1
products = []
for cat, items in categories.items():
    for item in items:
        price = round(random.uniform(9.99, 349.99), 2)
        products.append((product_id, item, cat, price))
        product_id += 1
cur.executemany("INSERT INTO products VALUES (?,?,?,?)", products)

# customers, spread over the last 2 years, ~18% churned
today = date(2026, 7, 27)
customers = []
for cid in range(1, 201):
    signup = today - timedelta(days=random.randint(30, 730))
    is_churned = 1 if random.random() < 0.18 else 0
    churn_date = None
    if is_churned:
        churn = signup + timedelta(days=random.randint(60, 700))
        if churn > today:
            churn = today - timedelta(days=random.randint(1, 90))
        churn_date = churn.isoformat()
    customers.append((
        cid,
        f"Customer {cid}",
        random.choice(countries),
        signup.isoformat(),
        is_churned,
        churn_date,
    ))
cur.executemany("INSERT INTO customers VALUES (?,?,?,?,?,?)", customers)

# orders: each active-ish customer gets a handful of orders
orders = []
order_id = 1
for c in customers:
    cid, _, _, signup_str, is_churned, churn_date = c
    signup = date.fromisoformat(signup_str)
    end = date.fromisoformat(churn_date) if churn_date else today
    n_orders = random.randint(1, 12)
    for _ in range(n_orders):
        span = max((end - signup).days, 1)
        order_date = signup + timedelta(days=random.randint(0, span))
        product = random.choice(products)
        orders.append((
            order_id,
            cid,
            product[0],
            random.randint(1, 5),
            order_date.isoformat(),
        ))
        order_id += 1
cur.executemany("INSERT INTO orders VALUES (?,?,?,?,?)", orders)

conn.commit()

# sanity check
cur.execute("SELECT COUNT(*) FROM customers WHERE is_churned=1")
churned = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM orders")
n_orders = cur.fetchone()[0]
print(f"Created {DB_PATH}")
print(f"  customers: {len(customers)} ({churned} churned)")
print(f"  products:  {len(products)}")
print(f"  orders:    {n_orders}")

conn.close()
