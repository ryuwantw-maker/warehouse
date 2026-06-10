import sys
import os
import streamlit as st
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# This forces the database file to be created inside your exact app directory
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'warehouse.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- 1. MEMASTIKAN PATH DIKENAL OLEH PYTHON ---
# Langkah wajib agar modul 'models' dapat diimpor tanpa masalah dari folder manapun
current_dir = os.path.abspath(os.path.dirname(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Impor library pihak ketiga dan modul database lokal
from werkzeug.security import generate_password_hash, check_password_hash
from models import app, db, User, Order, Customer, Vehicle

# --- 2. KONFIGURASI HALAMAN UTAMA STREAMLIT ---
st.set_page_config(
    page_title="WMS - Gerbang Utama", 
    page_icon="📦", 
    layout="wide"
)

# --- 3. INISIALISASI DATABASE & DATA AWAL (SEEDING) ---
with app.app_context():
    db.create_all()  # Membuat file database jika belum ada
    
    # Membuat Akun Dummy jika database masih kosong bersih
    if not User.query.filter_by(username='admin').first():
        db.session.add_all([
            User(username='admin', password=generate_password_hash('admin123'), role='Admin'),
            User(username='warehouse', password=generate_password_hash('wh123'), role='Warehouse FG'),
            User(username='qc_team', password=generate_password_hash('qc123'), role='QC')
        ])
        db.session.commit()

# --- 4. MANAJEMEN STATE PENGGUNA (SESSION STATE) ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_role' not in st.session_state:
    st.session_state['user_role'] = None
if 'username' not in st.session_state:
    st.session_state['username'] = None

# --- 5. TAMPILAN ANTARMUKA (INTERFACE) ---
st.title("📦 Sistem Informasi Manajemen Gudang (WMS)")
st.markdown("---")

# SKENARIO A: PENGGUNA BELUM LOGIN
if not st.session_state['logged_in']:
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.subheader("🔒 Silakan Masuk ke Sistem")
        with st.form("login_form", clear_on_submit=False):
            username_input = st.text_input("Username", placeholder="Masukkan username Anda")
            password_input = st.text_input("Password", type="password", placeholder="Masukkan password Anda")
            submit_button = st.form_submit_button("Masuk Sesi", use_container_width=True)
            
            if submit_button:
                if username_input and password_input:
                    with app.app_context():
                        user = User.query.filter_by(username=username_input).first()
                        
                        # Validasi kecocokan username dan enkripsi password
                        if user and check_password_hash(user.password, password_input):
                            st.session_state['logged_in'] = True
                            st.session_state['user_role'] = user.role
                            st.session_state['username'] = user.username
                            st.success(f"✔️ Login Berhasil! Anda masuk sebagai **{user.role}**.")
                            st.rerun()
                        else:
                            st.error("❌ Username atau password salah. Silakan coba lagi.")
                else:
                    st.warning("⚠️ Mohon isi seluruh kolom username dan password.")

# SKENARIO B: PENGGUNA SUDAH LOGIN (MENAMPILKAN DASHBOARD UTAMA)
else:
    # Konfigurasi Sidebar Informasi Akun Aktif
    st.sidebar.markdown("### 👤 Informasi Sesi")
    st.sidebar.info(f"**Pengguna:** {st.session_state['username']}\n\n**Hak Akses:** {st.session_state['user_role']}")
    st.sidebar.markdown("---")
    
    # Tombol Keluar Sistem yang Aman
    if st.sidebar.button("🚪 Log Out / Keluar", use_container_width=True):
        st.session_state.clear()  # Menghapus seluruh data sesi agar aman
        st.rerun()

    # Konten Halaman Dashboard Utama
    st.subheader("📊 Dasbor Pemantauan Transaksi Real-Time")
    st.write("Gunakan menu di bilah samping (*sidebar*) untuk mengakses modul kerja spesifik sesuai hak akses Anda.")
    
    with app.app_context():
        orders = Order.query.all()
        data_orders = []
        
        # Penggabungan data (JOIN) secara dinamis untuk laporan ringkas dashboard
        for o in orders:
            cust = Customer.query.get(o.customer_id)
            veh = Vehicle.query.get(o.vehicle_id) if o.vehicle_id else None
            
            data_orders.append({
                "ID Transaksi": o.id,
                "Nomor PO": o.po_number,
                "Nama Pelanggan": cust.name if cust else "Tidak Diketahui",
                "Nama Produk": o.product_name,
                "Jumlah (Qty)": o.quantity,
                "Tanggal Permintaan": str(o.request_date) if o.request_date else "-",
                "Nomor Lot Gudang": o.lot_number if o.lot_number else "-",
                "Nilai Viskositas": o.visco_result if o.visco_result else "-",
                "Status Mutu QC": o.qc_approved,
                "Armada Pengirim": veh.plate_number if veh else "-",
                "Status Alur Sistem": o.status
            })
            
        if data_orders:
            # Menampilkan data dalam bentuk tabel interaktif yang bisa difilter
            st.dataframe(data_orders, use_container_width=True)
        else:
            st.info("ℹ️ Saat ini belum ada data transaksi atau pesanan masuk di dalam sistem.")
