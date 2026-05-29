"""
DroneDine - Complete Backend with User Auth, Orders, Drone Tracking,
Admin/Restaurant Dashboards, Manager Dashboard, Rider App, and Drone Integration
"""
import os
import json
import random
import threading
import time
import urllib.request
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
from flask_sqlalchemy import SQLAlchemy

# ==================== CONFIGURATION ====================
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dronedine-super-secret-key-change-me")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dronedine.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
CORS(app, supports_credentials=True)
db = SQLAlchemy(app)

app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

MAPBOX_TOKEN = "pk.eyJ1IjoibWFub2oyNTgwOCIsImEiOiJjbXBsZ3B3NmoxYzJmMnFzbHV6Zmt1NnNwIn0.hzkSfnkPO_KRL3urJbFtxA"

# ==================== MODELS ====================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    addresses = db.Column(db.Text, default='[]')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    orders = db.relationship('Order', backref='user', lazy=True)

class Restaurant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    cuisine = db.Column(db.String(50))
    rating = db.Column(db.Float, default=4.0)
    delivery_time = db.Column(db.Integer, default=20)
    is_active = db.Column(db.Boolean, default=True)
    image_url = db.Column(db.String(200))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    menu = db.relationship('MenuItem', backref='restaurant', lazy=True)

class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200), default='Delicious fresh food')
    category = db.Column(db.String(50))
    image_url = db.Column(db.String(200))
    is_veg = db.Column(db.Boolean, default=True)

class Rider(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=False)
    current_lat = db.Column(db.Float, default=0.0)
    current_lng = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    zone = db.Column(db.String(50))
    manager_id = db.Column(db.Integer, db.ForeignKey('manager.id'))
    current_order_id = db.Column(db.Integer)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

class Manager(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True)
    phone = db.Column(db.String(10))
    password_hash = db.Column(db.String(200))
    zone = db.Column(db.String(50))
    status = db.Column(db.String(20), default='online')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    riders = db.relationship('Rider', backref='manager', lazy=True)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    rider_id = db.Column(db.Integer, db.ForeignKey('rider.id'), nullable=True)
    items = db.Column(db.Text, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    unlock_code = db.Column(db.String(4), nullable=False)
    status = db.Column(db.String(50), default='pending')
    delivery_lat = db.Column(db.Float, default=17.4116)
    delivery_lng = db.Column(db.Float, default=78.3400)
    delivery_address = db.Column(db.String(200), default='Gachibowli, Hyderabad')
    drone_id = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    delivered_at = db.Column(db.DateTime)
    manager_id = db.Column(db.Integer, db.ForeignKey('manager.id'))
    zone = db.Column(db.String(50))
    delivery_type = db.Column(db.String(20), default='drone')
    delivery_stage = db.Column(db.String(30))
    support_status = db.Column(db.String(20), default='none')

class DroneTracking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    altitude = db.Column(db.Float, default=0)
    speed = db.Column(db.Float, default=0)
    battery = db.Column(db.Integer, default=100)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class DeliveryStage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    stage = db.Column(db.String(30))
    status = db.Column(db.String(20), default='pending')
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    drone_flight_id = db.Column(db.String(50))

class SupportTicket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    rider_id = db.Column(db.Integer, db.ForeignKey('rider.id'))
    manager_id = db.Column(db.Integer, db.ForeignKey('manager.id'))
    issue_type = db.Column(db.String(50))
    message = db.Column(db.Text)
    priority = db.Column(db.String(20), default='medium')
    status = db.Column(db.String(20), default='open')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)

