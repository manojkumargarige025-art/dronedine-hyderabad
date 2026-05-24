# Drone Food Delivery MVP — Hyderabad

A beginner-friendly food delivery MVP for a drone startup: customer ordering, Razorpay test payments, shared 4-digit drone box password, restaurant dashboard, and admin panel.

**Stack:** Python 3.8+ · Flask · SQLite · HTML/CSS/JavaScript

---

## What’s included

| Page | URL | Purpose |
|------|-----|---------|
| Customer | http://127.0.0.1:5000/ | Browse restaurants, cart, checkout, pay |
| Track order | http://127.0.0.1:5000/track | Live status with order ID + phone |
| Restaurant | http://127.0.0.1:5000/restaurant/login | PIN login, live orders, accept/decline |
| Admin | http://127.0.0.1:5000/admin | View/filter/search orders, refund |

**Password flow (unique per order)**

1. Server assigns a **unique 4-digit password** when the order is created.
2. Customer sees it after payment; restaurant sees it on the dashboard (after payment).
3. Restaurant cannot **Send Drone** or mark **Delivered** until payment is `paid`.
4. Customer enters the password when the drone arrives (only if status is out for delivery).

**Restaurant login (demo PINs)**

| Restaurant | ID | PIN |
|--------------|-----|-----|
| Bawarchi | `bawarchi` | `1111` |
| Paradise | `paradise` | `2222` |
| Chutneys | `chutneys` | `3333` |

---

## Requirements

- Windows 10/11 (or any OS with Python)
- Python 3.8 or newer
- ~8GB RAM is enough
- Internet only needed for Razorpay checkout script (demo mode works offline after first load)

---

## Quick start (Windows)

### 1. Open terminal in project folder

```powershell
cd "d:\Drone Delivery"
```

### 2. Create virtual environment (recommended)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks scripts, run once:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Run the server

```powershell
python app.py
```

You should see:

```
=== Drone Food Delivery MVP ===
Customer:   http://127.0.0.1:5000/
Restaurant: http://127.0.0.1:5000/restaurant
Admin:      http://127.0.0.1:5000/admin
```

Open those URLs in your browser (Chrome or Edge recommended).

---

## Test the full flow

1. **Customer** (`/`) — Pick a restaurant (e.g. Bawarchi), add items, open cart, checkout.
2. Enter name, phone, and Hyderabad address. Password is auto-generated after checkout.
3. **Payment** — Without Razorpay keys, demo mode marks the order paid automatically.
4. **Track** (`/track`) — Enter order ID + phone to see live status.
5. **Restaurant** — Login at `/restaurant/login` with PIN `1111` for Bawarchi. Accept order → Preparing → Send Drone (only if paid).
6. **Customer unlock** — After drone is sent, enter order ID + password on the home page.
7. **Admin** — Filter by status/payment, search by name/phone/ID, refund paid orders.

---

## Razorpay test mode (optional)

By default, payments run in **demo mode** so you can test without a Razorpay account.

To use real Razorpay **test** checkout:

1. Sign up at [https://dashboard.razorpay.com/](https://dashboard.razorpay.com/)
2. Go to **Settings → API Keys** and generate **Test** keys.
3. In PowerShell (same session before `python app.py`):

```powershell
$env:RAZORPAY_KEY_ID = "rzp_test_xxxxxxxx"
$env:RAZORPAY_KEY_SECRET = "your_secret_here"
python app.py
```

Use Razorpay test cards from their docs (e.g. card `4111 1111 1111 1111`, any future expiry, any CVV).

---

## Project structure

```
Drone Delivery/
├── app.py              # Flask server + API routes
├── database.py         # SQLite setup
├── requirements.txt
├── orders.db           # Created automatically on first run
├── README.md
├── templates/
│   ├── index.html      # Customer page
│   ├── restaurant.html
│   └── admin.html
└── static/
    ├── css/style.css
    └── js/
        ├── customer.js
        ├── restaurant.js
        └── admin.js
```

---

## API overview (for learning)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/restaurants` | Hardcoded restaurant menus |
| POST | `/api/orders` | Create order + password |
| GET | `/api/orders` | All orders (admin) |
| GET | `/api/orders/pending` | Active orders (restaurant poll) |
| PATCH | `/api/orders/<id>` | Accept / decline / status updates |
| POST | `/api/verify-password` | Customer unlock at delivery |
| POST | `/api/create-razorpay-order` | Start payment |
| POST | `/api/verify-payment` | Confirm payment |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `python` not found | Install Python from [python.org](https://www.python.org/downloads/) and check “Add to PATH” |
| Port 5000 in use | Change `port=5000` in `app.py` last line to `5001` |
| Cart / orders not updating | Hard refresh browser (Ctrl+F5) |
| Razorpay popup doesn’t open | Check `RAZORPAY_KEY_ID` is set; or use demo mode (no keys) |

---

## Next steps (ideas)

- Map real GPS for drone routing
- SMS OTP instead of plain password
- Separate login per restaurant
- WebSockets instead of polling for “real-time”

---

Built for MVP demos in **Hyderabad, India**. Not production-hardened — use test keys only.

---

## Push to GitHub

This project is ready for GitHub. In PowerShell:

```powershell
cd "d:\Drone Delivery"
gh auth login
gh repo create dronedine-hyderabad --public --source=. --remote=origin --push --description "Drone food delivery MVP - Flask, Hyderabad"
```

Replace `dronedine-hyderabad` with your preferred repo name. If the repo already exists on GitHub:

```powershell
git remote add origin https://github.com/YOUR_USERNAME/dronedine-hyderabad.git
git push -u origin main
```
