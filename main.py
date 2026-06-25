import os
import random
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageTk

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import pygame
except ImportError:
    pygame = None


CARD_COLOR = "#4a576a"
TEXT_GRAY = "#9fa5ae"
MAX_PHONES = 16
PHONE_WIDTH = 230
PHONE_HEIGHT = 110
ICON_SIZE = 14
ID_ROW_WIDTH = 170
ID_ROW_HEIGHT = 22
PROGRESS_WIDTH = 112
PROGRESS_HEIGHT = 24
SIDEBAR_WIDTH = 148
VIDEO_TARGET_FPS = 6
ZOOM_TARGET_FPS = 3
CANVAS_X = SIDEBAR_WIDTH + 1
CANVAS_WIDTH = 1160 - CANVAS_X
CANVAS_HEIGHT = 650
GRID_LEFT = 16
GRID_TOP = 24
GRID_COL_STEP = 245
GRID_ROW_STEP = 148
BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
WINDOWS_FONT_DIR = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
WINDOWS_PIL_FONTS = [
    WINDOWS_FONT_DIR / "msyh.ttc",
    WINDOWS_FONT_DIR / "msyhbd.ttc",
    WINDOWS_FONT_DIR / "simhei.ttf",
    WINDOWS_FONT_DIR / "segoeui.ttf",
    WINDOWS_FONT_DIR / "arial.ttf",
]
TK_UI_FONT = "Microsoft YaHei UI"
TK_LATIN_FONT = "Segoe UI"


