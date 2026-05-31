import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from mido import Message, MidiFile, MidiTrack
import tempfile
import os

# =========================
# 🎵 CORE CONVERSION
# =========================
def process_image_for_preview(img, height_limit, threshold):
    """Xử lý ảnh để cho ra bản đồ pixel Trắng/Đen (Mô phỏng nốt nhạc)"""
    img = img.convert("L")  # Đưa về thang độ xám
    w, h = img.size

    # Cắt gọn chiều cao
    if h > height_limit:
        scale = height_limit / h
        new_size = (max(1, int(w * scale)), height_limit)
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    # Lọc pixel theo ngưỡng (Threshold)
    # Những pixel > threshold sẽ biến thành màu trắng (255) -> Đại diện cho Nốt nhạc
    # Những pixel <= threshold sẽ biến thành màu đen (0) -> Đại diện cho sự im lặng
    preview_img = img.point(lambda p: 255 if p > threshold else 0)
    return preview_img

def image_to_midi(img, time_unit=60, note_base=40, velocity=100, threshold=128):
    """Chuyển ảnh (đã qua tiền xử lý) -> dữ liệu MIDI."""
    w, h = img.size
    pixels = img.load()
    events = []
    duration = time_unit

    for x in range(w):
        start = x * time_unit
        for y in range(h):
            # Vì ảnh đầu vào đã là đen trắng (0 hoặc 255) qua hàm preview,
            # ta chỉ cần bắt các pixel trắng (255)
            if pixels[x, y] > threshold:  
                pitch = note_base + (h - 1 - y)
                if 0 <= pitch <= 127:
                    events.append((start, 'on', pitch))
                    events.append((start + duration, 'off', pitch))

    events.sort(key=lambda e: (e[0], 0 if e[1] == 'off' else 1))

    midi = MidiFile()
    track = MidiTrack()
    midi.tracks.append(track)

    current_time = 0
    for ev_time, ev_type, note in events:
        delta = int(ev_time - current_time)
        if delta < 0: delta = 0
        msg = Message('note_on' if ev_type == 'on' else 'note_off',
                      note=int(note),
                      velocity=(velocity if ev_type == 'on' else 0),
                      time=delta)
        track.append(msg)
        current_time = ev_time

    num_notes = len(events) // 2
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mid") as tmp:
        midi.save(tmp.name)
        tmp_path = tmp.name

    with open(tmp_path, "rb") as f:
        midi_data = f.read()
        
    os.remove(tmp_path) 
    
    return midi_data, w, h, num_notes


def text_to_image(text, font_bytes, font_size):
    """Tạo ảnh grayscale từ văn bản."""
    if not text.strip(): return None

    try:
        if font_bytes:
            font = ImageFont.truetype(font_bytes, font_size)
        else:
            font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    try:
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except AttributeError:
        text_width, text_height = font.getsize(text)

    padding = max(10, int(font_size * 0.1))
    img_size = (text_width + 2 * padding, text_height + 2 * padding)
    img = Image.new("L", img_size, color=0)
    draw = ImageDraw.Draw(img)
    draw.text((padding, padding), text, fill=255, font=font)
    return img


# =========================
# 🎨 WEB GUI APPLICATION
# =========================
st.set_page_config(page_title="Text & Image → MIDI", page_icon="🎹", layout="wide")

st.title("🎹 Trình tạo MIDI từ Hình ảnh & Chữ")
st.markdown("Tinh chỉnh pixel trực tiếp trên web trước khi xuất file âm thanh.")

# --- SIDEBAR: CÀI ĐẶT THÔNG SỐ & CHỈNH SỬA PIXEL ---
st.sidebar.header("🛠️ Tinh chỉnh Pixel & MIDI")
threshold = st.sidebar.slider("Ngưỡng tạo nốt (Threshold):", min_value=0, max_value=255, value=128, 
                              help="Kéo để chỉnh độ nhạy. Màu trắng sẽ là nốt nhạc, màu đen là im lặng.")
