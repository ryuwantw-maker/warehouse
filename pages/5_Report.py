import streamlit as st
import sys
import os
import pandas as pd

# --- 1. MEMASTIKAN PATH DIKENAL OLEH PYTHON ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import app, db, Order, SalesReturn, Customer, Vehicle, Product

# --- 2. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="WMS - Modul Report", layout="wide", page_icon="📊")

# --- 3. PROTEKSI HAK AKSES (USER MANAGEMENT) ---
# Memeriksa apakah pengguna sudah login
if not st.session_state.get('logged_in'):
    st.error("🔒 Akses Ditolak: Silakan login terlebih dahulu di halaman utama.")
    st.stop()

# Menerapkan aturan dokumen: Seluruh aktor BISA melihat, KECUALI Warehouse FG
if st.session_state.get('user_role') == 'Warehouse FG':
    st.error("⛔ Akses Ditolak: Sesuai spesifikasi sistem, Peran 'Warehouse FG' tidak diberikan izin untuk mengakses laporan manajemen.")
    st.stop()

st.title("📊 Pusat Laporan & Analisis Manajemen Gudang")
st.markdown(f"Status Sesi: Pengguna `{st.session_state['username']}` | Hak Akses: **{st.session_state['user_role']}**")
st.markdown("---")

# Pilihan Kategori Laporan Utama
jenis_laporan = st.radio(
    "Pilih Laporan yang Ingin Ditinjau:",
    ["🚚 Laporan Pengiriman (Delivery Order)", "↩️ Laporan Retur Barang (Sales Return)", "📦 Laporan Ringkasan Stok Produk"],
    horizontal=True
)

with app.app_context():
    
    # ==========================================
    # LAPORAN 1: DELIVERY ORDER (PENGIRIMAN)
    # ==========================================
    if "Delivery Order" in jenis_laporan:
        st.subheader("📋 Rekapitulasi Status Pengiriman Barang")
        
        # Ambil data pesanan yang sudah/sedang dalam proses kirim
        orders = Order.query.all()
        
        if orders:
            data_delivery = []
            for o in orders:
                cust = Customer.query.get(o.customer_id)
                veh = Vehicle.query.get(o.vehicle_id) if o.vehicle_id else None
                
                data_delivery.append({
                    "ID Order": o.id,
                    "No PO Customer": o.po_number,
                    "Nama Customer": cust.name if cust else "-",
                    "Nama Produk": o.product_name,
                    "Volume (Qty)": o.quantity,
                    "Tgl Minta Kirim": str(o.request_date) if o.request_date else "Belum Set",
                    "No Lot Gudang": o.lot_number if o.lot_number else "Belum Alokasi",
                    "Uji Visco QC": o.visco_result if o.visco_result else "-",
                    "No Plat Armada": veh.plate_number if veh else "Belum Ditugaskan",
                    "Supir Pengirim": veh.driver_name if veh else "-",
                    "Status Alur": o.status
                })
            
            df_delivery = pd.DataFrame(data_delivery)
            st.dataframe(df_delivery, use_container_width=True)
            
            # Fitur Unduh CSV untuk Manajemen
            csv_del = df_delivery.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Unduh Laporan Pengiriman (CSV)", csv_del, "Laporan_Delivery_Order.csv", "text/csv")
        else:
            st.info("ℹ️ Belum ada data transaksi pengiriman di dalam database.")

    # ==========================================
    # LAPORAN 2: SALES RETURN (RETUR BARANG)
    # ==========================================
    elif "Sales Return" in jenis_laporan:
        st.subheader("📋 Rekapitulasi Penanganan Kasus Retur Barang")
        
        returns = SalesReturn.query.all()
        
        if returns:
            data_returns = []
            for r in returns:
                o = Order.query.get(r.order_id)
                cust = Customer.query.get(o.customer_id) if o else None
                
                data_returns.append({
                    "ID Retur": r.id,
                    "ID Order Terkait": r.order_id,
                    "No PO Asal": o.po_number if o else "-",
                    "Nama Customer": cust.name if cust else "-",
                    "Nama Produk": o.product_name if o else "-",
                    "Jumlah Diretur": r.return_qty,
                    "Alasan Retur / Kerusakan": r.reason,
                    "Hasil Cek Viskositas QC": r.return_visco if r.return_visco else "Menunggu Uji Lab",
                    "Status Pemeriksaan QC": r.qc_status
                })
            
            df_returns = pd.DataFrame(data_returns)
            st.dataframe(df_returns, use_container_width=True)
            
            # Fitur Unduh CSV untuk Manajemen
            csv_ret = df_returns.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Unduh Laporan Retur Barang (CSV)", csv_ret, "Laporan_Sales_Return.csv", "text/csv")
        else:
            st.info("ℹ️ Bersih! Saat ini tidak ada catatan klaim retur barang dari customer.")

    # ==========================================
    # LAPORAN 3: RINGKASAN STOK PRODUK
    # ==========================================
    elif "Stok Produk" in jenis_laporan:
        st.subheader("📋 Status Inventaris Ketersediaan Barang Aktual")
        
        products = Product.query.all()
        
        if products:
            data_stock = [{
                "ID Produk": p.id,
                "Kode SKU": p.sku,
                "Nama Item / Produk": p.name,
                "Volume Siap Kirim (Stok OK)": p.stock_ok,
                "Volume Karantina (Stok HOLD)": p.stock_hold,
                "Total Saldo Stok Fisik": (p.stock_ok + p.stock_hold),
                "Verifikasi Warna Terakhir": p.color_process_result if p.color_process_result else "Belum Cek"
            } for p in products]
            
            df_stock = pd.DataFrame(data_stock)
            st.dataframe(df_stock, use_container_width=True)
            
            # Fitur Unduh CSV untuk Manajemen
            csv_stock = df_stock.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Unduh Laporan Stok (CSV)", csv_stock, "Laporan_Stok_Aktual.csv", "text/csv")
        else:
            st.info("ℹ️ Data master barang kosong. Tidak ada stok terhitung di dalam sistem.")