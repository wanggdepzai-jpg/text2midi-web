import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from mido import Message, MidiFile, MidiTrack
import tempfile
import os

# =========================
# 🎵 CORE CONVERSION
# =========================
def image_to_midi(img, time_unit=60, note_base=40, height_limit=120, velocity=100):
    """Chuyển ảnh (PIL Image) -> dữ liệu MIDI (bytes)."""
    if not isinstance(img, Image.Image):
        raise ValueError("Input phải là PIL Image.")
    
    img = img.convert("L")  # Grayscale
    w, h = img.size

    # Giới hạn chiều cao để tránh MIDI quá dài
    if h > height_limit:
        scale = height_limit / h
        new_size = (max(1, int(w * scale)), height_limit)
        img = img.resize(new_size, Image.Resampling.LANCZOS)
        w, h = img.size

    pixels = img.load()
    events = []
    duration = time_unit

    for x in range(w):
        start = x * time_unit
        for y in range(h):
            if pixels[x, y] > 128:  # Pixel sáng -> nốt nhạc
                pitch = note_base + (h - 1 - y)
                if 0 <= pitch <= 127:
                    events.append((start, 'on', pitch))
                    events.append((start + duration, 'off', pitch))

    # Sắp xếp events: off trước on nếu cùng thời gian để tránh overlap
    events.sort(key=lambda e: (e[0], 0 if e[1] == 'off' else 1))

    # Tạo MIDI
    midi = MidiFile()
    track = MidiTrack()
    midi.tracks.append(track)

    current_time = 0
    for ev_time, ev_type, note in events:
        delta = int(ev_time - current_time)
        if delta < 0:
            delta = 0
        msg = Message('note_on' if ev_type == 'on' else 'note_off',
                      note=int(note),
                      velocity=(velocity if ev_type == 'on' else 0),
                      time=delta)
        track.append(msg)
        current_time = ev_time

    num_notes = len(events) // 2
    
    # Sử dụng bộ nhớ tạm máy chủ để tạo file xuất ra dạng bytes cho Web download
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mid") as tmp:
        midi.save(tmp.name)
        tmp_path = tmp.name

    with open(tmp_path, "rb") as f:
        midi_data = f.read()
        
    os.remove(tmp_path)  # Dọn dẹp bộ nhớ tạm
    
    return midi_data, w, h, num_notes


def text_to_image(text, font_bytes, font_size):
    """Tạo ảnh từ văn bản."""
    if not text.strip():
        raise ValueError("Văn bản không được rỗng.")

    try:
        if font_bytes:
            font = ImageFont.truetype(font_bytes, font_size)
        else:
            font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    # Tính kích thước text
    try:
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except AttributeError:
        text_width, text_height = font.getsize(text)

    # Padding linh hoạt (10% của font_size)
    padding = max(10, int(font_size * 0.1))
    img_size = (text_width + 2 * padding, text_height + 2 * padding)
    img = Image.new("L", img_size, color=0)
    draw = ImageDraw.Draw(img)
    draw.text((padding, padding), text, fill=255, font=font)
    return img


# =========================
# 🎨 WEB GUI APPLICATION (STREAMLIT)
# =========================
st.set_page_config(page_title="Text & Image → MIDI Converter", page_icon="🎹", layout="wide")

st.title("🎹 Text & Image → MIDI Converter (Nâng cấp 2026)")
st.markdown("Chuyển đổi văn bản hoặc hình ảnh thành dữ liệu âm thanh MIDI trực tuyến.")

# --- SIDEBAR: SETTINGS (Thay thế cho khung Cài đặt cũ) ---
st.sidebar.header("⚙️ Cài đặt cấu hình")
time_unit = st.sidebar.number_input("Thời gian (ticks/column):", min_value=1, value=60)
note_base = st.sidebar.number_input("Note base (C4=60):", min_value=0, max_value=127, value=40)
height_limit = st.sidebar.slider("Height limit (max rows):", min_value=50, max_value=200, value=120)
velocity = st.sidebar.slider("Velocity (Độ mạnh nốt, 0-127):", min_value=0, max_value=127, value=100)
output_filename = st.sidebar.text_input("Tên file MIDI khi tải về:", value="output.mid")
if not output_filename.endswith(".mid"):
    output_filename += ".mid"

# --- TABS (Thay thế cho ttk.Notebook cũ) ---
tab_text, tab_png = st.tabs(["📝 Text → MIDI", "🖼️ Image → MIDI"])

# --- TAB 1: VĂN BẢN ---
with tab_text:
    st.subheader("Nhập văn bản của bạn")
    text_input = st.text_input("Nội dung chữ:", value="HELLO WORLD")
    
    col_size, col_font = st.columns(2)
    with col_size:
        font_size = st.slider("Cỡ chữ:", min_value=10, max_value=200, value=70)
    with col_font:
        uploaded_font = st.file_uploader("Tải lên Font chữ tùy chọn (.ttf / .otf) (Nếu trống sẽ dùng mặc định)", type=["ttf", "otf"])

    if st.button("🔍 Xem trước & Tạo MIDI từ chữ", type="primary", key="btn_text"):
        try:
            with st.spinner('Đang xử lý hình ảnh và nốt nhạc...'):
                img_text = text_to_image(text_input, uploaded_font, font_size)
                st.image(img_text, caption="Ảnh xem trước (Preview) từ Văn bản", width=400)
                
                midi_bytes, w, h, num_notes = image_to_midi(img_text, time_unit, note_base, height_limit, velocity)
                
                st.success(f"✅ Tạo thành công! Kích thước ảnh: {w}x{h} | Tổng số: {num_notes} nốt nhạc.")
                st.download_button(
                    label="🎶 Click để tải file MIDI về máy",
                    data=midi_bytes,
                    file_name=output_filename,
                    mime="audio/midi"
                )
        except Exception as e:
            st.error(f"❌ Lỗi: {e}")

# --- TAB 2: HÌNH ẢNH ---
with tab_png:
    st.subheader("Tải hình ảnh để quét thành nốt nhạc")
    uploaded_image = st.file_uploader("📂 Chọn file ảnh từ thiết bị của bạn", type=["png", "jpg", "jpeg", "bmp", "gif"])
    
    if uploaded_image is not None:
        try:
            img = Image.open(uploaded_image)
            st.image(img, caption="Ảnh gốc bạn đã tải lên", width=400)
            
            if st.button("🎶 Bắt đầu quét & Tạo MIDI từ ảnh này", type="primary", key="btn_img"):
                with st.spinner('Đang chuyển đổi pixel thành cao độ...'):
                    midi_bytes, w, h, num_notes = image_to_midi(img, time_unit, note_base, height_limit, velocity)
                    
                    st.success(f"✅ Tạo thành công! Kích thước ảnh xử lý: {w}x{h} | Tổng số: {num_notes} nốt nhạc.")
                    st.download_button(
                        label="🎶 Click để tải file MIDI về máy",
                        data=midi_bytes,
                        file_name=output_filename,
                        mime="audio/midi"
                    )
        except Exception as e:
            st.error(f"❌ Không thể xử lý file ảnh này: {e}")
