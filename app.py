import streamlit as st
import easyocr
import numpy as np
from PIL import Image
import re

# --- CACHING MODEL AI EASYOCR ---
@st.cache_resource(show_spinner="Memuat model AI ke memori server...")
def get_ocr_reader():
    return easyocr.Reader(['en'], gpu=False)

def process_single_image(image, target_accounts, reader):
    """Memproses 1 gambar dan mengembalikan nomor rekening yang ditemukan."""
    image_np = np.array(image)
    
    # AI membaca teks dari gambar
    results = reader.readtext(image_np, detail=0)
    extracted_text = " ".join(results)
    cleaned_digits_only = re.sub(r'\D', '', extracted_text)
    
    found_accounts = []
    for account in target_accounts:
        clean_target = re.sub(r'\D', '', str(account))
        if clean_target and clean_target in cleaned_digits_only:
            found_accounts.append(account)
            
    return found_accounts, extracted_text

# --- CONFIG TAMPILAN ---
st.set_page_config(page_title="AI Batch Scanner", page_icon="📦", layout="centered")
st.title("📦 AI Batch Scanner")
st.caption("Foto tumpukan kertas terlebih dahulu di HP, lalu upload semua foto sekaligus di sini.")
st.warning("🔒 Aman: Data tidak disimpan di server dan akan hilang otomatis begitu web ditutup.")

# Inisialisasi memori simpan sementara
if "target_accounts" not in st.session_state:
    st.session_state.target_accounts = []

# --- 1. FORM INPUT REKENING ---
st.subheader("1. Masukkan Data Rekening Target")

with st.form("form_rekening"):
    data_input = st.text_area(
        "Paste/Tempel daftar nomor rekening target di sini (pisahkan dengan Enter):", 
        height=120,
        placeholder="Contoh:\n1234567890\n0987654321"
    )
    submit_button = st.form_submit_button("💾 Simpan Data Rekening", type="primary", use_container_width=True)

if submit_button:
    accounts = [re.sub(r'\D', '', line.strip()) for line in data_input.split('\n') if line.strip()]
    st.session_state.target_accounts = accounts
    if accounts:
        st.toast(f"Berhasil menyimpan {len(accounts)} nomor rekening!", icon="✅")

# Status ketersediaan data
if not st.session_state.target_accounts:
    st.info("📌 Silakan paste nomor rekening di atas, lalu pencet tombol **'Simpan Data Rekening'**.")
else:
    st.success(f"✅ Data Aktif: **{len(st.session_state.target_accounts)}** nomor rekening dicari.")
    
    st.divider()
    
    # --- 2. BATCH UPLOAD DOKUMEN ---
    st.subheader("2. Upload Foto Massal dari Galeri HP")
    
    # Permatukan accept_multiple_files=True untuk upload banyak foto sekaligus
    uploaded_files = st.file_uploader(
        "Pilih/Tandai semua foto kertas dari galeri HP Anda:", 
        type=["jpg", "png", "jpeg"], 
        accept_multiple_files=True
    )

    if uploaded_files:
        st.info(f"📂 Total **{len(uploaded_files)} foto** dipilih dan siap diperiksa AI.")
        
        if st.button("🚀 Pindai Semua Foto Sekarang", type="primary", use_container_width=True):
            reader = get_ocr_reader()
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            results_list = []
            matched_count = 0
            
            # Loop memproses setiap foto satu per satu
            for index, file in enumerate(uploaded_files):
                status_text.text(f"AI sedang memeriksa Foto ke-{index+1} dari {len(uploaded_files)}...")
                
                image = Image.open(file)
                found, raw_text = process_single_image(image, st.session_state.target_accounts, reader)
                
                if found:
                    matched_count += 1
                
                results_list.append({
                    "index": index + 1,
                    "filename": file.name,
                    "found": found,
                    "raw_text": raw_text,
                    "image": image
                })
                
                # Update progress bar
                progress_bar.progress((index + 1) / len(uploaded_files))
                
            status_text.text("✅ Pemindaian selesai!")
            
            st.divider()
            st.subheader("📊 Hasil Pemindaian Massal")
            
            if matched_count > 0:
                st.success(f"🎉 Ditemukan **{matched_count} foto** yang COCOK dari total {len(uploaded_files)} foto!")
            else:
                st.error("❌ Tidak ada nomor rekening yang cocok dari seluruh foto yang diupload.")
                
            # Menampilkan Ringkasan Hasil
            for item in results_list:
                with st.expander(
                    f"{'✅ COCOK' if item['found'] else '❌ Tidak Cocok'} - Foto Ke-{item['index']} ({item['filename']})"
                ):
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.image(item['image'], use_container_width=True)
                    with col2:
                        if item['found']:
                            st.success("**Nomor Rekening Ditemukan:**")
                            for acc in item['found']:
                                st.write(f"- **{acc}**")
                        else:
                            st.write("Tidak ada nomor rekening target pada foto ini.")
                        
                        st.caption("Teks terbaca:")
                        st.text(item['raw_text'] if item['raw_text'] else "Tidak ada teks/angka terdeteksi.")
