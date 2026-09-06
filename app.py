import streamlit as st
import easyocr
import numpy as np
from PIL import Image
import re

# --- CACHING MODEL AI EASYOCR ---
# Model di-load 1x saja ke memori server agar proses baca cepat
@st.cache_resource(show_spinner="Memuat model AI ke memori server...")
def get_ocr_reader():
    return easyocr.Reader(['en'], gpu=False)

def process_image_for_accounts(image, target_accounts):
    reader = get_ocr_reader()
    
    # Konversi gambar dari PIL ke Numpy Array
    image_np = np.array(image)
    
    # Membaca teks/angka dari seluruh area foto
    results = reader.readtext(image_np, detail=0)
    
    # Gabungkan seluruh hasil bacaan menjadi satu string
    extracted_text = " ".join(results)
    
    # Hapus semua karakter selain angka (0-9)
    cleaned_digits_only = re.sub(r'\D', '', extracted_text)
    
    found_accounts = []
    for account in target_accounts:
        # Bersihkan nomor rekening target agar hanya berupa angka murni
        clean_target = re.sub(r'\D', '', str(account))
        
        # Cek apakah angka target ada di dalam deretan angka yang dibaca AI
        if clean_target and clean_target in cleaned_digits_only:
            found_accounts.append(account)
            
    return found_accounts, extracted_text

# --- TAMPILAN APLIKASI STREAMLIT ---
st.set_page_config(page_title="AI Scanner Rekening", page_icon="📱", layout="centered")
st.title("📱 AI Mobile Scanner")
st.caption("Mendukung angka cetakan mesin & tulisan tangan.")
st.warning("🔒 Aman: Data Anda tidak disimpan di server dan akan hilang otomatis begitu web ditutup.")

# Inisialisasi memori simpan sementara
if "target_accounts" not in st.session_state:
    st.session_state.target_accounts = []

# --- 1. FORM INPUT DENGAN TOMBOL SUBMIT ---
st.subheader("1. Masukkan Data Rekening Target")

with st.form("form_rekening"):
    data_input = st.text_area(
        "Paste/Tempel daftar nomor rekening di sini (pisahkan dengan Enter):", 
        height=120,
        placeholder="Contoh:\n1234567890\n0987654321"
    )
    submit_button = st.form_submit_button("💾 Simpan Data Rekening", type="primary", use_container_width=True)

if submit_button:
    accounts = [line.strip() for line in data_input.split('\n') if line.strip()]
    st.session_state.target_accounts = accounts
    if accounts:
        st.toast(f"Berhasil menyimpan {len(accounts)} nomor rekening!", icon="✅")

# Status ketersediaan data
if not st.session_state.target_accounts:
    st.info("📌 Silakan paste nomor rekening di atas, lalu pencet tombol **'Simpan Data Rekening'**.")
else:
    st.success(f"✅ Data Aktif: **{len(st.session_state.target_accounts)}** nomor rekening tersimpan.")
    
    st.divider()
    
    # --- 2. BAGIAN PINDAI DOKUMEN ---
    st.subheader("2. Pindai Kertas Dokumen")
    
    tab1, tab2 = st.tabs(["📸 Ambil Foto", "📂 Pilih dari Galeri"])
    image_to_process = None

    with tab1:
        camera_photo = st.camera_input("Ambil foto dokumen/bagian pojok kanan atas")
        if camera_photo is not None:
            image_to_process = Image.open(camera_photo)

    with tab2:
        uploaded_file = st.file_uploader("Pilih gambar dari galeri", type=["jpg", "png", "jpeg"])
        if uploaded_file is not None:
            image_to_process = Image.open(uploaded_file)
            st.image(image_to_process, caption="Preview Dokumen", use_container_width=True)

    # Tombol untuk memproses foto
    if image_to_process is not None:
        if st.button("🔍 Pindai Sekarang", type="primary", use_container_width=True):
            with st.spinner("AI sedang membaca angka pada kertas..."):
                found, raw_text = process_image_for_accounts(image_to_process, st.session_state.target_accounts)
                
            st.divider()
            if found:
                st.success("✅ **DOKUMEN DITEMUKAN! SIMPAN KERTAS INI.**")
                st.write("Nomor rekening yang cocok:")
                for acc in found:
                    st.write(f"- **{acc}**")
            else:
                st.error("❌ **TIDAK COCOK. KERTAS BISA DISINGKIRKAN.**")
                
            with st.expander("Lihat teks/angka yang terbaca oleh AI"):
                st.text(raw_text if raw_text else "Tidak ada teks/angka terdeteksi.")
