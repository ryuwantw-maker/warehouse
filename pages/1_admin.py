import streamlit as st
import sys
import os
from datetime import datetime

# --- 1. MEMASTIKAN PATH DIKENAL OLEH PYTHON ---
# Mengambil folder induk (parent directory) agar file models.py terdeteksi
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import app, db, Customer, Vehicle, Warehouse, Order, SalesReturn

# --- 2. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="WMS - Modul Admin", layout="wide")

# --- 3. PROTEKSI USER MANAGEMENT (HAK AKSES) ---
if not st.session_state.get('logged_in') or st.session_state.get('user_role') != 'Admin':
    st.error("⛔ Akses Ditolak: Halaman ini hanya diperuntukkan bagi akun berkepentingan Admin.")
    st.stop()

st.title("🧑‍💼 Pusat Kerja Admin (Sales & Data Management)")
st.markdown("---")

# Seleksi Sub-Peran Admin di Sidebar sesuai Spesifikasi Dokumen
sub_role = st.sidebar.selectbox("Pilih Sub-Peran Admin Anda:", ["Admin (Marketing)", "Admin (Delivery)"])
st.sidebar.markdown("---")

# Navigasi Menu Utama di Sidebar
menu_pilihan = st.sidebar.radio(
    "Pilih Menu Transaksi/Master:", 
    ["Sales Order", "TLSO Penjadwalan", "Delivery Order (SJ)", "Sales Return", "Data Management"]
)

