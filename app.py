"""
Drone Food Delivery MVP - Flask Backend
Hyderabad, India - Customer orders, restaurant dashboard, admin panel, shared password system.
"""

import json
import os
import random
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_cors import CORS

import database as db

# Optional: Razorpay test keys (get yours from https://dashboard.razorpay.com/)
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")

# Session secret (change in production)
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "drone-food-mvp-dev-key-change-me")
CORS(app, supports_credentials=True)

# Orders that are still "active" (password must be unique among these)
ACTIVE_STATUSES = ("pending", "accepted", "preparing", "out_for_delivery")

# Simple restaurant login for MVP (restaurant_id -> PIN)
RESTAURANT_LOGINS = {
    "bawarchi": {"pin": "1111", "name": "Bawarchi Restaurant"},
    "paradise": {"pin": "2222", "name": "Paradise Biryani"},
    "chutneys": {"pin": "3333", "name": "Chutneys South Indian"},
}

RESTAURANTS = [
    {
        "id": "bawarchi",
        "name": "Bawarchi Restaurant",
        "area": "RTC Cross Roads, Hyderabad",
        "rating": 4.5,
        "menu": [
            {"id": "m1", "name": "Hyderabadi Chicken Biryani", "price": 280},
            {"id": "m2", "name": "Mutton Biryani", "price": 350},
            {"id": "m3", "name": "Double Ka Meetha", "price": 80},
            {"id": "m4", "name": "Irani Chai", "price": 30},
        ],
    },
    {
        "id": "paradise",
        "name": "Paradise Biryani",
        "area": "Secunderabad, Hyderabad",
        "rating": 4.7,
        "menu": [
            {"id": "m1", "name": "Paradise Special Biryani", "price": 320},
            {"id": "m2", "name": "Keema Samosa (2 pcs)", "price": 90},
            {"id": "m3", "name": "Qubani Ka Meetha", "price": 120},
            {"id": "m4", "name": "Lassi", "price": 60},
        ],
    },
    {
        "id": "chutneys",
        "name": "Chutneys South Indian",
        "area": "Banjara Hills, Hyderabad",
        "rating": 4.4,
        "menu": [
            {"id": "m1", "name": "Masala Dosa", "price": 120},
            {"id": "m2", "name": "Idli Sambar (2 pcs)", "price": 80},
            {"id": "m3", "name": "Filter Coffee", "price": 50},
            {"id": "m4", "name": "Pesarattu Upma", "price": 140},
        ],
    },
]


def row_to_dict(row):
    """Convert sqlite3.Row to a plain dictionary."""
    d = dict(row)
    if d.get("items"):
        try:
            d["items"] = json.loads(d["items"])
        except json.JSONDecodeError:
            pass
    return d


def generate_unique_password(cursor):
    """Generate a 4-digit password not used by any active order."""
    placeholders = ",".join("?" * len(ACTIVE_STATUSES))
    for _ in range(200):
        password = str(random.randint(1000, 9999))
        cursor.execute(
            f"""
            SELECT id FROM orders
            WHERE password = ? AND status IN ({placeholders})
            """,
            (password,) + ACTIVE_STATUSES,
        )
        if not cursor.fetchone():
            return password
    raise RuntimeError("Could not generate unique password")


def restaurant_required(f):
    """API decorator: restaurant must be logged in."""

    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("restaurant_id"):
            return jsonify({"error": "Login required", "login_required": True}), 401
        return f(*args, **kwargs)

    return decorated


def get_order_row(cursor, order_id):
    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    return cursor.fetchone()


# ---------- Page routes ----------


@app.route("/")
def customer_page():
    return render_template("index.html")


@app.route("/track")
def track_page():
    return render_template("track.html")


@app.route("/restaurant/login")
def restaurant_login_page():
    if session.get("restaurant_id"):
        return redirect(url_for("restaurant_page"))
    return render_template("restaurant_login.html")


@app.route("/restaurant")
def restaurant_page():
    if not session.get("restaurant_id"):
        return redirect(url_for("restaurant_login_page"))
    return render_template("restaurant.html")


@app.route("/admin")
def admin_page():
    return render_template("admin.html")

@app.route("/support")
def support():
    return render_template("support.html")

@app.route('/simulator')
def simulator():
    return render_template('simulator.html')

@app.route('/tracking_demo')
def tracking_demo():
    return render_template('tracking_clean.html')


