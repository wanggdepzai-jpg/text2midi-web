import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from mido import Message, MidiFile, MidiTrack
import tempfile
import os

# =========================
# 🎵 CORE CONVERSION & VIP LOGIC
# =========================
def enhance_image(img, sharpness=1.0, contrast=1.0, brightness=1.0):
    """Tiền xử lý ảnh (VIP Mode) để tăng độ chi tiết trước khi quét"""
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    img = ImageEnhance.Sharpness(img).enhance(sharpness)
    img = ImageEnhance.Contrast(img).enhance(contrast)
    img = ImageEnhance.Brightness(img).enhance(brightness)
    return img

def image_to_midi_advanced(img, time_unit=60, note_base=24, height_limit=128, 
                           threshold=50, dynamic_duration=False, dynamic_velocity=False):
    """Chuyển đổi với khả năng phân tích chi tiết sâu (Độ dài & Lực gõ)"""
    img = img.convert("L")  # Chuyển về thang độ xám (Grayscale 0-255)
    w, h = img.size

    # Ép chiều cao tối đa bằng đúng giới hạn của chuẩn MIDI (128 nốt)
    max_h = min(height_limit, 128)
    if h > max_h:
        scale = max_h / h
        new_size = (max(1, int(w * scale)), max_h)
        img = img.resize(new_size, Image.Resampling.LANCZOS)
        w, h = img.size

    pixels = img.load()
    events = []

    for x in range(w):
        start = x * time_unit
        for y in range(h):
            p_val = pixels[x, y]  # Giá trị độ sáng pixel (0: Đen, 255: Trắng tinh)
            
            if p_val > threshold:  # Nếu sáng hơn ngưỡng thì tạo nốt
                pitch = note_base + (h - 1 - y)
                
                # Chống tràn nốt MIDI (0-127)
                if 0 <= pitch <= 127:
                    # 1. Tính toán Velocity (Lực gõ / Màu sắc trong FL Studio)
                    vel = int((p_val / 255.0) * 127) if dynamic_velocity else 100
                    vel = max(1, min(vel, 127))
                    
                    # 2. Tính toán Độ dài nốt (Duration / Chi tiết bề mặt)
                    if dynamic_duration:
                        # Pixel càng sáng -> Nốt càng dài (Từ 20% đến 150% của time_unit chuẩn)
                        dur_factor = 0.2 + (p_val / 255.0) * 1.3
                        dur = int(time_unit * dur_factor)
                    else:
                        dur = time_unit

                    events.append((start, 'on', pitch, vel))
                    events.append((start + dur, 'off', pitch, 0))

    # Sắp xếp các sự kiện theo dòng thời gian
    events.sort(key=lambda e: (e[0], 0 if e[1] == 'off' else 1))

    # Ghi vào file MIDI
    midi = MidiFile()
    track = MidiTrack()
    midi.tracks.append(track)

    current_time = 0
    for ev in events:
        ev_time, ev_type, pitch, vel = ev
        delta = int(ev_time - current_time)
        if delta < 0: delta = 0
        
        msg = Message('note_on' if ev_type == 'on' else 'note_off',
                      note=int(pitch),
                      velocity=int(vel),
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
    
    return midi_data, w, h, num_notes, img


def text_to_image(text, font_bytes, font_size):
    if not text.strip(): return None
    try:
        font = ImageFont.truetype(font_bytes, font_size) if font_bytes else ImageFont.load_default()
    except:
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
st.set_page_config(page_title="MIDI Art Studio", page_icon="🎨", layout="wide")

st.title("🎨 MIDI Art Studio cho FL Studio")
st.markdown("Chuyển đổi hình ảnh thành MIDI với độ chi tiết siêu cao nhờ áp dụng biến thiên theo Pixel.")

# --- SIDEBAR: CÀI ĐẶT CƠ BẢN ---
st.sidebar.header("⚙️ Thiết lập MIDI cơ bản")
time_unit = st.sidebar.number_input("Khoảng cách Pixel (ticks):", min_value=10, value=60, help="Độ rộng tổng thể của bức tranh trên Piano Roll.")
note_base = st.sidebar.number_input("Nốt gốc (Base Note):", min_value=0, max_value=127, value=12, help="Nốt thấp nhất (Trục Y). Khuyên dùng 12 hoặc 24.")
height_limit = st.sidebar.slider("Độ cao (Max 128 nốt):", min_value=10, max_value=128, value=100)
threshold = st.sidebar.slider("Ngưỡng bắt nốt (Threshold):", min_value=0, max_value=255, value=30, help="Hạ thấp để lấy nhiều chi tiết ở vùng tối.")

output_filename = st.sidebar.text_input("Tên file lưu trữ:", value="fl_studio_art.mid")
if not output_filename.endswith(".mid"): output_filename += ".mid"

# --- SIDEBAR: CHẾ ĐỘ VIP ---
st.sidebar.markdown("---")
st.sidebar.header("💎 Chế độ VIP (Siêu chi tiết)")
is_vip = st.sidebar.toggle("Kích hoạt VIP Mode", value=True)

if is_vip:
    st.sidebar.caption("1. Xử lý ảnh (Làm nét khối)")
    sharpness = st.sidebar.slider("Độ sắc nét (Sharpness)", 0.0, 5.0, 2.0, 0.1)
    contrast = st.sidebar.slider("Tương phản (Contrast)", 0.0, 5.0, 1.5, 0.1)
    brightness = st.sidebar.slider("Độ sáng (Brightness)", 0.0, 3.0, 1.0, 0.1)
    
    st.sidebar.caption("2. Chi tiết 3D (Piano Roll)")
    dynamic_velocity = st.sidebar.checkbox("Màu sắc theo Pixel (Dynamic Velocity)", value=True, help="FL Studio sẽ hiển thị nốt đậm/nhạt tùy theo pixel.")
    dynamic_duration = st.sidebar.checkbox("Độ dài theo Pixel (Dynamic Duration)", value=True, help="Tạo hiệu ứng răng cưa/chất liệu bề mặt cho ảnh.")
else:
    sharpness, contrast, brightness = 1.0, 1.0, 1.0
    dynamic_velocity, dynamic_duration = False, False

# --- GIAO DIỆN CHÍNH ---
tab_text, tab_png = st.tabs(["📝 Tạo từ Chữ", "🖼️ Tạo từ Ảnh"])

# --- TAB 1: TEXT ---
with tab_text:
    col_in1, col_out1 = st.columns(2)
    with col_in1:
        text_input = st.text_input("Nhập chữ:", value="FL STUDIO")
        font_size = st.slider("Cỡ chữ:", 10, 300, 80)
        font_upload = st.file_uploader("Upload Font (.ttf)", type=["ttf", "otf"])
    
    with col_out1:
        if text_input:
            raw_img = text_to_image(text_input, font_upload, font_size)
            if raw_img:
                if is_vip: raw_img = enhance_image(raw_img, sharpness, contrast, brightness)
                st.image(raw_img, caption="Ảnh Preview (Đã áp dụng bộ lọc VIP)")
                
                if st.button("🚀 XUẤT MIDI TỪ CHỮ", type="primary", use_container_width=True):
                    try:
                        midi_bytes, w, h, notes, final_img = image_to_midi_advanced(
                            raw_img, time_unit, note_base, height_limit, threshold, dynamic_duration, dynamic_velocity)
                        st.success(f"✅ Đã kết xuất {notes} nốt nhạc siêu chi tiết!")
                        st.download_button("⬇️ TẢI XUỐNG", data=midi_bytes, file_name=output_filename, mime="audio/midi", use_container_width=True)
                    except Exception as e:
                        st.error(str(e))

# --- TAB 2: IMAGE ---
with tab_png:
    col_in2, col_out2 = st.columns(2)
    with col_in2:
        img_upload = st.file_uploader("Tải ảnh bất kỳ lên", type=["png", "jpg", "jpeg"])
        if img_upload:
            original_img = Image.open(img_upload)
            st.image(original_img, caption="Ảnh gốc")
            
    with col_out2:
        if img_upload:
            # Tiền xử lý
            processed_img = original_img.copy()
            if is_vip: 
                processed_img = enhance_image(processed_img, sharpness, contrast, brightness)
            
            st.image(processed_img.convert("L"), caption="Bản đồ quét Grayscale thực tế")
            
            if st.button("🚀 XUẤT MIDI TỪ ẢNH NÀY", type="primary", use_container_width=True):
                try:
                    with st.spinner("Đang nội suy điểm ảnh..."):
                        midi_bytes, w, h, notes, final_img = image_to_midi_advanced(
                            processed_img, time_unit, note_base, height_limit, threshold, dynamic_duration, dynamic_velocity)
                        st.success(f"✅ Hoàn tất! Quét được {notes} nốt nhạc.")
                        st.download_button("⬇️ TẢI XUỐNG", data=midi_bytes, file_name=output_filename, mime="audio/midi", use_container_width=True)
                except Exception as e:
                    st.error(str(e))
