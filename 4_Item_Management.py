import streamlit as st
import sys
import os
from datetime import datetime

# --- 1. MEMASTIKAN PATH DIKENAL OLEH PYTHON ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import app, db, Category, Product, ItemTransfer, Warehouse

st.set_page_config(page_title="WMS - Modul Item", layout="wide")

# Proteksi Hak Akses Utama (Hanya Admin)
if not st.session_state.get('logged_in') or st.session_state.get('user_role') != 'Admin':
    st.error("⛔ Akses Ditolak: Halaman ini hanya untuk Akun dengan wewenang Admin.")
    st.stop()

st.title("📦 Pusat Manajemen Kontrol Stok & Item Inventory")
st.markdown("---")

# Seleksi Sub-Peran Admin di Sidebar sesuai Spesifikasi Dokumen Baru
sub_role_item = st.sidebar.selectbox("Pilih Departemen Admin Anda:", ["Admin (PPIC)", "Admin (QC)", "Admin (Delivery)"])
st.sidebar.markdown("---")

menu_item = st.sidebar.radio(
    "Pilih Menu Item:",
    ["Item Detail", "Categories", "Item Adjustment", "Item Outgoing", "Item Transfer"]
)

with app.app_context():
    
    # ==========================================
    # MENU 1: ITEM DETAIL (Dapat Diakses Semua Admin)
    # ==========================================
    if menu_item == "Item Detail":
        st.subheader("🔍 Informasi Detil Spesifikasi & Stok Produk Aktual")
        products = Product.query.all()
        if products:
            data_p = []
            for p in products:
                cat = Category.query.get(p.category_id)
                data_p.append({
                    "ID Produk": p.id, "Kategori": cat.name if cat else "-", "SKU": p.sku,
                    "Nama Barang": p.name, "Stok OK (Siap Jalan)": p.stock_ok, 
                    "Stok HOLD (Karantina)": p.stock_hold, "Hasil Analisa Warna": p.color_process_result if p.color_process_result else "-"
                })
            st.dataframe(data_p, use_container_width=True)
        else:
            st.info("ℹ️ Belum ada produk terdaftar di database gudang.")

    # ==========================================
    # MENU 2: CATEGORIES (Wewenang: Admin PPIC)
    # ==========================================
    elif menu_item == "Categories":
        st.subheader("🗂️ Manajemen Kategori Produk")
        if sub_role_item != "Admin (PPIC)":
            st.warning("⚠️ Penambahan kategori produk baru adalah hak akses Admin (PPIC).")
        else:
            with st.form("form_cat", clear_on_submit=True):
                cat_name = st.text_input("Nama Kategori Baru")
                if st.form_submit_button("Simpan Kategori"):
                    if cat_name:
                        if Category.query.filter_by(name=cat_name).first():
                            st.error("❌ Kategori sudah ada di database.")
                        else:
                            db.session.add(Category(name=cat_name))
                            db.session.commit()
                            st.success(f"✅ Kategori '{cat_name}' berhasil ditambahkan.")
                            st.rerun()
                    else:
                        st.error("Nama kategori wajib diisi.")
        
        # Tampilkan daftar kategori
        categories = Category.query.all()
        if categories:
            st.write("##### Daftar Kategori Terdaftar:")
            st.dataframe([{"ID Kategori": c.id, "Nama Kategori": c.name} for c in categories], use_container_width=True)

    # ==========================================
    # MENU 3: ITEM ADJUSTMENT (Wewenang: Admin PPIC)
    # ==========================================
    elif menu_item == "Item Adjustment":
        st.subheader("⚖️ Koreksi & Adjustment Stok Fisik Gudang FG")
        if sub_role_item != "Admin (PPIC)":
            st.warning("⚠️ Laporan pemasukan/pengeluaran barang (Adjustment) hanya wewenang Admin (PPIC).")
        else:
            # Pilihan membuat produk baru atau update produk lama
            opsi_adjust = st.radio("Jenis Transaksi Adjustment:", ["Tambah Produk Baru", "Update/Koreksi Stok Produk Terdaftar"], horizontal=True)
            
            if opsi_adjust == "Tambah Produk Baru":
                cats = Category.query.all()
                if not cats:
                    st.error("Harap isi Kategori Produk terlebih dahulu.")
                else:
                    cat_opts = {c.name: c.id for c in cats}
                    with st.form("form_new_prod", clear_on_submit=True):
                        p_sku = st.text_input("Kode SKU")
                        p_name = st.text_input("Nama Barang")
                        p_cat = st.selectbox("Pilih Kategori", list(cat_opts.keys()))
                        st_ok = st.number_input("Stok Awal (Status OK)", min_value=0, value=0)
                        st_hold = st.number_input("Stok Awal (Status HOLD)", min_value=0, value=0)
                        
                        if st.form_submit_button("Daftarkan Barang Baru"):
                            if p_sku and p_name:
                                if Product.query.filter_by(sku=p_sku).first():
                                    st.error("❌ Kode SKU sudah terpakai.")
                                else:
                                    db.session.add(Product(sku=p_sku, name=p_name, category_id=cat_opts[p_cat], stock_ok=st_ok, stock_hold=st_hold))
                                    db.session.commit()
                                    st.success(f"✅ Produk {p_name} didaftarkan.")
                                    st.rerun()
            
            elif opsi_adjust == "Update/Koreksi Stok Produk Terdaftar":
                products = Product.query.all()
                if not products:
                    st.info("Belum ada produk terdaftar.")
                else:
                    p_opts = {f"{p.sku} - {p.name}": p.id for p in products}
                    selected_p = st.selectbox("Pilih Produk yang Di-adjust:", list(p_opts.keys()))
                    
                    with st.form("form_adj_update", clear_on_submit=True):
                        tipe_adj = st.selectbox("Aksi Laporan Laju Barang:", ["IN (Pemasukan Barang)", "OUT (Barang Keluar Produksi)", "RETUR OK (Masuk ke Stok OK)", "RETUR HOLD (Masuk ke Data HOLD)"])
                        qty_adj = st.number_input("Jumlah Volume Barang", min_value=1, value=1)
                        
                        if st.form_submit_button("Eksekusi Adjustment"):
                            p_target = Product.query.get(p_opts[selected_p])
                            
                            if tipe_adj == "IN (Pemasukan Barang)":
                                p_target.stock_ok += qty_adj
                                st.success(f"✅ Berhasil menambah {qty_adj} unit ke Stok OK.")
                            elif tipe_adj == "OUT (Barang Keluar Produksi)":
                                if p_target.stock_ok >= qty_adj:
                                    p_target.stock_ok -= qty_adj
                                    st.success(f"✅ Berhasil mengeluarkan {qty_adj} unit dari Stok OK.")
                                else:
                                    st.error("❌ Gagal! Stok OK tidak mencukupi untuk dipakai produksi.")
                            elif tipe_adj == "RETUR OK (Masuk ke Stok OK)":
                                p_target.stock_ok += qty_adj
                                st.success(f"✅ Barang retur kondisi baik masuk ke Stok OK sebanyak {qty_adj} unit.")
                            elif tipe_adj == "RETUR HOLD (Masuk ke Data HOLD)":
                                p_target.stock_hold += qty_adj
                                st.success(f"⚠️ Barang retur bermasalah dikarantina ke Stok HOLD sebanyak {qty_adj} unit.")
                                
                            db.session.commit()
                            st.rerun()

    # ==========================================
    # MENU 4: ITEM OUTGOING (Wewenang: Admin QC)
    # ==========================================
    elif menu_item == "Item Outgoing":
        st.subheader("🎨 Pencatatan Hasil Proses Warna Produk")
        if sub_role_item != "Admin (QC)":
            st.warning("⚠️ Menu pencatatan verifikasi warna produk merupakan wewenang Admin (QC).")
        else:
            products = Product.query.all()
            if not products:
                st.info("Belum ada item di gudang untuk diverifikasi warnanya.")
            else:
                p_opts = {f"{p.sku} - {p.name}": p.id for p in products}
                selected_p = st.selectbox("Pilih Produk Hasil Item Adjustment:", list(p_opts.keys()))
                
                with st.form("form_color_qc"):
                    color_result = st.text_input("Masukkan Hasil Spektrofotometri / Analisa Visual Warna (misal: Delta E < 0.5 - PASS)")
                    if st.form_submit_button("Simpan Hasil Warna"):
                        if color_result:
                            p_target = Product.query.get(p_opts[selected_p])
                            p_target.color_process_result = color_result
                            db.session.commit()
                            st.success(f"✅ Hasil analisa warna untuk produk {p_target.name} berhasil disimpan.")
                            st.rerun()
                        else:
                            st.error("Form isian analisa warna tidak boleh kosong.")

    # ==========================================
    # MENU 5: ITEM TRANSFER (Wewenang: Admin Delivery)
    # ==========================================
    elif menu_item == "Item Transfer":
        st.subheader("🚚 Transfer Mutasi Gudang Pusat ke Cabang")
        if sub_role_item != "Admin (Delivery)":
            st.warning("⚠️ Penerbitan Surat Jalan mutasi/pemindahan gudang pusat ke cabang adalah wewenang Admin (Delivery).")
        else:
            products = Product.query.all()
            warehouses = Warehouse.query.all()
            
            if not products or not warehouses:
                            st.error("⚠️ Pastikan Data Master Gudang dan Master Produk terisi terlebih dahulu.")
    else:
            # Ambil data dari database terlebih dahulu sebelum digunakan
            products = Product.query.all()
            warehouses = Warehouse.query.all()
            
            # Baru jalankan proses pemetaan variabel ke komponen dropdown
            p_opts = {f"{p.sku} - {p.name} (Stok OK: {p.stock_ok})": p.id for p in products}
            wh_list = [w.warehouse_name for w in warehouses]
            
            with st.form("form_transfer", clear_on_submit=True):
                sj_num = st.text_input("Nomor Surat Jalan Mutasi (SJ Transfer)")
                selected_p = st.selectbox("Pilih Item yang Dipindahkan:", list(p_opts.keys()))
                qty_tf = st.number_input("Jumlah Mutasi", min_value=1, value=1)
                from_wh = st.selectbox("Dari Gudang Asal (Pusat):", wh_list, key="from")
                to_wh = st.text_input("Ke Gudang Cabang Tujuan:")
                
                if st.form_submit_button("Terbitkan SJ Pemindahan Gudang"):
                    p_target = Product.query.get(p_opts[selected_p])
                    if sj_num and to_wh:
                        if ItemTransfer.query.filter_by(sj_number=sj_num).first():
                            st.error("❌ Nomor Surat Jalan Transfer tersebut sudah digunakan.")
                        elif p_target.stock_ok >= qty_tf:
                            # Kurangi Stok Gudang Pusat
                            p_target.stock_ok -= qty_tf
                            # Catat transaksi mutasi
                            db.session.add(ItemTransfer(
                                product_id=p_target.id, 
                                qty=qty_tf, 
                                from_warehouse=from_wh, 
                                to_warehouse=to_wh, 
                                transfer_date=datetime.today().date(), 
                                sj_number=sj_num
                            ))
                            db.session.commit()
                            st.success(f"📜 SJ Mutasi #{sj_num} Terbit! {qty_tf} unit '{p_target.name}' dikirim dari {from_wh} ke {to_wh}.")
                            st.rerun()
                        else:
                            st.error("❌ Gagal! Volume stok OK di gudang pusat tidak mencukupi untuk ditransfer.")
                    else:
                        st.error("Mohon lengkapi kolom Nomor SJ dan Gudang Tujuan.")
        
# Tampilkan riwayat surat jalan pemindahan di luar blok penanganan form
    transfers = ItemTransfer.query.all()
    if transfers:
            st.markdown("---")
            st.markdown("#### Rekapitulasi Dokumen Surat Jalan Pemindahan Gudang")
            st.dataframe([{
                "No Surat Jalan": t.sj_number, 
                "ID Produk": t.product_id, 
                "Volume Mutasi": t.qty,
                "Dari Gudang": t.from_warehouse, 
                "Gudang Cabang Tujuan": t.to_warehouse, 
                "Tanggal Mutasi": str(t.transfer_date)
            } for t in transfers], use_container_width=True)