# ---------- Restaurant auth ----------


@app.route("/api/restaurant/login", methods=["POST"])
def restaurant_login():
    data = request.get_json() or {}
    restaurant_id = data.get("restaurant_id", "").strip()
    pin = str(data.get("pin", "")).strip()

    creds = RESTAURANT_LOGINS.get(restaurant_id)
    if not creds or creds["pin"] != pin:
        return jsonify({"error": "Invalid restaurant or PIN"}), 401

    session["restaurant_id"] = restaurant_id
    session["restaurant_name"] = creds["name"]
    return jsonify(
        {
            "success": True,
            "restaurant_id": restaurant_id,
            "restaurant_name": creds["name"],
        }
    )


@app.route("/api/restaurant/logout", methods=["POST"])
def restaurant_logout():
    session.clear()
    return jsonify({"success": True})


@app.route("/api/restaurant/me")
def restaurant_me():
    if not session.get("restaurant_id"):
        return jsonify({"logged_in": False}), 401
    return jsonify(
        {
            "logged_in": True,
            "restaurant_id": session["restaurant_id"],
            "restaurant_name": session.get("restaurant_name"),
        }
    )


# ---------- API: Restaurants ----------


@app.route("/api/restaurants")
def get_restaurants():
    return jsonify(RESTAURANTS)


# ---------- API: Orders (only one version) ----------


@app.route("/api/orders", methods=["POST"])
def create_order():
    """
    Create order. Server assigns a unique 4-digit drone box password.
    Expects JSON fields: customer_name, customer_phone, customer_address,
    restaurant_id, items, total_amount
    """
    data = request.get_json() or {}

    required = [
        "customer_name",
        "customer_phone",
        "customer_address",
        "restaurant_id",
        "items",
        "total_amount",
    ]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"Missing field: {field}"}), 400

    restaurant = next(
        (r for r in RESTAURANTS if r["id"] == data["restaurant_id"]), None
    )
    if not restaurant:
        return jsonify({"error": "Invalid restaurant"}), 400

    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        password = generate_unique_password(cursor)
    except RuntimeError:
        conn.close()
        return jsonify({"error": "Could not generate password. Try again."}), 500

    cursor.execute(
        """
        INSERT INTO orders (
            customer_name, customer_phone, customer_address,
            restaurant_id, restaurant_name, items, total_amount,
            password, status, payment_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', 'unpaid')
        """,
        (
            data["customer_name"],
            data["customer_phone"],
            data["customer_address"],
            data["restaurant_id"],
            restaurant["name"],
            json.dumps(data["items"]),
            float(data["total_amount"]),
            password,
        ),
    )
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return jsonify(
        {
            "success": True,
            "order_id": order_id,
            "password": password,
            "message": "Order placed. Save your drone password!",
            "track_url": f"/track?order_id={order_id}&phone={data['customer_phone']}",
        }
    )


@app.route("/api/orders")
def list_orders():
    """All orders for admin — supports status, payment, and search filters."""
    status = request.args.get("status", "").strip()
    payment = request.args.get("payment", "").strip()
    search = request.args.get("q", "").strip()

    conn = db.get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM orders WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"
        params.append(status)

    if payment:
        query += " AND payment_status = ?"
        params.append(payment)

    if search:
        query += " AND (customer_name LIKE ? OR customer_phone LIKE ? OR CAST(id AS TEXT) = ?)"
        like = f"%{search}%"
        params.extend([like, like, search])

    query += " ORDER BY created_at DESC"
    cursor.execute(query, params)
    orders = [row_to_dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(orders)


@app.route("/api/orders/track")
def track_order():
    """Customer tracking: order ID + phone number."""
    order_id = request.args.get("order_id", "").strip()
    phone = request.args.get("phone", "").strip()

    if not order_id or not phone:
        return jsonify({"error": "order_id and phone are required"}), 400

    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM orders WHERE id = ? AND customer_phone = ?",
        (order_id, phone),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "Order not found. Check ID and phone."}), 404

    order = row_to_dict(row)
    # Do not expose full password on tracking page (customer already has it from checkout)
    order.pop("password", None)
    return jsonify(order)