height_limit = st.sidebar.slider("Độ cao (Quãng nốt tối đa):", min_value=10, max_value=200, value=80)
note_base = st.sidebar.number_input("Nốt gốc (Base Note):", min_value=0, max_value=127, value=30)
time_unit = st.sidebar.number_input("Độ dài 1 Pixel (ticks):", min_value=1, value=60)
velocity = st.sidebar.slider("Lực gõ phím (Velocity):", min_value=0, max_value=127, value=100)

output_filename = st.sidebar.text_input("Tên file tải về:", value="ban_nhac_pixel.mid")
if not output_filename.endswith(".mid"): output_filename += ".mid"

# --- TABS ---
tab_text, tab_png = st.tabs(["📝 Chữ → MIDI", "🖼️ Ảnh → MIDI"])

# --- TAB 1: TEXT ---
with tab_text:
    col_input, col_preview = st.columns([1, 1])
    
    with col_input:
        st.subheader("1. Nhập văn bản")
        text_input = st.text_input("Nội dung:", value="HELLO")
        font_size = st.slider("Cỡ chữ (Phóng to/Thu nhỏ):", min_value=10, max_value=300, value=70)
        uploaded_font = st.file_uploader("Tải Font (.ttf / .otf)", type=["ttf", "otf"], key="font_upload")

    with col_preview:
        st.subheader("2. Xem trước bản đồ Nốt nhạc")
        if text_input:
            raw_img = text_to_image(text_input, uploaded_font, font_size)
            if raw_img:
                # Áp dụng bộ lọc pixel
                preview_img = process_image_for_preview(raw_img, height_limit, threshold)
                
                st.image(preview_img, caption="Phần màu Trắng sẽ biến thành tiếng đàn", use_column_width=True)
                
                if st.button("🎶 XUẤT FILE MIDI TỪ CHỮ NÀY", type="primary", use_container_width=True):
                    try:
                        midi_bytes, w, h, num_notes = image_to_midi(preview_img, time_unit, note_base, velocity, threshold)
                        st.success(f"✅ Đã tạo {num_notes} nốt nhạc!")
                        st.download_button("⬇️ TẢI FILE MIDI XUỐNG", data=midi_bytes, file_name=output_filename, mime="audio/midi", use_container_width=True)
                    except Exception as e:
                        st.error(f"Lỗi: {e}")

# --- TAB 2: IMAGE ---
with tab_png:
    col_img_input, col_img_preview = st.columns([1, 1])
    
    with col_img_input:
        st.subheader("1. Tải ảnh lên")
        uploaded_image = st.file_uploader("Chọn ảnh (Tốt nhất là ảnh nét, ít màu)", type=["png", "jpg", "jpeg", "bmp", "gif"])
        if uploaded_image:
            raw_img = Image.open(uploaded_image)
            st.image(raw_img, caption="Ảnh gốc của bạn")
            
    with col_img_preview:
        st.subheader("2. Tinh chỉnh Pixel")
        st.info("Kéo thanh 'Ngưỡng tạo nốt' và 'Độ cao' ở menu bên trái để chỉnh sửa hình dáng nốt nhạc.")
        if uploaded_image:
            # Áp dụng bộ lọc pixel trực tiếp
            preview_img = process_image_for_preview(raw_img, height_limit, threshold)
            st.image(preview_img, caption="Bản đồ MIDI (Trắng = Đánh đàn, Đen = Im lặng)", use_column_width=True)
            
            if st.button("🎶 XUẤT FILE MIDI TỪ ẢNH NÀY", type="primary", use_container_width=True):
                try:
                    with st.spinner("Đang chuyển Pixel thành MIDI..."):
                        midi_bytes, w, h, num_notes = image_to_midi(preview_img, time_unit, note_base, velocity, threshold)
                        st.success(f"✅ Đã tạo {num_notes} nốt nhạc!")
                        st.download_button("⬇️ TẢI FILE MIDI XUỐNG", data=midi_bytes, file_name=output_filename, mime="audio/midi", use_container_width=True)
                except Exception as e:
                    st.error(f"Lỗi: {e}")
