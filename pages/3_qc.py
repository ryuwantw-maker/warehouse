import streamlit as st
import sys
import os

# Karena file ini berada di dalam folder 'pages', kita ambil folder induknya (parent)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Sekarang impor models akan berjalan lancar dari halaman manapun
from models import app, db, Customer, Vehicle, Warehouse, Order, SalesReturn
from models import app, db, Order, SalesReturn, Product
from datetime import datetime

# ... sisa kode 1_Admin.py Anda ke bawah tetap sama

st.set_page_config(page_title="Modul QC", layout="wide")

# Proteksi Halaman
if not st.session_state.get('logged_in') or st.session_state.get('user_role') != 'QC':
    st.error("⛔ Akses Ditolak: Halaman ini khusus untuk Akun Laboratorium QC.")
    st.stop()

st.title("🧪 Laboratorium Pengujian Mutu (QC Outgoing)")

with app.app_context():
    st.subheader("🔬 1. Uji Viskositas Barang Siap Kirim (Outgoing Visco)")
    qc_queue = Order.query.filter_by(status='QC Testing').all()
    if qc_queue:
        for o in qc_queue:
            with st.expander(f"Uji Sampel PO: {o.po_number} - Nomor Lot Gudang: {o.lot_number}"):
                visco = st.number_input("Nilai Viskositas Cairan:", min_value=0.0, step=0.1, key=f"vis_{o.id}")
                if st.button("Verifikasi Kualitas OK", key=f"btn_qc_{o.id}"):
                    o.visco_result = visco
                    o.qc_approved = "Passed"
                    o.status = "TLSO Ready"
                    db.session.commit()
                    st.success("Kualitas diverifikasi OK. Data dialirkan ke Admin untuk cetak Surat Jalan.")
                    st.rerun()
    else:
        st.info("Tidak ada sampel produk baru untuk diuji.")

    st.markdown("---")
    st.subheader("🔬 Validasi Laboratorium Produk Sales Return (Outgoing Visco)")
    
    # Hanya menarik data returan yang sudah lolos tahap 'Cek Produk' oleh Warehouse FG
    qc_return_queue = SalesReturn.query.filter_by(qc_status='Checked by Warehouse').all()
    
    if qc_return_queue:
        for r in qc_queue: # Menggunakan loop antrean objek retur aktual
            o = Order.query.get(r.order_id)
            
            with st.expander(f"🧪 Uji Spesifikasi Sampel Retur ID #{r.id} (Produk: {o.product_name if o else '-'})", expanded=True):
                st.warning(f"📋 Keluhan Lapangan: {r.reason}")
                
                # Tahap 1: Jalankan Aktivitas 'Outgoing Visco'
                v_test = st.number_input("Input Hasil Uji Viskositas Cairan Retur:", min_value=0.0, step=0.1, key=f"v_ret_{r.id}")
                
                # Tahap 2: Gerbang Keputusan Kontrol Kualitas (Decision Box: Yakin?)
                st.markdown("**Konfirmasi Kelayakan Hasil Uji Standar Mutu:**")
                is_yakin = st.checkbox("Saya yakin hasil uji lab sudah sesuai dengan prosedur pengujian", key=f"yak_{r.id}")
                
                if is_yakin:
                    # Tahap 3: Aktivitas 'Mengambil Keputusan' (Apakah Masuk Kategori Stok OK atau HOLD)
                    keputusan_stok = st.radio(
                        "Ambil Keputusan Alokasi Item Adjustment:",
                        ["Masuk ke Status 'OK' (Stok Baik/Bisa Dijual Lagi)", "Masuk ke Data 'HOLD' (Karantina/Barang Reject)"],
                        key=f"kep_{r.id}"
                    )
                    
                    if st.button("Simpan & Eksekusi Penyesuaian Item Adjustment", key=f"btn_save_ret_{r.id}"):
                        r.return_visco = v_test
                        
                        # Hubungkan keputusan QC untuk otomatis memperbarui saldo di tabel Product (Item Adjustment)
                        # Cari produk berdasarkan kecocokan nama produk transaksi asal
                        prod_target = Product.query.filter_by(name=o.product_name).first()
                        
                        if "Status 'OK'" in keputusan_stok:
                            r.qc_status = "OK"
                            if prod_target:
                                prod_target.stock_ok += r.return_qty # Otomatis menambah saldo Stok OK
                            st.success(f"✔️ Sukses! {r.return_qty} unit berhasil di-adjust masuk ke saldo STOK OK.")
                        else:
                            r.qc_status = "HOLD"
                            if prod_target:
                                prod_target.stock_hold += r.return_qty # Otomatis menambah saldo Stok HOLD
                            st.error(f"⚠️ Karantina! {r.return_qty} unit dialokasikan masuk ke dalam laporan DATA HOLD.")
                            
                        db.session.commit()
                        st.rerun()
                else:
                    st.info("💡 Berikan tanda centang pada kotak konfirmasi 'Yakin?' di atas untuk membuka opsi pengambilan keputusan.")
    else:
        st.info("ℹ️ Tidak ada sampel cairan dari barang retur yang menunggu antrean uji laboratorium Outgoing Visco.")