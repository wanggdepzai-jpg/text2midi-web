import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageDraw, ImageFont, ImageTk
from mido import Message, MidiFile, MidiTrack
import os
from datetime import datetime  # Để thêm timestamp cho log


# =========================
# 🎵 CORE CONVERSION
# =========================
def image_to_midi(img, output_file, time_unit=60, note_base=40, height_limit=120, velocity=100):
    """Chuyển ảnh (PIL Image) -> file MIDI. Nâng cấp: Thêm velocity và height_limit tùy chỉnh."""
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

    # Lưu file
    midi.save(output_file)
    num_notes = len(events) // 2
    return (output_file, w, h, num_notes)


def text_to_image(text, font_path, font_size):
    """Tạo ảnh từ văn bản. Nâng cấp: Padding linh hoạt, hỗ trợ PIL cũ/mới."""
    if not text.strip():
        raise ValueError("Văn bản không được rỗng.")

    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception:
        font = ImageFont.load_default()
        font_path = "Default font"  # Log info

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
# 🎨 GUI APPLICATION
# =========================
class MidiApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🎹 Text & Image → MIDI Converter (Nâng cấp 2025)")
        self.root.geometry("950x750")
        self.root.configure(bg="#1e1e1e")

        # Biến
        self.font_path = tk.StringVar(value="arial.ttf")
        self.font_size = tk.IntVar(value=70)
        self.time_unit = tk.IntVar(value=60)
        self.note_base = tk.IntVar(value=40)
        self.height_limit = tk.IntVar(value=120)
        self.velocity = tk.IntVar(value=100)
        self.text_input = tk.StringVar(value="HELLO WORLD")
        self.image_path = tk.StringVar(value="")
        self.output_path = tk.StringVar(value="output.mid")

        self._build_menu()
        self._build_ui()

    # ---------------- MENU ----------------
    def _build_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0, bg="#252526", fg="white")
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=0, bg="#252526", fg="white")
        help_menu.add_command(label="About", command=self._about)
        menubar.add_cascade(label="Help", menu=help_menu)

    def _about(self):
        messagebox.showinfo("About", "Text & Image to MIDI Converter v2025\nNâng cấp: Hỗ trợ font browse, multi-image, velocity, height limit.\nDùng PIL & Mido.")

    # ---------------- UI ----------------
    def _build_ui(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # --- TAB TEXT ---
        tab_text = tk.Frame(notebook, bg="#252526")
        notebook.add(tab_text, text="📝 Text → MIDI")

        tk.Label(tab_text, text="Nhập văn bản:", fg="white", bg="#252526").pack(pady=5)
        tk.Entry(tab_text, textvariable=self.text_input, width=60, bg="#3c3c3c", fg="white").pack(pady=5)

        # Font path với browse
        font_frame = tk.Frame(tab_text, bg="#252526")
        font_frame.pack(pady=5)
        tk.Label(font_frame, text="Font path:", fg="white", bg="#252526").pack(side="left")
        tk.Entry(font_frame, textvariable=self.font_path, width=50, bg="#3c3c3c", fg="white").pack(side="left", padx=5)
        tk.Button(font_frame, text="Browse", bg="#2196F3", fg="white", command=self.browse_font).pack(side="left", padx=5)

        tk.Label(tab_text, text="Cỡ chữ:", fg="white", bg="#252526").pack(pady=(10,0))
        tk.Scale(tab_text, from_=10, to=200, orient="horizontal", variable=self.font_size,
                 bg="#252526", fg="white", troughcolor="#333").pack(fill="x", padx=40)

        self.preview_label_text = tk.Label(tab_text, bg="#1e1e1e", relief="sunken", bd=2)
        self.preview_label_text.pack(pady=10)

        tk.Button(tab_text, text="🔍 Xem trước", bg="#2196F3", fg="white",
                  command=self.preview_text).pack(pady=5)

        tk.Button(tab_text, text="🎶 Tạo MIDI từ chữ", bg="#00C853", fg="white",
                  command=self.create_text_midi).pack(pady=10)

        # --- TAB IMAGE ---
        tab_png = tk.Frame(notebook, bg="#252526")
        notebook.add(tab_png, text="🖼️ Image → MIDI")

        tk.Button(tab_png, text="📂 Chọn ảnh (PNG/JPG/BMP/GIF)", bg="#0078D7", fg="white",
                  command=self.choose_image).pack(pady=5)
        tk.Entry(tab_png, textvariable=self.image_path, width=60, bg="#3c3c3c", fg="white").pack(pady=5)

        self.preview_label_png = tk.Label(tab_png, bg="#1e1e1e", relief="sunken", bd=2)
        self.preview_label_png.pack(pady=10)

        tk.Button(tab_png, text="🎶 Tạo MIDI từ ảnh", bg="#00C853", fg="white",
                  command=self.create_image_midi).pack(pady=10)

        # --- SETTINGS ---
        settings = tk.LabelFrame(self.root, text="⚙️ Cài đặt", bg="#1e1e1e", fg="white", padx=10, pady=10)
        settings.pack(fill="x", padx=10, pady=5)

        # Grid layout cho settings
        row = 0
        tk.Label(settings, text="Thời gian (ticks/column):", fg="white", bg="#1e1e1e").grid(row=row, column=0, sticky="w", padx=5, pady=5)
        tk.Entry(settings, textvariable=self.time_unit, width=8, bg="#3c3c3c", fg="white").grid(row=row, column=1, padx=5)
        tk.Label(settings, text="Note base (C4=60):", fg="white", bg="#1e1e1e").grid(row=row, column=2, sticky="w", padx=5)
        tk.Entry(settings, textvariable=self.note_base, width=8, bg="#3c3c3c", fg="white").grid(row=row, column=3, padx=5)
        row += 1

        tk.Label(settings, text="Height limit (max rows):", fg="white", bg="#1e1e1e").grid(row=row, column=0, sticky="w", padx=5, pady=5)
        height_frame = tk.Frame(settings, bg="#1e1e1e")
        height_frame.grid(row=row, column=1, columnspan=2, sticky="w", padx=5)
        tk.Entry(height_frame, textvariable=self.height_limit, width=8, bg="#3c3c3c", fg="white").pack(side="left")
        tk.Scale(height_frame, from_=50, to=200, orient="horizontal", variable=self.height_limit, length=150,
                 bg="#1e1e1e", fg="white", troughcolor="#333").pack(side="left", padx=5)
        row += 1

        tk.Label(settings, text="Velocity (0-127):", fg="white", bg="#1e1e1e").grid(row=row, column=0, sticky="w", padx=5, pady=5)
        tk.Scale(settings, from_=0, to=127, orient="horizontal", variable=self.velocity,
                 bg="#1e1e1e", fg="white", troughcolor="#333").grid(row=row, column=1, columnspan=2, sticky="w", padx=5)
        row += 1

        tk.Label(settings, text="Output MIDI file:", fg="white", bg="#1e1e1e").grid(row=row, column=0, sticky="w", padx=5, pady=5)
        out_frame = tk.Frame(settings, bg="#1e1e1e")
        out_frame.grid(row=row, column=1, columnspan=4, sticky="ew", padx=5)
        tk.Entry(out_frame, textvariable=self.output_path, width=40, bg="#3c3c3c", fg="white").pack(side="left", fill="x", expand=True)
        tk.Button(out_frame, text="Browse", bg="#2196F3", fg="white", command=self.browse_output).pack(side="right", padx=5)
        settings.columnconfigure(1, weight=1)

        # --- LOG ---
        log_frame = tk.Frame(self.root, bg="#1e1e1e")
        log_frame.pack(fill="both", expand=False, padx=10, pady=5)
        tk.Label(log_frame, text="📋 Log:", fg="white", bg="#1e1e1e").pack(anchor="w")
        self.log = tk.Text(log_frame, height=8, bg="#111", fg="lime", font=("Consolas", 9), wrap="word")
        scrollbar = tk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=scrollbar.set)
        self.log.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    # ---------------- EVENTS ----------------
    def log_msg(self, text):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log.insert("end", f"[{timestamp}] {text}\n")
        self.log.see("end")

    def browse_font(self):
        path = filedialog.askopenfilename(filetypes=[("Font files", "*.ttf *.otf")])
        if path:
            self.font_path.set(path)
            self.log_msg(f"📄 Font đã chọn: {os.path.basename(path)}")

    def browse_output(self):
        path = filedialog.asksaveasfilename(defaultextension=".mid", filetypes=[("MIDI files", "*.mid")])
        if path:
            self.output_path.set(path)
            self.log_msg(f"💾 Output sẽ lưu tại: {os.path.basename(path)}")

    def validate_inputs(self):
        """Validation cơ bản."""
        if self.time_unit.get() <= 0:
            raise ValueError("Time unit phải > 0.")
        if self.font_size.get() <= 0:
            raise ValueError("Font size phải > 0.")
        if self.height_limit.get() < 10:
            raise ValueError("Height limit phải >= 10.")
        if not (0 <= self.velocity.get() <= 127):
            raise ValueError("Velocity phải từ 0-127.")

    def preview_text(self):
        try:
            self.validate_inputs()
            text = self.text_input.get().strip()
            font_path = self.font_path.get()
            font_size = self.font_size.get()
            img = text_to_image(text, font_path, font_size)

            # Preview
            preview = img.copy().convert("RGB")
            preview.thumbnail((400, 200), Image.Resampling.LANCZOS)
            tk_img = ImageTk.PhotoImage(preview)
            self.preview_label_text.configure(image=tk_img)
            self.preview_label_text.image = tk_img

            self.log_msg("✅ Preview text thành công.")
        except Exception as e:
            messagebox.showerror("Lỗi Preview", str(e))
            self.log_msg(f"❌ Lỗi preview text: {e}")

    def choose_image(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif")])
        if not path:
            return
        if not os.path.exists(path):
            messagebox.showerror("Lỗi", "File không tồn tại!")
            return
        self.image_path.set(path)
        try:
            img = Image.open(path)
            preview = img.copy().convert("RGB")
            preview.thumbnail((400, 200), Image.Resampling.LANCZOS)
            tk_img = ImageTk.PhotoImage(preview)
            self.preview_label_png.configure(image=tk_img)
            self.preview_label_png.image = tk_img
            self.log_msg(f"🖼️ Ảnh đã chọn: {os.path.basename(path)} (Kích thước: {img.size})")
        except Exception as e:
            messagebox.showerror("Lỗi Load Ảnh", str(e))
            self.log_msg(f"❌ Không thể load ảnh: {e}")

    def create_text_midi(self):
        try:
            self.validate_inputs()
            text = self.text_input.get().strip()
            if not text:
                raise ValueError("Chưa nhập văn bản!")

            # Chọn output nếu chưa có
            out = self.output_path.get().strip()
            if not out:
                out = filedialog.asksaveasfilename(defaultextension=".mid", filetypes=[("MIDI files", "*.mid")])
                if not out:
                    return
                self.output_path.set(out)

            font_path = self.font_path.get().strip()
            font_size = self.font_size.get()
            time_unit = self.time_unit.get()
            note_base = self.note_base.get()
            height_limit = self.height_limit.get()
            velocity = self.velocity.get()

            img = text_to_image(text, font_path, font_size)
            res = image_to_midi(img, out, time_unit, note_base, height_limit, velocity)
            self.log_msg(f"✅ Tạo MIDI từ text thành công: {res[0]} (Kích thước: {res[1]}x{res[2]}, {res[3]} nốt)")
            messagebox.showinfo("Hoàn tất", f"Đã tạo file MIDI:\n{res[0]}\nSố nốt: {res[3]}")
        except Exception as e:
            self.log_msg(f"❌ Lỗi tạo MIDI từ text: {e}")
            messagebox.showerror("Lỗi", str(e))

    def create_image_midi(self):
        try:
            self.validate_inputs()
            path = self.image_path.get().strip()
            if not path or not os.path.exists(path):
                raise ValueError("Chưa chọn ảnh hợp lệ!")

            # Chọn output nếu chưa có
            out = self.output_path.get().strip()
            if not out:
                out = filedialog.asksaveasfilename(defaultextension=".mid", filetypes=[("MIDI files", "*.mid")])
                            # Chọn output nếu chưa có
            out = self.output_path.get().strip()
            if not out:
                out = filedialog.asksaveasfilename(defaultextension=".mid", filetypes=[("MIDI files", "*.mid")])
                if not out:
                    return
                self.output_path.set(out)
            img = Image.open(path)
            time_unit = self.time_unit.get()
            note_base = self.note_base.get()
            height_limit = self.height_limit.get()
            velocity = self.velocity.get()
            res = image_to_midi(img, out, time_unit, note_base, height_limit, velocity)
            self.log_msg(f"Tạo MIDI từ ảnh thành công: {res[0]} (Kích thước: {res[1]}x{res[2]}, {res[3]} nốt)")
            messagebox.showinfo("Hoàn tất", f"Đã tạo file MIDI:\n{res[0]}\nSố nốt: {res[3]}")
        except Exception as e:
            self.log_msg(f"Lỗi tạo MIDI từ ảnh: {e}")
            messagebox.showerror("Lỗi", str(e))
# =========================
#  MAIN
# =========================
if __name__ == "__main__":
    root = tk.Tk()
    style = ttk.Style()
    try:
        style.theme_use("clam")  # Dark theme nếu có
    except:
        pass
    app = MidiApp(root)
    root.mainloop()