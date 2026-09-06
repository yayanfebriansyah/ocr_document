import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, WebRtcMode
import easyocr
import cv2
import numpy as np
import re
import time

# --- CACHING MODEL AI EASYOCR ---
@st.cache_resource(show_spinner="Memuat model AI ke memori server...")
def get_ocr_reader():
    return easyocr.Reader(['en'], gpu=False)

# Inisialisasi awal
reader = get_ocr_reader()

st.set_page_config(page_title="Scanner Real-Time", page_icon="⚡", layout="centered")
st.title("⚡ Real-Time Scanner (Beep & Getar)")
st.caption("Sorot kamera ke arah kertas. HP akan berbunyi BEEP otomatis saat menemukan nomor rekening.")

if "target_accounts" not in st.session_state:
    st.session_state.target_accounts = []

# --- 1. FORM INPUT REKENING ---
st.subheader("1. Masukkan Data Rekening Target")

with st.form("form_rekening"):
    data_input = st.text_area(
        "Paste/Tempel daftar nomor rekening di sini (pisahkan dengan Enter):", 
        height=100,
        placeholder="Contoh:\n1234567890\n0987654321"
    )
    submit_button = st.form_submit_button("💾 Simpan Data Rekening", type="primary", use_container_width=True)

if submit_button:
    accounts = [re.sub(r'\D', '', line.strip()) for line in data_input.split('\n') if line.strip()]
    st.session_state.target_accounts = accounts
    if accounts:
        st.toast(f"Berhasil menyimpan {len(accounts)} nomor rekening!", icon="✅")

if not st.session_state.target_accounts:
    st.info("📌 Silakan masukan nomor rekening di atas lalu klik **'Simpan Data Rekening'** sebelum memulai kamera.")
else:
    st.success(f"✅ Target Aktif: **{len(st.session_state.target_accounts)}** nomor rekening dicari.")
    
    st.divider()
    st.subheader("2. Kamera Real-Time")

    # --- EFEK AUDIO BEEP & GETAR (JAVASCRIPT) ---
    sound_html = """
    <audio id="beep-sound" src="https://actions.google.com/sounds/v1/beeps/short_high_tone.ogg" preload="auto"></audio>
    <script>
        function playBeep() {
            var audio = document.getElementById('beep-sound');
            if (audio) { audio.play(); }
            if (navigator.vibrate) { navigator.vibrate([200, 100, 200]); }
        }
    </script>
    """
    st.components.v1.html(sound_html, height=0)

    # --- VIDEO PROCESSING CLASS ---
    class AccountScanner(VideoTransformerBase):
        def __init__(self):
            self.last_scan_time = 0
            self.found_match = False
            self.detected_account = ""

        def transform(self, frame):
            img = frame.to_ndarray(format="bgr24")
            h, w, _ = img.shape

            # Pembacaan dilakukan di SELURUH area kamera (tanpa cropping otomatis)
            current_time = time.time()
            if current_time - self.last_scan_time > 0.8:
                self.last_scan_time = current_time
                
                # AI membaca seluruh area yang terlihat di layar
                results = reader.readtext(img, detail=0)
                extracted_text = " ".join(results)
                cleaned_digits = re.sub(r'\D', '', extracted_text)

                # Pencocokan data
                self.found_match = False
                for target in st.session_state.target_accounts:
                    if target and target in cleaned_digits:
                        self.found_match = True
                        self.detected_account = target
                        break

            # Jika nomor rekening cocok, beri bingkai HIJAU tebal pada layar video
            if self.found_match:
                cv2.rectangle(img, (0, 0), (w, h), (0, 255, 0), 12)
                cv2.putText(img, f"MATCH: {self.detected_account}", (20, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 3)

            return img

    # --- STREAMER KAMERA ---
    ctx = webrtc_streamer(
        key="account-scanner-full",
        mode=WebRtcMode.SENDRECV,
        video_transformer_factory=AccountScanner,
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        media_stream_constraints={"video": {"facingMode": "environment"}, "audio": False},
        async_processing=True,
    )

    if ctx.video_transformer:
        if ctx.video_transformer.found_match:
            st.success(f"🎉 **DOKUMEN DITEMUKAN! Nomor Rekening: {ctx.video_transformer.detected_account}**")
            # Jalankan perintah JavaScript suara Beep
            st.components.v1.html("<script>playBeep();</script>", height=0)