@app.route("/api/restaurant/stats")
@restaurant_required
def restaurant_stats():
    """Today's order count and revenue for logged-in restaurant."""
    restaurant_id = session["restaurant_id"]
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT COUNT(*), COALESCE(SUM(total_amount), 0)
        FROM orders
        WHERE restaurant_id = ?
        AND date(created_at) = date('now')
        """,
        (restaurant_id,),
    )
    row = cursor.fetchone()
    today_orders = row[0]
    today_revenue = row[1]

    placeholders = ",".join("?" * len(ACTIVE_STATUSES))
    cursor.execute(
        f"""
        SELECT COUNT(*) FROM orders
        WHERE restaurant_id = ? AND status IN ({placeholders})
        """,
        (restaurant_id,) + ACTIVE_STATUSES,
    )
    active_orders = cursor.fetchone()[0]
    conn.close()

    return jsonify(
        {
            "today_orders": today_orders,
            "today_revenue": round(float(today_revenue), 2),
            "active_orders": active_orders,
            "drone_status": "Ready",
        }
    )


@app.route("/api/orders/pending")
@restaurant_required
def pending_orders():
    """Active orders for logged-in restaurant only."""
    restaurant_id = session["restaurant_id"]
    conn = db.get_connection()
    cursor = conn.cursor()
    placeholders = ",".join("?" * len(ACTIVE_STATUSES))
    cursor.execute(
        f"""
        SELECT * FROM orders
        WHERE restaurant_id = ?
        AND status IN ({placeholders})
        ORDER BY created_at DESC
        """,
        (restaurant_id,) + ACTIVE_STATUSES,
    )
    orders = [row_to_dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(orders)


@app.route("/api/orders/<int:order_id>", methods=["PATCH"])
@restaurant_required
def update_order(order_id):
    """
    Restaurant: accept, decline, or advance status.
    Blocks drone dispatch and delivery if payment is not 'paid'.
    """
    data = request.get_json() or {}
    action = data.get("action")

    status_map = {
        "accept": "accepted",
        "decline": "declined",
        "preparing": "preparing",
        "out_for_delivery": "out_for_delivery",
        "delivered": "delivered",
    }

    if action not in status_map:
        return jsonify({"error": "Invalid action"}), 400

    new_status = status_map[action]
    requires_payment = ("out_for_delivery", "delivered")

    conn = db.get_connection()
    cursor = conn.cursor()
    row = get_order_row(cursor, order_id)

    if not row:
        conn.close()
        return jsonify({"error": "Order not found"}), 404

    if row["restaurant_id"] != session["restaurant_id"]:
        conn.close()
        return jsonify({"error": "Not your order"}), 403

    if action in requires_payment and row["payment_status"] != "paid":
        conn.close()
        return jsonify(
            {
                "error": "Payment pending. Cannot send drone or mark delivered until paid.",
            }
        ), 400

    cursor.execute(
        "UPDATE orders SET status = ? WHERE id = ?",
        (new_status, order_id),
    )
    conn.commit()
    conn.close()

    return jsonify({"success": True, "status": new_status})


@app.route("/api/orders/<int:order_id>/password")
@restaurant_required
def get_order_password(order_id):
    """Restaurant views drone box password (only for their orders)."""
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT password, customer_name, status, restaurant_id, payment_status FROM orders WHERE id = ?",
        (order_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "Order not found"}), 404

    if row["restaurant_id"] != session["restaurant_id"]:
        return jsonify({"error": "Not your order"}), 403

    return jsonify(
        {
            "order_id": order_id,
            "password": row["password"],
            "customer_name": row["customer_name"],
            "status": row["status"],
            "payment_status": row["payment_status"],
        }
    )


@app.route("/api/orders/<int:order_id>/refund", methods=["POST"])
def admin_refund(order_id):
    """Admin: mark order payment as refunded (simple MVP action)."""
    conn = db.get_connection()
    cursor = conn.cursor()
    row = get_order_row(cursor, order_id)
    if not row:
        conn.close()
        return jsonify({"error": "Order not found"}), 404

    cursor.execute(
        "UPDATE orders SET payment_status = 'refunded' WHERE id = ?",
        (order_id,),
    )
    conn.commit()
    conn.close()
    return jsonify({"success": True, "payment_status": "refunded"})


@app.route("/api/verify-password", methods=["POST"])
def verify_password():
    """
    Customer unlocks drone box at delivery.
    Requires correct password, paid status, and order out for delivery.
    """
    data = request.get_json() or {}
    order_id = data.get("order_id")
    password = str(data.get("password", "")).strip()

    if not order_id or not password:
        return jsonify({"error": "order_id and password required"}), 400

    conn = db.get_connection()
    cursor = conn.cursor()
    row = get_order_row(cursor, order_id)
    conn.close()

    if not row:
        return jsonify({"error": "Order not found"}), 404

    if row["payment_status"] != "paid":
        return jsonify(
            {"success": False, "message": "Payment pending. Complete payment first."}
        ), 402

    if row["status"] not in ("out_for_delivery", "delivered"):
        return jsonify(
            {
                "success": False,
                "message": f"Drone not ready yet. Status: {row['status']}",
            }
        ), 400

    if row["password"] == password:
        return jsonify(
            {
                "success": True,
                "message": "Password correct! Drone box unlocked. Enjoy your meal!",
            }
        )

    return jsonify({"success": False, "message": "Wrong password. Try again."}), 401


# ---------- Razorpay (test mode) ----------


@app.route("/api/razorpay-config")
def razorpay_config():
    return jsonify(
        {
            "key_id": RAZORPAY_KEY_ID,
            "demo_mode": not (RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET),
        }
    )


@app.route("/api/create-razorpay-order", methods=["POST"])
def create_razorpay_order():
    data = request.get_json() or {}
    amount = int(float(data.get("amount", 0)) * 100)
    order_id = data.get("order_id")

    if amount <= 0:
        return jsonify({"error": "Invalid amount"}), 400

    if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
        try:
            import razorpay

            client = razorpay.Client(
                auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
            )
            rp_order = client.order.create(
                {
                    "amount": amount,
                    "currency": "INR",
                    "receipt": f"order_{order_id}_{random.randint(1000, 9999)}",
                }
            )
            razorpay_order_id = rp_order["id"]

            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE orders SET razorpay_order_id = ? WHERE id = ?",
                (razorpay_order_id, order_id),
            )
            conn.commit()
            conn.close()

            return jsonify(
                {
                    "razorpay_order_id": razorpay_order_id,
                    "amount": amount,
                    "currency": "INR",
                    "key_id": RAZORPAY_KEY_ID,
                }
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # Demo mode: mark paid immediately for local testing
    demo_id = f"demo_order_{order_id}_{datetime.now().strftime('%H%M%S')}"
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE orders SET razorpay_order_id = ?, payment_status = 'paid' WHERE id = ?",
        (demo_id, order_id),
    )
    conn.commit()
    conn.close()

    return jsonify(
        {
            "razorpay_order_id": demo_id,
            "amount": amount,
            "currency": "INR",
            "key_id": "",
            "demo_mode": True,
        }
    )


@app.route("/api/verify-payment", methods=["POST"])
def verify_payment():
    data = request.get_json() or {}
    order_id = data.get("order_id")
    razorpay_order_id = data.get("razorpay_order_id")
    razorpay_payment_id = data.get("razorpay_payment_id")
    razorpay_signature = data.get("razorpay_signature")

    if data.get("demo_mode"):
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE orders SET payment_status = 'paid',
            razorpay_payment_id = 'demo_payment'
            WHERE id = ?
            """,
            (order_id,),
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Demo payment recorded"})

    if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
        return jsonify({"error": "Missing payment fields"}), 400

    if RAZORPAY_KEY_SECRET:
        try:
            import razorpay

            client = razorpay.Client(
                auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
            )
            client.utility.verify_payment_signature(
                {
                    "razorpay_order_id": razorpay_order_id,
                    "razorpay_payment_id": razorpay_payment_id,
                    "razorpay_signature": razorpay_signature,
                }
            )

            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE orders SET payment_status = 'paid',
                razorpay_payment_id = ?
                WHERE id = ?
                """,
                (razorpay_payment_id, order_id),
            )
            conn.commit()
            conn.close()

            return jsonify({"success": True, "message": "Payment verified"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return jsonify({"error": "Razorpay not configured"}), 500


# Create SQLite tables on startup
db.init_db()

if __name__ == "__main__":
    print("\n=== Drone Food Delivery MVP ===")
    print("DroneDine:  http://127.0.0.1:5000/")
    print("Track:      http://127.0.0.1:5000/track")
    print("Restaurant: http://127.0.0.1:5000/restaurant/login")
    print("Admin:      http://127.0.0.1:5000/admin")
    print("\nRestaurant PINs: bawarchi=1111, paradise=2222, chutneys=3333")
    print("==============================\n")
    app.run(debug=True, host="127.0.0.1", port=5000)
