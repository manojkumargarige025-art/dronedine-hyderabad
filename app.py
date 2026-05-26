"""
DroneDine - Complete Backend with User Auth, Orders, Drone Tracking,
Admin/Restaurant Dashboards, Profile Updates, and Saved Addresses
"""
import os
if os.path.exists('dronedine.db'):
    os.remove('dronedine.db')

import json
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
from flask_sqlalchemy import SQLAlchemy

# ==================== CONFIGURATION ====================
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dronedine-super-secret-key-change-me")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dronedine.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
CORS(app, supports_credentials=True)
db = SQLAlchemy(app)

# Mapbox token (your existing one)
MAPBOX_TOKEN = "pk.eyJ1IjoibWFub2oyNTgwOCIsImEiOiJjbXBsZ3B3NmoxYzJmMnFzbHV6Zmt1NnNwIn0.hzkSfnkPO_KRL3urJbFtxA"


# ==================== MODELS ====================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    addresses = db.Column(db.Text, default='[]')  # JSON array of address objects
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    orders = db.relationship('Order', backref='user', lazy=True)

class Restaurant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    cuisine = db.Column(db.String(50))
    rating = db.Column(db.Float, default=4.0)
    delivery_time = db.Column(db.Integer, default=20)  # minutes
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
    description = db.Column(db.String(200))
    category = db.Column(db.String(50))
    image_url = db.Column(db.String(200))
    is_veg = db.Column(db.Boolean, default=True)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    items = db.Column(db.Text, nullable=False)  # JSON string
    total_amount = db.Column(db.Float, nullable=False)
    unlock_code = db.Column(db.String(4), nullable=False)
    status = db.Column(db.String(50), default='placed')  # placed, accepted, preparing, out_for_delivery, delivered, cancelled
    delivery_lat = db.Column(db.Float)
    delivery_lng = db.Column(db.Float)
    delivery_address = db.Column(db.String(200))
    drone_id = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    delivered_at = db.Column(db.DateTime)

class DroneTracking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    altitude = db.Column(db.Float, default=0)
    speed = db.Column(db.Float, default=0)
    battery = db.Column(db.Integer, default=100)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


# ==================== HELPER FUNCTIONS ====================
def generate_unlock_code():
    return str(random.randint(1000, 9999))

def calculate_co2_saved(orders):
    delivered = [o for o in orders if o.status == 'delivered']
    return len(delivered) * 0.065


# ==================== ROUTES: AUTH ====================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form.get('phone')
        if not phone or len(phone) != 10:
            return render_template('login.html', error="Invalid phone number")
        otp = "123456"  # always 123456 for demo
        session['login_otp'] = otp
        session['login_phone'] = phone
        print(f"[DEMO] OTP for {phone}: {otp}")
        return redirect(url_for('verify_otp'))
    return render_template('login.html')

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        entered_otp = request.form.get('otp')
        if str(entered_otp) == str(session.get('login_otp')) or str(entered_otp) == "123456":
            phone = session.get('login_phone')
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


# ==================== ROUTES: PAGES ====================
@app.route('/')
def home():
    restaurants = Restaurant.query.filter_by(is_active=True).all()
    return render_template('home.html', restaurants=restaurants)

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
    orders = Order.query.filter_by(user_id=user.id).order_by(Order.created_at.desc()).all()
    co2_saved = calculate_co2_saved(orders)
    return render_template('profile.html', user=user, orders=orders, co2_saved=co2_saved)

@app.route('/track-order/<int:order_id>')
def track_order(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    order = Order.query.get_or_404(order_id)
    if order.user_id != session['user_id']:
        return "Unauthorized", 403
    return render_template('track.html', order=order)


# ==================== ROUTES: PROFILE API ====================
@app.route('/api/user/update', methods=['POST'])
def update_user_profile():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    data = request.get_json()
    user = User.query.get(session['user_id'])
    if 'name' in data:
        user.name = data['name']
    if 'email' in data:
        user.email = data['email']
    db.session.commit()
    return jsonify({'success': True, 'name': user.name, 'email': user.email})

@app.route('/api/user/addresses', methods=['GET', 'POST', 'DELETE'])
def user_addresses():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    user = User.query.get(session['user_id'])
    if request.method == 'GET':
        addresses = json.loads(user.addresses) if user.addresses else []
        return jsonify(addresses)
    elif request.method == 'POST':
        data = request.get_json()
        addresses = json.loads(user.addresses) if user.addresses else []
        addresses.append(data)
        user.addresses = json.dumps(addresses)
        db.session.commit()
        return jsonify({'success': True, 'addresses': addresses})
    elif request.method == 'DELETE':
        index = request.args.get('index', type=int)
        addresses = json.loads(user.addresses) if user.addresses else []
        if 0 <= index < len(addresses):
            addresses.pop(index)
            user.addresses = json.dumps(addresses)
            db.session.commit()
        return jsonify({'success': True, 'addresses': addresses})


# ==================== ROUTES: ORDER API ====================
@app.route('/api/place-order', methods=['POST'])
def place_order():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    data = request.get_json()
    required = ['restaurant_id', 'items', 'total', 'delivery_address', 'latitude', 'longitude']
    for field in required:
        if field not in data:
            return jsonify({'error': f'Missing {field}'}), 400
    unlock_code = generate_unlock_code()
    order = Order(
        user_id=session['user_id'],
        restaurant_id=data['restaurant_id'],
        items=json.dumps(data['items']),
        total_amount=data['total'],
        unlock_code=unlock_code,
        status='placed',
        delivery_lat=data['latitude'],
        delivery_lng=data['longitude'],
        delivery_address=data['delivery_address']
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
        'unlock_code': unlock_code,
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
        'drone_id': order.drone_id
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
            return render_template('restaurant_login.html', error="Invalid credentials")
    return render_template('restaurant_login.html')

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


# ==================== ROUTES: ADMIN DASHBOARD ====================
@app.route('/admin/dashboard')
def admin_dashboard():
    total_orders = Order.query.count()
    active_orders = Order.query.filter(Order.status.in_(['accepted', 'preparing', 'out_for_delivery'])).count()
    delivered_orders = Order.query.filter_by(status='delivered').count()
    total_revenue = db.session.query(db.func.sum(Order.total_amount)).filter_by(status='delivered').scalar() or 0
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/dashboard.html', 
                         total_orders=total_orders,
                         active_orders=active_orders,
                         delivered_orders=delivered_orders,
                         total_revenue=total_revenue,
                         orders=orders)


# ==================== INITIAL DATA SEED (run at startup) ====================
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


# ==================== RUN (tables created on app load) ====================
with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
