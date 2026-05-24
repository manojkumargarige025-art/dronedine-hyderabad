"""
SQLite database setup for Drone Food Delivery MVP.
Run once at startup to create tables if they don't exist.
"""

import sqlite3
import os

# Database file lives in the project folder
DB_PATH = os.path.join(os.path.dirname(__file__), "orders.db")


def get_connection():
    """Open a connection to SQLite. Row factory lets us access columns by name."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the orders table if it does not exist yet."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            customer_address TEXT NOT NULL,
            restaurant_id TEXT NOT NULL,
            restaurant_name TEXT NOT NULL,
            items TEXT NOT NULL,
            total_amount REAL NOT NULL,
            password TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            payment_status TEXT NOT NULL DEFAULT 'unpaid',
            razorpay_order_id TEXT,
            razorpay_payment_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.commit()
    conn.close()
    print("Database ready:", DB_PATH)