# --- 4. LOGIKA MODUL KERJA ---
with app.app_context():
    
    # ==========================================
    # MENU 1: SALES ORDER (Wewenang: Admin Marketing)
    # ==========================================
    if menu_pilihan == "Sales Order":
        st.subheader("✍️ Pembuatan Dokumen Sales Order (SO)")
        if sub_role != "Admin (Marketing)":
            st.warning("⚠️ Menu ini hanya dapat diisi oleh Admin (Marketing) sesuai spesifikasi.")
        else:
            customers = Customer.query.all()
            if not customers:
                st.info("ℹ️ Belum ada data customer terdaftar. Silakan lengkapi Data Management terlebih dahulu.")
            else:
                cust_options = {c.name: c.id for c in customers}
                with st.form("form_so", clear_on_submit=True):
                    po_num = st.text_input("Nomor PO Customer")
                    selected_cust = st.selectbox("Pilih Customer:", list(cust_options.keys()))
                    prod_name = st.text_input("Nama Produk / Item")
                    qty = st.number_input("Jumlah Pesanan (Qty)", min_value=1, value=1)
                    
                    if st.form_submit_button("Simpan Data Sales Order"):
                        if po_num and prod_name:
                            new_order = Order(
                                po_number=po_num, 
                                customer_id=cust_options[selected_cust], 
                                product_name=prod_name, 
                                quantity=qty, 
                                status='Sales Order Created'
                            )
                            db.session.add(new_order)
                            db.session.commit()
                            st.success(f"✅ Dokumen SO untuk PO #{po_num} berhasil disimpan ke sistem.")
                            st.rerun()
                        else:
                            st.error("❌ Nomor PO dan Nama Produk wajib diisi.")

    # ==========================================
    # MENU 2: TLSO PENJADWALAN (Wewenang: Admin Delivery)
    # ==========================================
    elif menu_pilihan == "TLSO Penjadwalan":
        st.subheader(" Jatahtime Kirim (TLSO)")
        if sub_role != "Admin (Delivery)":
            st.warning("⚠️ Penjadwalan jadwal kirim (TLSO) hanya wewenang Admin (Delivery).")
        else:
            so_list = Order.query.filter_by(status='Sales Order Created').all()
            if so_list:
                for o in so_list:
                    cust = Customer.query.get(o.customer_id)
                    with st.expander(f"📋 PO: {o.po_number} | Pelanggan: {cust.name if cust else '-'} - Item: {o.product_name}"):
                        req_date = st.date_input("Tentukan Tanggal Permintaan Pengiriman:", min_value=datetime.today().date(), key=f"d_{o.id}")
                        if st.button("Set Jadwal & Teruskan Informasi ke Warehouse", key=f"btn_{o.id}"):
                            o.request_date = req_date
                            o.status = "TLSO Scheduled"
                            db.session.commit()
                            st.success("✔️ Informasi Delivery Order dijadwalkan. Antrean dikirim ke Warehouse FG untuk pengisian Lot.")
                            st.rerun()
            else:
                st.info("ℹ️ Tidak ada antrean dokumen Sales Order baru untuk dijadwalkan.")

    # ==========================================
    # MENU 3: DELIVERY ORDER / SURAT JALAN (Wewenang: Admin Delivery)
    # ==========================================
    elif menu_pilihan == "Delivery Order (SJ)":
        st.subheader("📜 Penerbitan berkas Surat Jalan (Delivery Order)")
        if sub_role != "Admin (Delivery)":
            st.warning("⚠️ Pencetakan dokumen Surat Jalan (SJ) hanya wewenang Admin (Delivery).")
        else:
            ready_do = Order.query.filter_by(status='TLSO Ready').all()
            vehicles = Vehicle.query.all()
            
            if ready_do:
                if not vehicles:
                    st.error("⚠️ Data armada kendaraan kosong. Harap isi data kendaraan terlebih dahulu di menu Data Management.")
                else:
                    for o in ready_do:
                        cust = Customer.query.get(o.customer_id)
                        with st.expander(f"📄 Penerbitan SJ PO: {o.po_number} ({cust.name if cust else '-'})"):
                            st.write(f"**Item:** {o.product_name} | **Jumlah:** {o.quantity} Pcs | **No Lot:** {o.lot_number}")
                            st.write(f"🧪 **Hasil Uji Viskositas QC:** {o.visco_result} ({o.qc_approved})")
                            
                            veh_opts = {f"🚚 {v.plate_number} - Supir: {v.driver_name} ({v.vehicle_type})": v.id for v in vehicles}
                            selected_v = st.selectbox("Pilih Armada untuk SJ:", list(veh_opts.keys()), key=f"v_{o.id}")
                            
                            if st.button("Cetak Dokumen Surat Jalan", key=f"pr_{o.id}"):
                                o.vehicle_id = veh_opts[selected_v]
                                o.status = "DO Issued"
                                db.session.commit()
                                st.success(f"🖨️ Surat Jalan (SJ) Berhasil Dicetak! Armada {selected_v} ditugaskan.")
                                st.rerun()
            else:
                st.info("ℹ️ Belum ada data barang hasil validasi Lot & QC yang siap diterbitkan Surat Jalannya.")

    # ==========================================
    # MENU 4: SALES RETURN (Wewenang: Admin Delivery)
    # ==========================================
    elif menu_pilihan == "Sales Return":
        st.subheader("↩️ Pencatatan Returan Customer")
        if sub_role != "Admin (Delivery)":
            st.warning("⚠️ Pencatatan returan pelanggan dilakukan oleh Admin (Delivery).")
        else:
            shipped = Order.query.filter_by(status='DO Issued').all()
            if shipped:
                order_opts = {f"PO: {o.po_number} ({o.product_name})": o.id for o in shipped}
                with st.form("form_ret", clear_on_submit=True):
                    sel_ret = st.selectbox("Pilih Dokumen Order Terkirim:", list(order_opts.keys()))
                    r_qty = st.number_input("Jumlah Barang Diretur (Qty)", min_value=1, value=1)
                    reason = st.text_area("Alasan Retur / Kerusakan Barang")
                    
                    if st.form_submit_button("Proses Dokumen Retur"):
                        new_return = SalesReturn(order_id=order_opts[sel_ret], return_qty=r_qty, reason=reason)
                        db.session.add(new_return)
                        db.session.commit()
                        st.success("✅ Dokumen returan berhasil dicatat. Sampel dikirim ke lab QC Outgoing untuk cek viskositas.")
                        st.rerun()
            else:
                st.info("ℹ️ Belum ada riwayat pengiriman selesai (DO Issued) yang dapat diretur.")
            
            # Menampilkan Riwayat Retur Aktual
            st.markdown("---")
            st.markdown("#### Riwayat Status Retur Produk")
            returns = SalesReturn.query.all()
            if returns:
                st.dataframe([{
                    "ID Retur": r.id, "ID Order": r.order_id, "Jumlah": r.return_qty,
                    "Alasan": r.reason, "Uji Lab QC (Visco)": r.return_visco if r.return_visco else "-", "Status": r.qc_status
                } for r in returns], use_container_width=True)

    # ==========================================
    # MENU 5: DATA MANAGEMENT MASTER
    # ==========================================
    elif menu_pilihan == "Data Management":
        st.subheader("🗂️ Pengelolaan Modul Data Management Master")
        
        m_type = st.radio("Pilih Data Master yang Akan Dikelola:", ["👥 Customer", "🚛 Vehicles", "🏢 Warehouse"], horizontal=True)
        st.markdown("---")
        
        # --- KONDISI A: MASTER CUSTOMER (Admin Marketing) ---
        if m_type == "👥 Customer":
            if sub_role != "Admin (Marketing)":
                st.error("⛔ Akses Ditolak: Data Master Customer hanya boleh diisi oleh Admin (Marketing).")
            else:
                with st.form("form_cust", clear_on_submit=True):
                    n = st.text_input("Nama Lengkap Customer / Perusahaan")
                    p = st.text_input("Nomor Telepon")
                    a = st.text_area("Alamat Lengkap")
                    if st.form_submit_button("Simpan Data Master"):
                        if n and p and a:
                            db.session.add(Customer(name=n, phone=p, address=a))
                            db.session.commit()
                            st.success(f"✅ Data Customer '{n}' sukses disimpan.")
                        st.rerun()
                    else:
                        st.error("❌ Semua kolom form customer wajib diisi.")
            
            # Tampilkan tabel data customer di bawah form
            cust_list = Customer.query.all()
            if cust_list:
                st.write("##### Tabel Database Master Customer aktual:")
                st.dataframe([{"ID": c.id, "Nama": c.name, "No Telp": c.phone, "Alamat": c.address} for c in cust_list], use_container_width=True)

        # --- KONDISI B: MASTER VEHICLES (Admin Marketing & Delivery) ---
        elif m_type == "🚛 Vehicles":
            with st.form("form_veh", clear_on_submit=True):
                v_plate = st.text_input("Nomor Plat Kendaraan (Dipakai pada SJ)")
                v_driver = st.text_input("Nama Pengemudi / Supir")
                v_type = st.selectbox("Jenis Kendaraan", ["Mobil Box", "Truk Engkel", "Container"])
                
                if st.form_submit_button("Simpan Data Armada"):
                    if v_plate and v_driver:
                        if Vehicle.query.filter_by(plate_number=v_plate).first():
                            st.error("❌ Nomor plat kendaraan tersebut sudah terdaftar.")
                        else:
                            new_vehicle = Vehicle(plate_number=v_plate, driver_name=v_driver, vehicle_type=v_type)
                            db.session.add(new_vehicle)
                            db.session.commit()
                            st.success(f"✅ Armada [{v_plate}] berhasil didaftarkan.")
                            st.rerun()
                    else:
                        st.error("⚠️ Kolom Plat Nomor dan Nama Pengemudi tidak boleh kosong.")
            
            # Tampilkan tabel data kendaraan di bawah form
            veh_list = Vehicle.query.all()
            if veh_list:
                st.write("##### Tabel Database Kendaraan Perusahaan aktual:")
                st.dataframe([{"ID": v.id, "No Plat": v.plate_number, "Nama Supir": v.driver_name, "Tipe": v.vehicle_type} for v in veh_list], use_container_width=True)

        # --- KONDISI C: MASTER WAREHOUSE (Admin Marketing) ---
        elif m_type == "🏢 Warehouse":
            if sub_role != "Admin (Marketing)":
                st.error("⛔ Akses Ditolak: Data Master Gudang hanya boleh diisi oleh Admin (Marketing).")
            else:
                with st.form("form_wh", clear_on_submit=True):
                    w_name = st.text_input("Nama Gudang")
                    w_loc = st.text_input("Lokasi / Area")
                    
                    if st.form_submit_button("Simpan Informasi Gudang"):
                        if w_name:
                            new_warehouse = Warehouse(warehouse_name=w_name, location=w_loc)
                            db.session.add(new_warehouse)
                            db.session.commit()
                            st.success(f"✅ Gudang '{w_name}' berhasil didaftarkan.")
                            st.rerun()
                        else:
                            st.error("⚠️ Nama Gudang tidak boleh kosong.")
                
                # Tampilkan tabel data gudang di bawah form
                wh_list = Warehouse.query.all()
                if wh_list:
                    st.write("##### Tabel Database Lokasi Gudang aktual:")
                    st.dataframe([{"ID": w.id, "Nama Gudang": w.warehouse_name, "Lokasi": w.location} for w in wh_list], use_container_width=True)