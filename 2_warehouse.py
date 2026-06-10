import streamlit as st
import sys
import os

# Karena file ini berada di dalam folder 'pages', kita ambil folder induknya (parent)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Sekarang impor models akan berjalan lancar dari halaman manapun
from models import app, db, Customer, Vehicle, Warehouse, Order, SalesReturn
from datetime import datetime

# ... sisa kode 1_Admin.py Anda ke bawah tetap sama

st.set_page_config(page_title="Modul Warehouse", layout="wide")

# Proteksi Halaman
if not st.session_state.get('logged_in') or st.session_state.get('user_role') != 'Warehouse FG':
    st.error("⛔ Akses Ditolak: Halaman ini khusus untuk Akun Tim Warehouse FG.")
    st.stop()

st.title("🏢 Area Kerja Operasional Warehouse FG")

with app.app_context():
    st.subheader("📥 Alokasi Nomor Lot Berdasarkan Stok Fisik")
    wh_queue = Order.query.filter_by(status='TLSO Scheduled').all()
    if wh_queue:
        for o in wh_queue:
            cust = Customer.query.get(o.customer_id)
            with st.expander(f"📦 Siapkan Stok PO: {o.po_number} | Customer: {cust.name if cust else '-'} - {o.product_name}"):
                lot_in = st.text_input("Masukkan Nomor Lot Produksi Gudang:", key=f"lot_{o.id}")
                if st.button("Kunci Nomor Lot & Kirim ke QC", key=f"btn_lot_{o.id}"):
                    if lot_in:
                        o.lot_number = lot_in
                        o.status = "QC Testing"
                        db.session.commit()
                        st.success(f"Nomor Lot {lot_in} dikunci. Menunggu hasil uji lab.")
                        st.rerun()
                    else:
                        st.error("Nomor Lot wajib diisi.")
    else:
        st.info("Tidak ada instruksi penyiapan nomor lot barang saat ini.")

    # ========================================================
    # ALUR AKTIVITAS BARU: CEK PRODUK SALES RETURN
    # ========================================================
    st.markdown("---")
    st.subheader("↩️ Antrean Pemeriksaan Fisik Barang Retur (Cek Produk)")
    
    # Menampilkan returan yang baru diinput oleh Admin dan belum dicek fisik oleh gudang
    ret_warehouse_queue = SalesReturn.query.filter_by(qc_status='Pending Check').all()
    
    if ret_warehouse_queue:
        for r in ret_warehouse_queue:
            o = Order.query.get(r.order_id)
            cust = Customer.query.get(o.customer_id) if o else None
            
            with st.expander(f"📦 Pemeriksaan Fisik Retur ID #{r.id} - PO Customer: {o.po_number if o else '-'}"):
                st.write(f"**Nama Pelanggan:** {cust.name if cust else '-'}")
                st.write(f"**Produk Rusak/Klaim:** {o.product_name if o else '-'} | **Volume:** {r.return_qty} Pcs")
                st.write(f"**Alasan Keluhan:** *\"{r.reason}\"*")
                
                if st.button("Selesai Cek Fisik & Teruskan ke Laboratorium QC", key=f"wh_ret_{r.id}"):
                    r.qc_status = "Checked by Warehouse" # Mengalirkan status ke kolom QC (Outgoing Visco)
                    db.session.commit()
                    st.success("✔️ Produk selesai dicek fisik. Sampel cairan diteruskan ke meja uji laboratorium QC.")
                    st.rerun()
    else:
        st.info("ℹ️ Tidak ada paket barang returan baru yang perlu diperiksa fisiknya di gudang.")