class CloudPhoneManager(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("红手指")
        self.geometry("1160x650")
        self.resizable(False, False)
        self.configure(bg="#f6f8fb")

        start_id = random.randint(73000000, 86000000)
        self.phone_ids = [str(start_id + index) for index in range(MAX_PHONES)]
        self.phone_buttons = []
        self.id_buttons = []
        self.id_row_images = []
        self.phone_current_images = []
        self.phone_image = self.make_phone_image()
        self.audio_pil = self.make_status_pil("音频播放中")
        self.audio_image = ImageTk.PhotoImage(self.audio_pil)
        self.device_icon_source = self.load_pil_icon("device.png")
        self.upload_icon_source = self.load_pil_icon("upload.png")
        self.video_capture = None
        self.video_after_id = None
        self.video_frame_image = None
        self.video_fps = 25
        self.video_source_fps = 25
        self.video_frame_step = 1.0
        self.video_skip_remainder = 0.0
        self.video_path = None
        self.video_start_seconds = 0
        self.media_duration = 0
        self.current_progress_seconds = 0
        self.media_kind = None
        self.is_dragging_progress = False
        self.is_paused = False
        self.progress_after_id = None
        self.progress_bar_image = None
        self.material_paths = []
        self.pygame_ready = False
        self.audio_path = None
        self.audio_seek_seconds = 0
        self.rename_text = ""
        self.rename_editing = False
        self.rename_input_visible = False
        self.selected_phone_index = None
        self.zoom_window = None
        self.zoom_button = None
        self.zoom_image = None
        self.video_frame_count = 0
        self.last_zoom_update_at = 0
        self.last_progress_update_at = 0
        self.current_content_pil = None
        self.current_zoom_content_pil = None
        self.grid_base_image = None
        self.grid_photo_image = None
        self.grid_image_item = None
        self.phone_canvas = None

        self.build_ui()
        self.show_all_phones()

    def make_phone_image(self):
        image = tk.PhotoImage(width=PHONE_WIDTH, height=PHONE_HEIGHT)
        image.put(CARD_COLOR, to=(0, 0, PHONE_WIDTH, PHONE_HEIGHT))
        image.put("#566477", to=(18, 15, 96, 25))
        image.put("#687689", to=(148, 78, 210, 87))
        image.put("#627083", to=(22, 80, 40, 100))
        return image

    def make_status_pil(self, text):
        image = Image.new("RGB", (PHONE_WIDTH, PHONE_HEIGHT), CARD_COLOR)
        draw = ImageDraw.Draw(image)
        font = self.get_status_font()
        text_box = draw.textbbox((0, 0), text, font=font)
        x = (PHONE_WIDTH - (text_box[2] - text_box[0])) // 2
        y = (PHONE_HEIGHT - (text_box[3] - text_box[1])) // 2 - text_box[1]
        draw.text((x, y), text, fill="#d9dee7", font=font)
        return image

    def make_status_image(self, text):
        return ImageTk.PhotoImage(self.make_status_pil(text))

    def make_phone_card_pil(self, number):
        image = Image.new("RGB", (PHONE_WIDTH, PHONE_HEIGHT), CARD_COLOR)
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((0, 0, PHONE_WIDTH - 1, PHONE_HEIGHT - 1), radius=2, fill=CARD_COLOR)
        draw.rounded_rectangle((18, 15, 96, 25), radius=3, fill="#566477")
        draw.rounded_rectangle((148, 78, 210, 87), radius=3, fill="#687689")
        draw.rounded_rectangle((22, 80, 40, 100), radius=4, fill="#627083")
        font = self.get_pil_font(15)
        label = f"{number:02d}   Cloud Phone"
        text_box = draw.textbbox((0, 0), label, font=font)
        x = (PHONE_WIDTH - (text_box[2] - text_box[0])) // 2
        y = (PHONE_HEIGHT - (text_box[3] - text_box[1])) // 2 - text_box[1]
        draw.text((x, y), label, fill="#d9dee7", font=font)
        return image

    def load_pil_icon(self, file_name):
        icon_path = BASE_DIR / "assets" / file_name
        if icon_path.exists():
            image = Image.open(icon_path).convert("RGBA")
            image = image.resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS)
            return image

        image = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (255, 255, 255, 0))
        return image

    def make_id_row_pil(self, phone_id):
        image = Image.new("RGBA", (ID_ROW_WIDTH, ID_ROW_HEIGHT), (255, 255, 255, 255))
        draw = ImageDraw.Draw(image)
        font = self.get_id_font()

        icon_y = (ID_ROW_HEIGHT - ICON_SIZE) // 2
        image.alpha_composite(self.device_icon_source, (0, icon_y))
        text_x = ICON_SIZE + 4
        sample_box = draw.textbbox((0, 0), phone_id, font=font)
        text_height = sample_box[3] - sample_box[1]
        text_y = (ID_ROW_HEIGHT - text_height) // 2 - sample_box[1]
        draw.text((text_x, text_y), phone_id, fill=TEXT_GRAY, font=font)

        text_box = draw.textbbox((text_x, text_y), phone_id, font=font)
        upload_x = min(text_box[2] + 6, ID_ROW_WIDTH - ICON_SIZE)
        image.alpha_composite(self.upload_icon_source, (upload_x, icon_y))

        return image

    def make_id_row_image(self, phone_id):
        return ImageTk.PhotoImage(self.make_id_row_pil(phone_id))

    def get_pil_font(self, size):
        for path in WINDOWS_PIL_FONTS:
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                continue
        return ImageFont.load_default()

    def get_id_font(self):
        return self.get_pil_font(11)

    def get_status_font(self):
        return self.get_pil_font(16)

    def build_ui(self):
        self.sidebar = tk.Frame(self, bg="#eef3f8")
        self.sidebar.place(x=0, y=0, width=SIDEBAR_WIDTH, height=650)

        tk.Label(
            self.sidebar,
            text="红手指",
            bg="#eef3f8",
            fg="#1f2937",
            font=(TK_UI_FONT, 16, "bold"),
        ).place(x=20, y=18, width=108, height=26)
        tk.Label(
            self.sidebar,
            text="素材控制台",
            bg="#eef3f8",
            fg="#7b8794",
            font=(TK_UI_FONT, 9),
        ).place(x=20, y=45, width=108, height=18)

        self.add_left_button("上传视频", 82, self.upload_video, primary=True)
        self.add_left_button("上传语音", 132, self.upload_audio)
        self.add_left_button("批量素材", 182, self.batch_upload_materials)
        self.rename_button = self.add_left_button("批量改名", 250, self.batch_rename)

        self.rename_entry = tk.Entry(
            self.sidebar,
            font=(TK_UI_FONT, 11),
            relief=tk.FLAT,
            bd=0,
            bg="#ffffff",
            fg="#1f2937",
            insertbackground="#2563eb",
            highlightthickness=1,
            highlightcolor="#60a5fa",
            highlightbackground="#cfd8e3",
            justify="center",
        )
        self.rename_entry.bind("<Return>", lambda _event: self.batch_rename())
        self.rename_entry.bind("<Escape>", lambda _event: self.hide_rename_entry())

        tk.Frame(self, bg="#dfe7f0").place(x=SIDEBAR_WIDTH, y=0, width=1, height=650)
        self.phone_canvas = tk.Canvas(
            self,
            width=CANVAS_WIDTH,
            height=CANVAS_HEIGHT,
            bg="#f6f8fb",
            bd=0,
            highlightthickness=0,
        )
        self.phone_canvas.place(x=CANVAS_X, y=0, width=CANVAS_WIDTH, height=CANVAS_HEIGHT)
        self.grid_image_item = self.phone_canvas.create_image(0, 0, anchor=tk.NW)
        self.phone_canvas.bind("<Button-1>", self.on_phone_canvas_click)
        self.build_progress_controls()

    def build_progress_controls(self):
        self.play_pause_button = self.make_sidebar_button(
            self.sidebar,
            "暂停",
            self.toggle_pause,
            bg="#ffffff",
            fg="#1f2937",
            active_bg="#e8eef6",
        )
        self.progress_button = tk.Label(
            self.sidebar,
            text="进度 0:00 / 0:00",
            font=(TK_UI_FONT, 9),
            bg="#eef3f8",
            fg="#687385",
        )
        self.progress_bar_button = tk.Button(
            self.sidebar,
            relief=tk.FLAT,
            bd=0,
            padx=0,
            pady=0,
            bg="#eef3f8",
            activebackground="#eef3f8",
            highlightthickness=0,
            takefocus=0,
            cursor="hand2",
        )
        self.progress_bar_button.bind("<ButtonPress-1>", self.on_progress_press)
        self.progress_bar_button.bind("<B1-Motion>", self.on_progress_drag)
        self.progress_bar_button.bind("<ButtonRelease-1>", self.on_progress_release)

    def make_sidebar_button(self, parent, text, command, bg="#ffffff", fg="#334155", active_bg="#e8eef6"):
        button = tk.Button(
            parent,
            text=text,
            font=(TK_UI_FONT, 11, "bold"),
            bg=bg,
            fg=fg,
            activebackground=active_bg,
            activeforeground=fg,
            relief=tk.FLAT,
            bd=0,
            padx=0,
            pady=0,
            cursor="hand2",
            highlightthickness=1,
            highlightbackground="#dbe3ee",
        )
        if command is not None:
            button.config(command=command)
        return button

    def add_left_button(self, text, y, command, primary=False):
        button = self.make_sidebar_button(
            self.sidebar,
            text,
            command,
            bg="#2563eb" if primary else "#ffffff",
            fg="#ffffff" if primary else "#334155",
            active_bg="#1d4ed8" if primary else "#e8eef6",
        )
        button.place(x=18, y=y, width=112, height=36)
        return button

    def show_all_phones(self):
        self.stop_video()
        self.current_content_pil = None
        self.current_zoom_content_pil = None
        self.build_grid_base_image()
        self.render_phone_grid()
        self.update_zoom_image_from_current()

    def build_grid_base_image(self):
        image = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), "#f6f8fb")
        for index, phone_id in enumerate(self.phone_ids):
            x, y = self.get_phone_position(index)
            id_row = self.make_id_row_pil(phone_id)
            image.paste(id_row.convert("RGB"), (x, y + PHONE_HEIGHT + 2), id_row)
        self.grid_base_image = image

    def get_phone_position(self, index):
        row = index // 4
        column = index % 4
        return GRID_LEFT + column * GRID_COL_STEP, GRID_TOP + row * GRID_ROW_STEP

    def render_phone_grid(self, content_image=None):
        if self.grid_base_image is None:
            self.build_grid_base_image()

        image = self.grid_base_image.copy()
        for index in range(MAX_PHONES):
            x, y = self.get_phone_position(index)
            card = content_image if content_image is not None else self.make_phone_card_pil(index + 1)
            image.paste(card, (x, y))

        self.grid_photo_image = ImageTk.PhotoImage(image)
        self.phone_canvas.itemconfig(self.grid_image_item, image=self.grid_photo_image)

    def on_phone_canvas_click(self, event):
        index = self.get_phone_index_at(event.x, event.y)
        if index is not None:
            self.open_zoom_window(index)

    def get_phone_index_at(self, x, y):
        for index in range(MAX_PHONES):
            card_x, card_y = self.get_phone_position(index)
            if card_x <= x <= card_x + PHONE_WIDTH and card_y <= y <= card_y + PHONE_HEIGHT:
                return index
        return None

    def clear_phones(self):
        for widget in self.phone_buttons + self.id_buttons:
            widget.destroy()
        self.phone_buttons = []
        self.id_buttons = []
        self.id_row_images = []
        self.phone_current_images = []

    def create_phone(self, number, phone_id, x, y):
        phone_button = tk.Button(
            self,
            text=f"{number:02d}   Cloud Phone",
            image=self.phone_image,
            compound=tk.CENTER,
            font=(TK_LATIN_FONT, 15, "bold"),
            fg="#d9dee7",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            command=lambda idx=number - 1: self.open_zoom_window(idx),
        )
        phone_button.place(x=x, y=y, width=PHONE_WIDTH, height=PHONE_HEIGHT)

        id_row_image = self.make_id_row_image(phone_id)
        id_button = tk.Button(
            self,
            image=id_row_image,
            bg="white",
            activebackground="white",
            relief=tk.FLAT,
            bd=0,
            padx=0,
            pady=0,
            highlightthickness=0,
            takefocus=0,
        )
        id_button.place(x=x, y=y + PHONE_HEIGHT + 2, width=ID_ROW_WIDTH, height=ID_ROW_HEIGHT)

        self.phone_buttons.append(phone_button)
        self.id_buttons.append(id_button)
        self.id_row_images.append(id_row_image)
        self.phone_current_images.append(self.phone_image)

    def upload_video(self):
        if cv2 is None:
            messagebox.showerror("缺少依赖", "需要先安装 opencv-python 才能播放视频。")
            return

        video_path = filedialog.askopenfilename(
            title="选择视频文件",
            filetypes=[
                ("视频文件", "*.mp4 *.mov *.avi *.mkv *.webm"),
                ("所有文件", "*.*"),
            ],
        )
        if not video_path:
            return

        start_seconds = self.get_start_seconds_from_entry()
        if start_seconds is None:
            return

        self.video_path = video_path
        self.video_start_seconds = start_seconds
        self.start_video(video_path, start_seconds)

    def start_video(self, video_path, start_seconds=0):
        self.stop_video()
        capture = cv2.VideoCapture(video_path)
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if not capture.isOpened():
            messagebox.showerror("打开失败", "这个视频文件无法打开。")
            return

        fps = capture.get(cv2.CAP_PROP_FPS)
        frame_count = capture.get(cv2.CAP_PROP_FRAME_COUNT)
        duration = frame_count / fps if fps and fps > 1 and frame_count else 0
        if start_seconds > 0:
            capture.set(cv2.CAP_PROP_POS_MSEC, start_seconds * 1000)

        self.video_capture = capture
        source_fps = fps if fps and fps > 1 else 25
        self.video_source_fps = source_fps
        self.video_fps = min(VIDEO_TARGET_FPS, source_fps)
        self.video_frame_step = max(1.0, self.video_source_fps / max(1, self.video_fps))
        self.video_skip_remainder = 0.0
        self.video_start_seconds = start_seconds
        self.media_kind = "video"
        self.media_duration = int(duration) if duration else 0
        self.is_paused = False
        self.video_frame_count = 0
        self.show_progress_controls(self.media_duration, start_seconds)
        self.play_next_video_frame()

    def play_next_video_frame(self):
        if self.video_capture is None:
            return
        if self.is_paused:
            return

        ok, frame = self.video_capture.read()
        if not ok:
            self.video_capture.set(cv2.CAP_PROP_POS_MSEC, self.video_start_seconds * 1000)
            ok, frame = self.video_capture.read()
            if not ok:
                self.stop_video()
                return
            self.video_skip_remainder = 0.0

        self.current_content_pil = self.make_video_preview_image(frame)
        self.current_zoom_content_pil = self.make_video_zoom_image(frame)
        self.render_phone_grid(self.current_content_pil)
        self.video_frame_count += 1
        if self.video_frame_count % 2 == 0:
            self.update_zoom_image_from_current(throttled=True)

        self.skip_video_frames_for_realtime()

        current_seconds = int(self.video_capture.get(cv2.CAP_PROP_POS_MSEC) / 1000)
        self.update_progress_value(current_seconds, throttled=True)

        delay = max(60, int(1000 / self.video_fps))
        self.video_after_id = self.after(delay, self.play_next_video_frame)

    def skip_video_frames_for_realtime(self):
        skip_float = self.video_frame_step - 1 + self.video_skip_remainder
        skip_count = int(skip_float)
        self.video_skip_remainder = skip_float - skip_count
        for _ in range(skip_count):
            if self.video_capture is None or not self.video_capture.grab():
                break

    def make_video_preview_image(self, frame):
        h, w = frame.shape[:2]
        target_ratio = PHONE_WIDTH / PHONE_HEIGHT
        frame_ratio = w / h if h else target_ratio
        if frame_ratio > target_ratio:
            crop_w = int(h * target_ratio)
            x1 = max(0, (w - crop_w) // 2)
            frame = frame[:, x1:x1 + crop_w]
        else:
            crop_h = int(w / target_ratio) if target_ratio else h
            y1 = max(0, (h - crop_h) // 2)
            frame = frame[y1:y1 + crop_h, :]

        frame = cv2.resize(frame, (PHONE_WIDTH, PHONE_HEIGHT), interpolation=cv2.INTER_AREA)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return Image.fromarray(frame)

    def make_video_zoom_image(self, frame):
        h, w = frame.shape[:2]
        if not h or not w:
            return self.current_content_pil or self.make_phone_card_pil(1)

        max_w, max_h = 1280, 720
        scale = min(max_w / w, max_h / h, 1)
        if scale < 1:
            frame = cv2.resize(frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return Image.fromarray(frame)

    def stop_video(self):
        if self.video_after_id is not None:
            self.after_cancel(self.video_after_id)
            self.video_after_id = None
        if self.video_capture is not None:
            self.video_capture.release()
            self.video_capture = None

    def get_start_seconds_from_entry(self):
        return 0

    def parse_time_to_seconds(self, value):
        text = value.strip()
        if not text:
            return 0
        parts = text.split(":")
        if len(parts) == 1:
            return max(0, int(float(parts[0])))
        if len(parts) == 2:
            minutes, seconds = parts
            return max(0, int(minutes) * 60 + int(float(seconds)))
        if len(parts) == 3:
            hours, minutes, seconds = parts
            return max(0, int(hours) * 3600 + int(minutes) * 60 + int(float(seconds)))
        raise ValueError("invalid time")

    def format_seconds(self, seconds):
        minutes = int(seconds) // 60
        remain = int(seconds) % 60
        return f"{minutes}:{remain:02d}"

    def seek_video(self):
        if not self.video_path:
            messagebox.showinfo("提示", "请先上传一个视频。")
            return

        start_seconds = self.get_start_seconds_from_entry()
        if start_seconds is None:
            return

        self.video_start_seconds = start_seconds
        self.start_video(self.video_path, start_seconds)

    def upload_audio(self):
        if pygame is None:
            messagebox.showerror("缺少依赖", "需要先安装 pygame 才能播放音频。")
            return

        audio_path = filedialog.askopenfilename(
            title="选择音频文件",
            filetypes=[
                ("音频文件", "*.mp3 *.wav *.ogg *.m4a"),
                ("所有文件", "*.*"),
            ],
        )
        if not audio_path:
            return

        self.stop_video()
        self.current_content_pil = self.audio_pil
        self.current_zoom_content_pil = self.audio_pil
        self.render_phone_grid(self.current_content_pil)
        self.update_zoom_image_from_current()

        self.audio_path = audio_path
        self.audio_seek_seconds = 0
        self.media_kind = "audio"
        self.media_duration = self.get_audio_duration(audio_path)
        self.is_paused = False
        self.show_progress_controls(self.media_duration, 0)
        thread = threading.Thread(target=self.play_audio_file, args=(audio_path,), daemon=True)
        thread.start()

    def play_audio_file(self, audio_path):
        try:
            if not self.pygame_ready:
                pygame.mixer.init()
                self.pygame_ready = True
            pygame.mixer.music.stop()
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play(start=self.audio_seek_seconds)
            self.after(0, self.schedule_audio_progress_update)
        except Exception as exc:
            self.after(0, lambda: messagebox.showerror("播放失败", f"这个音频文件无法播放：{exc}"))

    def get_audio_duration(self, audio_path):
        try:
            if not self.pygame_ready:
                pygame.mixer.init()
                self.pygame_ready = True
            sound = pygame.mixer.Sound(audio_path)
            return int(sound.get_length())
        except Exception:
            return 0

    def schedule_audio_progress_update(self):
        if self.progress_after_id is not None:
            self.after_cancel(self.progress_after_id)
            self.progress_after_id = None
        self.update_audio_progress()

    def update_audio_progress(self):
        if self.media_kind != "audio" or pygame is None or not self.pygame_ready:
            return
        if self.is_paused:
            return

        position_ms = pygame.mixer.music.get_pos()
        if position_ms >= 0:
            current_seconds = int(self.audio_seek_seconds + position_ms / 1000)
            self.update_progress_value(current_seconds)
        if pygame.mixer.music.get_busy():
            self.progress_after_id = self.after(500, self.update_audio_progress)

    def batch_upload_materials(self):
        paths = filedialog.askopenfilenames(
            title="批量选择素材",
            filetypes=[
                ("素材文件", "*.mp4 *.mov *.avi *.mkv *.webm *.mp3 *.wav *.ogg *.m4a"),
                ("所有文件", "*.*"),
            ],
        )
        if not paths:
            return

        self.material_paths = list(paths)
        messagebox.showinfo("批量素材", f"已选择 {len(self.material_paths)} 个素材。")

    def start_rename_input(self):
        self.rename_input_visible = True
        self.rename_entry.delete(0, tk.END)
        self.rename_entry.place(x=18, y=294, width=112, height=34)
        self.rename_entry.focus_set()
        self.rename_button.config(text="确认改名", bg="#16a34a", fg="#ffffff", activebackground="#15803d")

    def hide_rename_entry(self):
        self.rename_input_visible = False
        self.rename_entry.place_forget()
        self.rename_button.config(text="批量改名", bg="#ffffff", fg="#334155", activebackground="#e8eef6")

    def batch_rename(self):
        if not self.rename_input_visible:
            self.start_rename_input()
            return

        name = self.rename_entry.get().strip()
        if not name:
            messagebox.showinfo("提示", "请先输入要修改的名称。")
            self.rename_entry.focus_set()
            return

        self.rename_text = name[:20]
        self.phone_ids = [self.rename_text for _ in range(MAX_PHONES)]
        self.refresh_id_rows()
        self.hide_rename_entry()

    def refresh_id_rows(self):
        self.build_grid_base_image()
        self.render_phone_grid(self.current_content_pil)

    def open_zoom_window(self, index):
        self.selected_phone_index = index
        phone_name = self.phone_ids[index]

        if self.zoom_window is not None and self.zoom_window.winfo_exists():
            self.zoom_window.title(phone_name)
            self.zoom_window.lift()
            self.update_zoom_image_from_current()
            return

        self.zoom_window = tk.Toplevel(self)
        self.zoom_window.title(phone_name)
        self.zoom_window.geometry("820x500+220+110")
        self.zoom_window.resizable(True, True)
        self.zoom_window.configure(bg="#e9eff6")
        self.zoom_window.protocol("WM_DELETE_WINDOW", self.close_zoom_window)
        self.zoom_window.bind("<Configure>", lambda _event: self.update_zoom_image_from_current())

        self.zoom_button = tk.Button(
            self.zoom_window,
            relief=tk.FLAT,
            bd=0,
            padx=0,
            pady=0,
            highlightthickness=0,
            takefocus=0,
        )
        self.zoom_button.pack(fill=tk.BOTH, expand=True)
        self.zoom_button.bind("<Button-1>", self.on_zoom_click)
        self.update_zoom_image_from_current()

    def close_zoom_window(self):
        if self.zoom_window is not None:
            self.zoom_window.destroy()
        self.zoom_window = None
        self.zoom_button = None
        self.zoom_image = None

    def on_zoom_click(self, event):
        if self.zoom_window is None or not self.zoom_window.winfo_exists():
            return

        width = max(320, self.zoom_window.winfo_width())
        if event.y <= 48 and width - 52 <= event.x <= width - 12:
            self.close_zoom_window()

    def update_zoom_image_from_current(self, throttled=False):
        if self.selected_phone_index is None:
            return
        if self.zoom_window is None or not self.zoom_window.winfo_exists() or self.zoom_button is None:
            return
        if self.selected_phone_index >= MAX_PHONES:
            return
        if throttled:
            now = time.perf_counter()
            if now - self.last_zoom_update_at < 1 / ZOOM_TARGET_FPS:
                return
            self.last_zoom_update_at = now

        content_image = self.current_zoom_content_pil or self.current_content_pil
        if content_image is None:
            content_image = self.make_phone_card_pil(self.selected_phone_index + 1)

        width = max(320, self.zoom_window.winfo_width())
        height = max(180, self.zoom_window.winfo_height())
        zoom_ui = self.make_zoom_window_image(content_image.convert("RGB"), width, height)
        self.zoom_image = ImageTk.PhotoImage(zoom_ui)
        self.zoom_button.config(image=self.zoom_image, text="")

    def make_zoom_window_image(self, content_image, width, height):
        image = Image.new("RGB", (width, height), "#e9eff6")
        draw = ImageDraw.Draw(image)
        title_font = self.get_zoom_font(16)
        sub_font = self.get_zoom_font(11)
        mini_font = self.get_zoom_font(9)

        top_h = 58
        side_w = 76
        padding = 18
        screen_x = padding
        screen_y = top_h + 16
        screen_w = max(160, width - side_w - screen_x - 18)
        screen_h = max(110, height - screen_y - 44)

        # Top emulator toolbar.
        draw.rectangle((0, 0, width, top_h), fill="#ffffff")
        draw.line((0, top_h - 1, width, top_h - 1), fill="#d5dee9")
        phone_name = self.phone_ids[self.selected_phone_index]
        draw.text((18, 11), "红手指云机", fill="#172033", font=title_font)
        draw.text((18, 34), f"{phone_name}   VM010036084034", fill="#7a8596", font=sub_font)
        draw.rounded_rectangle((210, 18, 286, 40), radius=11, fill="#eafff4")
        draw.ellipse((222, 25, 230, 33), fill="#15b66a")
        draw.text((236, 21), "高速", fill="#15945b", font=mini_font)

        close_x1 = width - 48
        close_y1 = 12
        close_x2 = width - 14
        close_y2 = 44
        self.draw_window_control(draw, width - 116, 12, "min")
        self.draw_window_control(draw, width - 82, 12, "max")
        self.draw_window_control(draw, close_x1, close_y1, "close")

        # Main screen.
        shadow = (screen_x - 5, screen_y - 5, screen_x + screen_w + 5, screen_y + screen_h + 5)
        draw.rounded_rectangle(shadow, radius=14, fill="#d7e0eb")
        draw.rounded_rectangle((screen_x, screen_y, screen_x + screen_w, screen_y + screen_h), radius=10, fill="#111827")
        fitted = ImageOps.contain(content_image, (screen_w, screen_h), Image.LANCZOS)
        paste_x = screen_x + (screen_w - fitted.width) // 2
        paste_y = screen_y + (screen_h - fitted.height) // 2
        image.paste(fitted, (paste_x, paste_y))
        draw.rounded_rectangle((screen_x, screen_y, screen_x + screen_w, screen_y + screen_h), radius=10, outline="#0f172a", width=2)

        # Right toolbar.
        side_x = width - side_w
        panel = (side_x + 10, screen_y, width - 10, max(screen_y + 260, height - 28))
        draw.rounded_rectangle(panel, radius=18, fill="#ffffff")
        item_x = side_x + 38
        start_y = screen_y + 36
        gap = 62
        self.draw_toolbar_button(draw, item_x, start_y, "network", "0ms", active=True)
        self.draw_toolbar_button(draw, item_x, start_y + gap, "rotate", "横屏")
        self.draw_toolbar_button(draw, item_x, start_y + gap * 2, "back", "返回")
        self.draw_toolbar_button(draw, item_x, start_y + gap * 3, "home", "主页")
        self.draw_toolbar_button(draw, item_x, start_y + gap * 4, "recent", "多任务")

        hint = "自适应原比例显示，横屏视频不再强行裁剪"
        draw.text((screen_x, height - 27), hint, fill="#667085", font=sub_font)

        return image

    def get_zoom_font(self, size):
        return self.get_pil_font(size)

    def draw_window_control(self, draw, x, y, kind):
        fill = "#fff1f2" if kind == "close" else "#f4f7fb"
        color = "#e5484d" if kind == "close" else "#647084"
        draw.rounded_rectangle((x, y, x + 32, y + 32), radius=9, fill=fill)
        if kind == "close":
            draw.line((x + 11, y + 11, x + 21, y + 21), fill=color, width=2)
            draw.line((x + 21, y + 11, x + 11, y + 21), fill=color, width=2)
        elif kind == "max":
            draw.rounded_rectangle((x + 10, y + 10, x + 22, y + 22), radius=2, outline=color, width=2)
        else:
            draw.line((x + 10, y + 20, x + 22, y + 20), fill=color, width=2)

    def draw_toolbar_button(self, draw, cx, cy, kind, label, active=False):
        fill = "#eafff4" if active else "#f4f7fb"
        color = "#18b873" if active else "#8792a3"
        draw.ellipse((cx - 18, cy - 18, cx + 18, cy + 18), fill=fill)
        if kind == "network":
            self.draw_wifi_icon(draw, cx, cy - 4, color)
        elif kind == "rotate":
            self.draw_rotate_icon(draw, cx, cy, color)
        elif kind == "back":
            self.draw_back_icon(draw, cx, cy, color)
        elif kind == "home":
            self.draw_home_icon(draw, cx, cy, color)
        elif kind == "recent":
            self.draw_recent_icon(draw, cx, cy, color)

        font = self.get_zoom_font(9)
        text_box = draw.textbbox((0, 0), label, font=font)
        x = cx - (text_box[2] - text_box[0]) // 2
        draw.text((x, cy + 22), label, fill=color, font=font)

    def draw_pin_icon(self, draw, x, y):
        draw.line((x + 7, y, x + 15, y + 8), fill="#a0a8b3", width=2)
        draw.line((x + 4, y + 8, x + 12, y + 16), fill="#a0a8b3", width=2)
        draw.line((x + 10, y + 10, x + 4, y + 18), fill="#a0a8b3", width=2)

    def draw_toolbar_circle(self, draw, cx, cy, fill):
        draw.ellipse((cx - 17, cy - 17, cx + 17, cy + 17), fill=fill)

    def draw_wifi_icon(self, draw, cx, cy, color="#1fcf7a"):
        draw.arc((cx - 13, cy - 11, cx + 13, cy + 15), 220, 320, fill=color, width=3)
        draw.arc((cx - 8, cy - 6, cx + 8, cy + 10), 220, 320, fill=color, width=3)
        draw.ellipse((cx - 3, cy + 5, cx + 3, cy + 11), fill=color)

    def draw_grid_icon(self, draw, cx, cy):
        color = "#8f9aaa"
        for row in range(2):
            for col in range(2):
                x = cx - 10 + col * 13
                y = cy - 10 + row * 13
                draw.rounded_rectangle((x, y, x + 8, y + 8), radius=2, outline=color, width=2)

    def draw_rotate_icon(self, draw, cx, cy, color="#8f9aaa"):
        draw.arc((cx - 11, cy - 11, cx + 11, cy + 11), 35, 300, fill=color, width=3)
        draw.polygon([(cx + 10, cy - 12), (cx + 17, cy - 11), (cx + 13, cy - 5)], fill=color)
        draw.rounded_rectangle((cx - 8, cy - 5, cx + 8, cy + 6), radius=2, outline=color, width=2)

    def draw_back_icon(self, draw, cx, cy, color="#8f9aaa"):
        draw.line((cx + 9, cy - 10, cx - 9, cy, cx + 9, cy + 10), fill=color, width=4)

    def draw_home_icon(self, draw, cx, cy, color="#8f9aaa"):
        draw.polygon([(cx - 12, cy), (cx, cy - 12), (cx + 12, cy), (cx + 8, cy), (cx + 8, cy + 11), (cx - 8, cy + 11), (cx - 8, cy)], fill=color)

    def draw_recent_icon(self, draw, cx, cy, color="#8f9aaa"):
        draw.rounded_rectangle((cx - 10, cy - 10, cx + 10, cy + 10), radius=3, outline=color, width=3)

    def show_progress_controls(self, duration, current_seconds=0):
        self.media_duration = max(1, int(duration))
        self.current_progress_seconds = min(self.media_duration, max(0, int(current_seconds)))
        self.update_progress_text(self.current_progress_seconds)
        self.update_progress_bar_image(self.current_progress_seconds)
        self.play_pause_button.config(text="暂停")
        self.play_pause_button.place(x=18, y=404, width=112, height=34)
        self.progress_button.place(x=18, y=446, width=112, height=22)
        self.progress_bar_button.place(x=18, y=474, width=PROGRESS_WIDTH, height=PROGRESS_HEIGHT)

    def toggle_pause(self):
        if self.media_kind is None:
            return

        if self.is_paused:
            self.resume_media()
        else:
            self.pause_media()

    def pause_media(self):
        self.is_paused = True
        self.play_pause_button.config(text="继续")
        if self.media_kind == "video":
            if self.video_after_id is not None:
                self.after_cancel(self.video_after_id)
                self.video_after_id = None
        elif self.media_kind == "audio" and pygame is not None and self.pygame_ready:
            pygame.mixer.music.pause()

    def resume_media(self):
        self.is_paused = False
        self.play_pause_button.config(text="暂停")
        if self.media_kind == "video":
            self.play_next_video_frame()
        elif self.media_kind == "audio" and pygame is not None and self.pygame_ready:
            pygame.mixer.music.unpause()
            self.schedule_audio_progress_update()

    def on_progress_press(self, event):
        self.is_dragging_progress = True
        self.set_progress_from_x(event.x)

    def on_progress_drag(self, event):
        self.set_progress_from_x(event.x)

    def on_progress_release(self, _event):
        self.is_dragging_progress = False
        self.seek_media_to(self.current_progress_seconds)

    def set_progress_from_x(self, x):
        ratio = min(1, max(0, x / PROGRESS_WIDTH))
        seconds = int(ratio * max(1, self.media_duration))
        self.current_progress_seconds = seconds
        self.update_progress_text(seconds)
        self.update_progress_bar_image(seconds)

    def seek_media_to(self, seconds):
        self.is_paused = False
        self.play_pause_button.config(text="暂停")
        if self.media_kind == "video" and self.video_path:
            self.video_start_seconds = seconds
            self.start_video(self.video_path, seconds)
        elif self.media_kind == "audio" and self.audio_path:
            self.audio_seek_seconds = seconds
            thread = threading.Thread(target=self.play_audio_file, args=(self.audio_path,), daemon=True)
            thread.start()

    def update_progress_value(self, seconds, throttled=False):
        if self.is_dragging_progress:
            return
        if throttled:
            now = time.perf_counter()
            if now - self.last_progress_update_at < 0.25:
                return
            self.last_progress_update_at = now
        if self.media_duration:
            seconds = min(seconds, self.media_duration)
        self.current_progress_seconds = max(0, int(seconds))
        self.update_progress_text(self.current_progress_seconds)
        self.update_progress_bar_image(self.current_progress_seconds)

    def update_progress_text(self, seconds):
        total = self.media_duration if self.media_duration else 0
        self.progress_button.config(text=f"进度 {self.format_seconds(seconds)} / {self.format_seconds(total)}")

    def update_progress_bar_image(self, seconds):
        total = max(1, self.media_duration)
        ratio = min(1, max(0, seconds / total))
        fill_width = int(PROGRESS_WIDTH * ratio)
        knob_x = max(6, min(PROGRESS_WIDTH - 6, fill_width))

        image = Image.new("RGB", (PROGRESS_WIDTH, PROGRESS_HEIGHT), "#eef3f8")
        draw = ImageDraw.Draw(image)
        track_y = PROGRESS_HEIGHT // 2
        draw.rounded_rectangle((0, track_y - 4, PROGRESS_WIDTH, track_y + 4), radius=4, fill="#e5e7eb")
        draw.rounded_rectangle((0, track_y - 4, fill_width, track_y + 4), radius=4, fill="#4a576a")
        draw.ellipse((knob_x - 6, track_y - 6, knob_x + 6, track_y + 6), fill="#4a576a")

        self.progress_bar_image = ImageTk.PhotoImage(image)
        self.progress_bar_button.config(image=self.progress_bar_image)

    def add_phone(self):
        messagebox.showinfo("提示", "当前右侧已经直接铺满 16 台云手机。")

    def select_phone(self, phone_id):
        messagebox.showinfo("云手机", f"你点击了云手机：{phone_id}")

    def show_todo(self, action):
        messagebox.showinfo("提示", f"{action}功能下一步可以继续开发。")

    def destroy(self):
        self.stop_video()
        if self.progress_after_id is not None:
            self.after_cancel(self.progress_after_id)
            self.progress_after_id = None
        if pygame is not None and self.pygame_ready:
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        super().destroy()


def enable_windows_runtime_settings():
    if sys.platform != "win32":
        return

    try:
        import ctypes

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("CloudPhoneManager")
    except Exception:
        pass


if __name__ == "__main__":
    enable_windows_runtime_settings()
    app = CloudPhoneManager()
    app.mainloop()