class Drone(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    drone_id = db.Column(db.String(20), unique=True)
    battery = db.Column(db.Integer, default=100)
    status = db.Column(db.String(20), default='idle')
    current_order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    zone = db.Column(db.String(50))
    last_lat = db.Column(db.Float, default=0.0)
    last_lng = db.Column(db.Float, default=0.0)
    payload_lock = db.Column(db.Boolean, default=False)

# ==================== HELPER FUNCTIONS ====================
def generate_unlock_code():
    return str(random.randint(1000, 9999))

def calculate_co2_saved(orders):
    delivered = [o for o in orders if o.status == 'delivered']
    return len(delivered) * 0.065

# ==================== ROUTES: AUTH (Customer) ====================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form.get('phone')
        if not phone or len(phone) != 10:
            return render_template('login.html', error="Invalid phone number (10 digits required)")
        session['login_phone'] = phone
        session['login_otp'] = "123456"
        print(f"[DEMO] OTP for {phone}: 123456")
        return redirect(url_for('verify_otp'))
    return render_template('login.html')

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        entered_otp = request.form.get('otp')
        expected_otp = session.get('login_otp')
        phone = session.get('login_phone')
        if not phone:
            return render_template('verify_otp.html', error="Session expired. Please login again.")
        if str(entered_otp) == str(expected_otp) or str(entered_otp) == "123456":
            user = User.query.filter_by(phone=phone).first()
            if not user:
                user = User(phone=phone)
                db.session.add(user)
                db.session.commit()
            session['user_id'] = user.id
            session.pop('login_otp', None)
            session.pop('login_phone', None)
            return redirect(url_for('home'))
        else:
            return render_template('verify_otp.html', error="Wrong OTP")
    return render_template('verify_otp.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# ==================== ROUTES: PAGES (Customer) ====================
@app.route('/')
def home():
    restaurants = Restaurant.query.filter_by(is_active=True).all()
    user = None
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
    return render_template('home.html', restaurants=restaurants, user=user)

@app.route('/restaurant/<int:restaurant_id>')
def restaurant_menu(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    menu_items = MenuItem.query.filter_by(restaurant_id=restaurant_id).all()
    return render_template('menu.html', restaurant=restaurant, items=menu_items)

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login'))
    orders = Order.query.filter_by(user_id=user.id).order_by(Order.created_at.desc()).all()
    co2_saved = calculate_co2_saved(orders)
    return render_template('profile.html', user=user, orders=orders, co2_saved=co2_saved)

@app.route('/checkout')
def checkout():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('checkout.html')

@app.route('/track/<int:order_id>')
def track_order(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    order = Order.query.get_or_404(order_id)
    if order.user_id != session['user_id']:
        return "Unauthorized", 403
    return render_template('track.html', order=order)

@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('cart.html')

# ==================== RIDER AUTH & DASHBOARD ====================
@app.route('/rider/login', methods=['GET', 'POST'])
def rider_login():
    if request.method == 'POST':
        phone = request.form.get('phone')
        if not phone or len(phone) != 10:
            return render_template('rider/login.html', error="Invalid phone number")
        session['rider_login_phone'] = phone
        session['rider_login_otp'] = "123456"
        print(f"[DEMO] Rider OTP for {phone}: 123456")
        return redirect(url_for('rider_verify_otp'))
    return render_template('rider/login.html')

@app.route('/rider/verify-otp', methods=['GET', 'POST'])
def rider_verify_otp():
    if request.method == 'POST':
        entered_otp = request.form.get('otp')
        expected_otp = session.get('rider_login_otp')
        phone = session.get('rider_login_phone')
        if not phone:
            return render_template('rider/verify_otp.html', error="Session expired")
        if str(entered_otp) == str(expected_otp) or str(entered_otp) == "123456":
            rider = Rider.query.filter_by(phone=phone).first()
            if not rider:
                rider = Rider(phone=phone)
                db.session.add(rider)
                db.session.commit()
            session['rider_id'] = rider.id
            session.pop('rider_login_otp', None)
            session.pop('rider_login_phone', None)
            return redirect(url_for('rider_dashboard'))
        else:
            return render_template('rider/verify_otp.html', error="Wrong OTP")
    return render_template('rider/verify_otp.html')

@app.route('/rider/dashboard')
def rider_dashboard():
    if 'rider_id' not in session:
        return redirect(url_for('rider_login'))
    return render_template('rider/dashboard.html')

@app.route('/rider/logout')
def rider_logout():
    session.pop('rider_id', None)
    return redirect(url_for('rider_login'))

# ==================== RIDER API ====================
@app.route('/api/rider/me')
def rider_me():
    if 'rider_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    rider = Rider.query.get(session['rider_id'])
    return jsonify({'id': rider.id, 'name': rider.name, 'is_active': rider.is_active})

@app.route('/api/rider/toggle', methods=['POST'])
def rider_toggle():
    if 'rider_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    rider = Rider.query.get(session['rider_id'])
    rider.is_active = not rider.is_active
    db.session.commit()
    return jsonify({'is_active': rider.is_active})

@app.route('/api/rider/location', methods=['POST'])
def update_rider_location():
    if 'rider_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    rider = Rider.query.get(session['rider_id'])
    rider.current_lat = data['lat']
    rider.current_lng = data['lng']
    rider.last_seen = datetime.utcnow()
    db.session.commit()
    return jsonify({'status': 'ok'})

@app.route('/api/rider/current-order')
def rider_current_order():
    if 'rider_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    rider_id = session['rider_id']
    order = Order.query.filter_by(rider_id=rider_id).filter(Order.status.in_(['rider_to_pad', 'rider_to_customer'])).first()
    if not order:
        return jsonify({})
    if order.status == 'rider_to_pad':
        pickup = "Restaurant address"
        dropoff = "Drone Launch Pad"
    else:
        pickup = "Drone Landing Pad"
        dropoff = order.delivery_address
    return jsonify({
        'id': order.id,
        'pickup_address': pickup,
        'dropoff_address': dropoff,
        'status': order.status
    })

@app.route('/api/rider/complete-stage', methods=['POST'])
def rider_complete_stage():
    if 'rider_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    order_id = data['order_id']
    qr_code = data.get('qr_code')
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    if order.rider_id != session['rider_id']:
        return jsonify({'error': 'Not your order'}), 403
    if order.status == 'rider_to_pad':
        order.status = 'drone_in_air'
        db.session.commit()
        request_drone(order.id)
    elif order.status == 'rider_to_customer':
        order.status = 'delivered'
        order.delivered_at = datetime.utcnow()
        db.session.commit()
    else:
        return jsonify({'error': 'Invalid stage'}), 400
    return jsonify({'success': True})

@app.route('/api/rider/create-ticket', methods=['POST'])
def rider_create_ticket():
    if 'rider_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    order_id = data.get('order_id')
    issue_type = data.get('issue_type')
    message = data.get('message')
    rider_id = session['rider_id']
    rider = Rider.query.get(rider_id)
    manager_id = rider.manager_id if rider else None
    ticket = SupportTicket(
        order_id=order_id,
        rider_id=rider_id,
        manager_id=manager_id,
        issue_type=issue_type,
        message=message,
        priority='medium',
        status='open'
    )
    db.session.add(ticket)
    db.session.commit()
    return jsonify({'success': True, 'ticket_id': ticket.id})

# ==================== DRONE INTEGRATION (SIMULATED) ====================
def request_drone(order_id):
    print(f"[DRONE] Requesting drone for order {order_id}")
    threading.Timer(2.0, simulate_drone_webhook, args=[order_id]).start()

def simulate_drone_webhook(order_id):
    send_drone_webhook(order_id, 'takeoff')
    time.sleep(2)
    for i in range(5):
        lat = 17.4300 + (i * 0.002)
        lng = 78.3450 + (i * 0.003)
        send_drone_webhook(order_id, 'position', lat=lat, lng=lng, alt=50 + i*10, speed=60 - i*5, battery=100 - i*5)
        time.sleep(1)
    send_drone_webhook(order_id, 'landed')

def send_drone_webhook(order_id, event, lat=None, lng=None, alt=None, speed=None, battery=None):
    payload = {'order_id': order_id, 'event': event}
    if lat is not None:
        payload.update({'lat': lat, 'lng': lng, 'alt': alt, 'speed': speed, 'battery': battery})
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request('http://localhost:5000/api/drone/webhook', data=data, method='POST', headers={'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(req, timeout=2)
    except Exception as e:
        print(f"Webhook error: {e}")

@app.route('/api/drone/webhook', methods=['POST'])
def drone_webhook():
    data = request.get_json()
    order_id = data['order_id']
    event = data['event']
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    if event == 'takeoff':
        order.status = 'drone_in_air'
        db.session.commit()
        print(f"[DRONE] Order {order_id} takeoff")
    elif event == 'position':
        tracking = DroneTracking(
            order_id=order_id,
            latitude=data['lat'],
            longitude=data['lng'],
            altitude=data['alt'],
            speed=data['speed'],
            battery=data['battery']
        )
        db.session.add(tracking)
        db.session.commit()
    elif event == 'landed':
        order.status = 'rider_to_customer'
        db.session.commit()
        print(f"[DRONE] Order {order_id} landed, awaiting final rider")
    return jsonify({'status': 'ok'})

# ==================== API: ORDERS, RESTAURANT STATS, PENDING ORDERS ====================
@app.route('/api/place-order', methods=['POST'])
def place_order():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    data = request.get_json()
    required = ['restaurant_id', 'items', 'total', 'delivery_address', 'latitude', 'longitude', 'unlock_code']
    for field in required:
        if field not in data:
            return jsonify({'error': f'Missing {field}'}), 400
    order = Order(
        user_id=session['user_id'],
        restaurant_id=data['restaurant_id'],
        items=json.dumps(data['items']),
        total_amount=data['total'],
        unlock_code=data['unlock_code'],
        status='pending',
        delivery_lat=data['latitude'],
        delivery_lng=data['longitude'],
        delivery_address=data['delivery_address'],
        zone='Gachibowli'  # default zone, you can derive from address
    )
    db.session.add(order)
    db.session.commit()
    tracking = DroneTracking(
        order_id=order.id,
        latitude=data['latitude'],
        longitude=data['longitude'],
        altitude=0,
        speed=0,
        battery=100
    )
    db.session.add(tracking)
    db.session.commit()
    return jsonify({
        'order_id': order.id,
        'unlock_code': order.unlock_code,
        'status': 'success'
    })

@app.route('/api/order/<int:order_id>')
def get_order(order_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    order = Order.query.get_or_404(order_id)
    if order.user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    return jsonify({
        'id': order.id,
        'status': order.status,
        'unlock_code': order.unlock_code,
        'total': order.total_amount,
        'created_at': order.created_at.isoformat(),
        'delivery_address': order.delivery_address,
        'drone_id': order.drone_id,
        'delivery_lat': order.delivery_lat,
        'delivery_lng': order.delivery_lng
    })

@app.route('/api/tracking/<int:order_id>')
def get_tracking(order_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    order = Order.query.get_or_404(order_id)
    if order.user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    tracking = DroneTracking.query.filter_by(order_id=order_id).order_by(DroneTracking.timestamp.desc()).first()
    if not tracking:
        return jsonify({
            'latitude': order.delivery_lat,
            'longitude': order.delivery_lng,
            'altitude': 0,
            'speed': 0,
            'battery': 100,
            'status': order.status,
            'unlock_code': order.unlock_code
        })
    return jsonify({
        'latitude': tracking.latitude,
        'longitude': tracking.longitude,
        'altitude': tracking.altitude,
        'speed': tracking.speed,
        'battery': tracking.battery,
        'status': order.status,
        'unlock_code': order.unlock_code
    })

@app.route('/api/order/update-status/<int:order_id>', methods=['POST'])
def update_order_status(order_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    new_status = data.get('status')
    if new_status not in ['delivered', 'cancelled']:
        return jsonify({'error': 'Invalid status'}), 400
    order = Order.query.get_or_404(order_id)
    if order.user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    order.status = new_status
    if new_status == 'delivered':
        order.delivered_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True, 'status': new_status})

@app.route('/admin/manager/<int:manager_id>')
def admin_manager_detail(manager_id):
    manager = Manager.query.get_or_404(manager_id)
    riders = Rider.query.filter_by(manager_id=manager_id).all()
    orders = Order.query.filter_by(manager_id=manager_id).all()
    return render_template('admin/manager_detail.html', manager=manager, riders=riders, orders=orders)

@app.route('/api/orders')
def list_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    result = []
    for o in orders:
        result.append({
            'id': o.id,
            'customer_name': o.user.name if o.user else 'Guest',
            'customer_phone': o.user.phone if o.user else 'N/A',
            'restaurant_id': o.restaurant_id,
            'items': o.items,
            'total_amount': o.total_amount,
            'status': o.status,
            'unlock_code': o.unlock_code,
            'created_at': o.created_at.isoformat()
        })
    return jsonify(result)

@app.route('/api/restaurant/stats')
def restaurant_stats():
    if 'restaurant_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    rid = session['restaurant_id']
    restaurant = Restaurant.query.filter_by(name=rid.capitalize()).first()
    if not restaurant:
        return jsonify({'today_orders': 0, 'today_revenue': 0, 'active_orders': 0, 'drone_status': 'Ready', 'completed_orders': 0, 'rating': 4.5})
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    orders_today = Order.query.filter(
        Order.restaurant_id == restaurant.id,
        Order.created_at >= today_start
    ).all()
    today_orders = len(orders_today)
    today_revenue = sum(o.total_amount for o in orders_today if o.status == 'delivered')
    active_orders = Order.query.filter(
        Order.restaurant_id == restaurant.id,
        Order.status.in_(['pending', 'accepted', 'preparing', 'out_for_delivery'])
    ).count()
    completed_orders = Order.query.filter_by(restaurant_id=restaurant.id, status='delivered').count()
    return jsonify({
        'today_orders': today_orders,
        'today_revenue': float(today_revenue),
        'active_orders': active_orders,
        'drone_status': 'Ready',
        'completed_orders': completed_orders,
        'rating': 4.5
    })

@app.route('/api/orders/pending')
def pending_orders():
    if 'restaurant_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    rid = session['restaurant_id']
    restaurant = Restaurant.query.filter_by(name=rid.capitalize()).first()
    if not restaurant:
        return jsonify([])
    orders = Order.query.filter(
        Order.restaurant_id == restaurant.id,
        Order.status.in_(['pending', 'accepted', 'preparing', 'out_for_delivery'])
    ).order_by(Order.created_at.desc()).all()
    result = []
    for o in orders:
        result.append({
            'id': o.id,
            'customer_name': o.user.name if o.user else 'Guest',
            'customer_phone': o.user.phone if o.user else 'N/A',
            'items': o.items,
            'total_amount': o.total_amount,
            'status': o.status,
            'delivery_address': o.delivery_address,
            'password': o.unlock_code
        })
    return jsonify(result)

# ==================== ROUTES: RESTAURANT DASHBOARD ====================
RESTAURANT_PINS = {
    'bawarchi': '1111',
    'paradise': '2222',
    'chutneys': '3333'
}

@app.route('/restaurant/login', methods=['GET', 'POST'])
def restaurant_login_page():
    if request.method == 'POST':
        rid = request.form.get('restaurant_id')
        pin = request.form.get('pin')
        if rid in RESTAURANT_PINS and RESTAURANT_PINS[rid] == pin:
            session['restaurant_id'] = rid
            session['restaurant_name'] = rid.capitalize()
            return redirect(url_for('restaurant_dashboard'))
        else:
            return render_template('restaurant/login.html', error="Invalid credentials")
    return render_template('restaurant/login.html')

@app.route('/restaurant/dashboard')
def restaurant_dashboard():
    if 'restaurant_id' not in session:
        return redirect(url_for('restaurant_login_page'))
    rid = session['restaurant_id']
    restaurant = Restaurant.query.filter_by(name=rid.capitalize()).first()
    if not restaurant:
        restaurant = Restaurant(name=rid.capitalize(), cuisine='Indian', rating=4.5, is_active=True)
        db.session.add(restaurant)
        db.session.commit()
    orders = Order.query.filter_by(restaurant_id=restaurant.id).order_by(Order.created_at.desc()).all()
    return render_template('restaurant/dashboard.html', restaurant=restaurant, orders=orders)

@app.route('/api/restaurant/update-order/<int:order_id>', methods=['POST'])
def restaurant_update_order(order_id):
    if 'restaurant_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    action = data.get('action')
    order = Order.query.get_or_404(order_id)
    restaurant = Restaurant.query.filter_by(name=session['restaurant_id'].capitalize()).first()
    if not restaurant or order.restaurant_id != restaurant.id:
        return jsonify({'error': 'Unauthorized'}), 403
    status_map = {
        'accept': 'accepted',
        'prepare': 'preparing',
        'dispatch': 'out_for_delivery',
        'deliver': 'delivered'
    }
    if action in status_map:
        order.status = status_map[action]
        if action == 'deliver':
            order.delivered_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True, 'status': order.status})
    return jsonify({'error': 'Invalid action'}), 400

# ==================== ROUTES: MANAGER DASHBOARD ====================
MANAGER_PINS = {
    'arjun': '1111',
    'priya': '2222',
    'sameer': '3333'
}

@app.route('/manager/login', methods=['GET', 'POST'])
def manager_login():
    if request.method == 'POST':
        username = request.form.get('username')
        pin = request.form.get('pin')
        if username in MANAGER_PINS and MANAGER_PINS[username] == pin:
            manager = Manager.query.filter_by(name=username.capitalize()).first()
            if manager:
                session['manager_id'] = manager.id
                session['manager_name'] = manager.name
                session['manager_zone'] = manager.zone
                return redirect(url_for('manager_dashboard'))
        return render_template('manager/login.html', error="Invalid credentials")
    return render_template('manager/login.html')

@app.route('/manager/dashboard')
def manager_dashboard():
    if 'manager_id' not in session:
        return redirect(url_for('manager_login'))
    return render_template('manager/dashboard.html')

@app.route('/manager/logout')
def manager_logout():
    session.pop('manager_id', None)
    session.pop('manager_name', None)
    session.pop('manager_zone', None)
    return redirect(url_for('manager_login'))

# ==================== MANAGER API ENDPOINTS ====================
@app.route('/api/manager/stats')
def manager_stats():
    if 'manager_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    zone = session.get('manager_zone')
    active_riders = Rider.query.filter_by(zone=zone, is_active=True).count()
    active_orders = Order.query.filter_by(zone=zone, status='out_for_delivery').count()
    open_tickets = SupportTicket.query.join(Rider).filter(Rider.zone==zone, SupportTicket.status=='open').count()
    return jsonify({
        'active_riders': active_riders,
        'active_orders': active_orders,
        'open_tickets': open_tickets
    })

@app.route('/api/manager/riders')
def manager_riders():
    if 'manager_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    zone = session.get('manager_zone')
    riders = Rider.query.filter_by(zone=zone).all()
    return jsonify([{
        'id': r.id,
        'name': r.name,
        'phone': r.phone,
        'is_active': r.is_active,
        'current_order_id': r.current_order_id,
        'last_seen': r.last_seen.isoformat() if r.last_seen else None
    } for r in riders])

@app.route('/api/manager/orders')
def manager_orders():
    if 'manager_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    zone = session.get('manager_zone')
    orders = Order.query.filter_by(zone=zone).filter(Order.status.in_(['pending','accepted','preparing','out_for_delivery'])).all()
    result = []
    for o in orders:
        rider = Rider.query.get(o.rider_id)
        result.append({
            'id': o.id,
            'customer_name': o.user.name if o.user else 'Guest',
            'restaurant_name': Restaurant.query.get(o.restaurant_id).name,
            'total': o.total_amount,
            'status': o.status,
            'rider_name': rider.name if rider else 'Unassigned',
            'created_at': o.created_at.isoformat()
        })
    return jsonify(result)

@app.route('/api/manager/tickets')
def manager_tickets():
    if 'manager_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    zone = session.get('manager_zone')
    tickets = SupportTicket.query.join(Rider).filter(Rider.zone==zone, SupportTicket.status.in_(['open','escalated'])).all()
    result = []
    for t in tickets:
        rider = Rider.query.get(t.rider_id)
        order = Order.query.get(t.order_id)
        result.append({
            'id': t.id,
            'order_id': t.order_id,
            'rider_name': rider.name if rider else 'N/A',
            'issue_type': t.issue_type,
            'message': t.message,
            'priority': t.priority,
            'status': t.status,
            'created_at': t.created_at.isoformat()
        })
    return jsonify(result)

@app.route('/api/manager/ticket/<int:ticket_id>/resolve', methods=['POST'])
def manager_resolve_ticket(ticket_id):
    if 'manager_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    ticket = SupportTicket.query.get(ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404
    ticket.status = 'resolved'
    ticket.resolved_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/manager/ticket/<int:ticket_id>/escalate', methods=['POST'])
def manager_escalate_ticket(ticket_id):
    if 'manager_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    ticket = SupportTicket.query.get(ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404
    ticket.priority = 'high'
    ticket.status = 'escalated'
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/manager/assign-rider', methods=['POST'])
def manager_assign_rider():
    if 'manager_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    order_id = data.get('order_id')
    rider_id = data.get('rider_id')
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    if order.zone != session.get('manager_zone'):
        return jsonify({'error': 'Not your zone'}), 403
    order.rider_id = rider_id
    order.status = 'rider_to_pad'
    db.session.commit()
    rider = Rider.query.get(rider_id)
    if rider:
        rider.current_order_id = order_id
        db.session.commit()
    return jsonify({'success': True})

# ==================== ROUTES: ADMIN DASHBOARD ====================
@app.route('/admin/dashboard')
def admin_dashboard():
    return render_template('admin/dashboard.html')

# ==================== ADMIN API ENDPOINTS ====================
@app.route('/api/admin/stats')
def admin_stats():
    total_orders = Order.query.count()
    total_revenue = db.session.query(db.func.sum(Order.total_amount)).filter_by(status='delivered').scalar() or 0
    active_riders = Rider.query.filter_by(is_active=True).count()
    active_drones = Drone.query.filter(Drone.status.in_(['idle','flying'])).count()
    open_tickets = SupportTicket.query.filter_by(status='open').count()
    return jsonify({
        'total_orders': total_orders,
        'total_revenue': float(total_revenue),
        'active_riders': active_riders,
        'active_drones': active_drones,
        'open_tickets': open_tickets
    })

@app.route('/api/admin/managers')
def admin_managers():
    managers = Manager.query.all()
    result = []
    for m in managers:
        riders_count = Rider.query.filter_by(manager_id=m.id).count()
        active_orders = Order.query.filter_by(manager_id=m.id, status='out_for_delivery').count()
        issues_count = SupportTicket.query.filter_by(manager_id=m.id, status='open').count()
        result.append({
            'id': m.id,
            'name': m.name,
            'zone': m.zone,
            'riders_count': riders_count,
            'active_orders': active_orders,
            'issues_count': issues_count,
            'status': m.status
        })
    return jsonify(result)

@app.route('/api/admin/drones')
def admin_drones():
    drones = Drone.query.all()
    return jsonify([{
        'id': d.id,
        'drone_id': d.drone_id,
        'battery': d.battery,
        'status': d.status,
        'zone': d.zone,
        'current_order_id': d.current_order_id
    } for d in drones])

@app.route('/api/admin/tickets')
def admin_tickets():
    tickets = SupportTicket.query.filter_by(status='open').all()
    result = []
    for t in tickets:
        rider = Rider.query.get(t.rider_id)
        result.append({
            'id': t.id,
            'order_id': t.order_id,
            'rider_name': rider.name if rider else 'N/A',
            'issue_type': t.issue_type,
            'priority': t.priority,
            'status': t.status
        })
    return jsonify(result)

@app.route('/api/admin/drone/<int:drone_id>/<action>', methods=['POST'])
def admin_drone_action(drone_id, action):
    drone = Drone.query.get(drone_id)
    if not drone:
        return jsonify({'error': 'Drone not found'}), 404
    if action == 'return':
        drone.status = 'returning'
    elif action == 'emergency':
        drone.status = 'emergency_stop'
    db.session.commit()
    return jsonify({'status': 'ok'})

@app.route('/api/admin/ticket/<int:ticket_id>/resolve', methods=['POST'])
def resolve_ticket(ticket_id):
    ticket = SupportTicket.query.get(ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404
    ticket.status = 'resolved'
    ticket.resolved_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'status': 'ok'})

# ==================== INITIAL DATA SEED ====================
def init_db():
    db.create_all()
    if Restaurant.query.count() == 0:
        sample_restaurants = [
            Restaurant(name='Bawarchi', cuisine='Biryani, Kebabs', rating=4.5, delivery_time=15, is_active=True),
            Restaurant(name='Paradise', cuisine='Biryani, Kebab', rating=4.7, delivery_time=20, is_active=True),
            Restaurant(name='Chutneys', cuisine='South Indian', rating=4.3, delivery_time=12, is_active=True)
        ]
        db.session.add_all(sample_restaurants)
        db.session.commit()
        menu_items = [
            MenuItem(restaurant_id=1, name='Chicken Biryani (Full)', price=280, description='Hyderabadi special', category='Biryani', is_veg=False),
            MenuItem(restaurant_id=1, name='Mutton Biryani (Full)', price=350, description='Tender mutton', category='Biryani', is_veg=False),
            MenuItem(restaurant_id=1, name='Haleem', price=180, description='Ramadan special', category='Starters', is_veg=False),
            MenuItem(restaurant_id=2, name='Paradise Special Biryani', price=320, description='Signature dish', category='Biryani', is_veg=False),
            MenuItem(restaurant_id=2, name='Keema Samosa', price=90, description='Crispy snack', category='Starters', is_veg=False),
            MenuItem(restaurant_id=3, name='Masala Dosa', price=120, description='Crispy dosa', category='Main Course', is_veg=True),
            MenuItem(restaurant_id=3, name='Idli Sambar', price=80, description='Soft idlis', category='Main Course', is_veg=True),
        ]
        db.session.add_all(menu_items)
        db.session.commit()

    # Seed managers
    if Manager.query.count() == 0:
        managers = [
            Manager(name='Arjun', email='arjun@dronedine.com', phone='9999999991', zone='Madhapur', status='online'),
            Manager(name='Priya', email='priya@dronedine.com', phone='9999999992', zone='Banjara Hills', status='online'),
            Manager(name='Sameer', email='sameer@dronedine.com', phone='9999999993', zone='Gachibowli', status='busy'),
        ]
        db.session.add_all(managers)
        db.session.commit()

    # Seed drones
    if Drone.query.count() == 0:
        drones = [
            Drone(drone_id='DR-001', battery=87, status='idle', zone='Gachibowli'),
            Drone(drone_id='DR-002', battery=94, status='flying', zone='Madhapur'),
            Drone(drone_id='DR-003', battery=32, status='charging', zone='HITEC City'),
        ]
        db.session.add_all(drones)
        db.session.commit()

    # Seed riders
    if Rider.query.count() == 0:
        riders = [
            Rider(phone='9999999911', name='Rahul', zone='Madhapur', manager_id=1, is_active=True),
            Rider(phone='9999999912', name='Neha', zone='Madhapur', manager_id=1, is_active=True),
            Rider(phone='9999999913', name='Vikram', zone='Gachibowli', manager_id=3, is_active=True),
        ]
        db.session.add_all(riders)
        db.session.commit()

    # Sample orders
    if Order.query.count() == 0:
        orders = [
            Order(user_id=1, restaurant_id=1, items='[{"name":"Chicken Biryani","quantity":2,"price":280}]', total_amount=560, unlock_code='1234', status='pending', delivery_address='HITEC City, Hyderabad', zone='HITEC City'),
            Order(user_id=1, restaurant_id=2, items='[{"name":"Paradise Special Biryani","quantity":1,"price":320}]', total_amount=320, unlock_code='5678', status='out_for_delivery', delivery_address='Madhapur, Hyderabad', zone='Madhapur'),
        ]
        db.session.add_all(orders)
        db.session.commit()

    # Sample support tickets
    if SupportTicket.query.count() == 0:
        tickets = [
            SupportTicket(order_id=1, rider_id=1, issue_type='restaurant_delay', priority='medium', status='open'),
            SupportTicket(order_id=2, rider_id=2, issue_type='customer_not_reachable', priority='high', status='escalated'),
        ]
        db.session.add_all(tickets)
        db.session.commit()

with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
