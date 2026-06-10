from flask_sqlalchemy import SQLAlchemy
from flask import Flask

# --- 1. KONFIGURASI DATABASE PUSAT ---
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///warehouse_sales_v3.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- 2. MODUL USER MANAGEMENT ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False)

# --- 3. MODUL DATA MANAGEMENT MASTER ---
class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, nullable=False)

class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plate_number = db.Column(db.String(20), unique=True, nullable=False)
    driver_name = db.Column(db.String(100), nullable=False)
    vehicle_type = db.Column(db.String(50), nullable=False)

class Warehouse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    warehouse_name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(255), nullable=True)

# --- 4. MODUL SALES TRANSAKSI ---
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    po_number = db.Column(db.String(50), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    request_date = db.Column(db.Date, nullable=True)
    lot_number = db.Column(db.String(50), nullable=True)
    visco_result = db.Column(db.Float, nullable=True)
    qc_approved = db.Column(db.String(10), default='Pending')
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=True)
    status = db.Column(db.String(50), default='Sales Order Created')

class SalesReturn(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    return_qty = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    return_visco = db.Column(db.Float, nullable=True)
    qc_status = db.Column(db.String(20), default='Pending Check')

# --- 5. MODUL INVENTARIS ITEM (PENYELAMAT ERROR IMPORT) ---
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    stock_ok = db.Column(db.Integer, default=0)
    stock_hold = db.Column(db.Integer, default=0)
    color_process_result = db.Column(db.String(100), nullable=True)

class ItemTransfer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    qty = db.Column(db.Integer, nullable=False)
    from_warehouse = db.Column(db.String(100), nullable=False)
    to_warehouse = db.Column(db.String(100), nullable=False)
    transfer_date = db.Column(db.Date, nullable=False)
    sj_number = db.Column(db.String(50), unique=True, nullable=False)
