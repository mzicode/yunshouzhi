import random
import sys
import threading
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
PROGRESS_WIDTH = 122
PROGRESS_HEIGHT = 24
BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


class CloudPhoneManager(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("云手机管理 - 全按钮显示版")
        self.geometry("1160x650")
        self.resizable(False, False)
        self.configure(bg="white")

        start_id = random.randint(73000000, 86000000)
        self.phone_ids = [str(start_id + index) for index in range(MAX_PHONES)]
        self.phone_buttons = []
        self.id_buttons = []
        self.id_row_images = []
        self.phone_image = self.make_phone_image()
        self.audio_image = self.make_status_image("音频播放中")
        self.device_icon_source = self.load_pil_icon("device.png")
        self.upload_icon_source = self.load_pil_icon("upload.png")
        self.video_capture = None
        self.video_after_id = None
        self.video_frame_image = None
        self.video_fps = 25
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

        self.build_ui()
        self.show_all_phones()

    def make_phone_image(self):
        image = tk.PhotoImage(width=PHONE_WIDTH, height=PHONE_HEIGHT)
        image.put(CARD_COLOR, to=(0, 0, PHONE_WIDTH, PHONE_HEIGHT))
        image.put("#566477", to=(18, 15, 96, 25))
        image.put("#687689", to=(148, 78, 210, 87))
        image.put("#627083", to=(22, 80, 40, 100))
        return image

    def make_status_image(self, text):
        image = Image.new("RGB", (PHONE_WIDTH, PHONE_HEIGHT), CARD_COLOR)
        draw = ImageDraw.Draw(image)
        font = self.get_status_font()
        text_box = draw.textbbox((0, 0), text, font=font)
        x = (PHONE_WIDTH - (text_box[2] - text_box[0])) // 2
        y = (PHONE_HEIGHT - (text_box[3] - text_box[1])) // 2 - text_box[1]
        draw.text((x, y), text, fill="#d9dee7", font=font)
        return ImageTk.PhotoImage(image)

    def load_pil_icon(self, file_name):
        icon_path = BASE_DIR / "assets" / file_name
        if icon_path.exists():
            image = Image.open(icon_path).convert("RGBA")
            image = image.resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS)
            return image

        image = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (255, 255, 255, 0))
        return image

    def make_id_row_image(self, phone_id):
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

        return ImageTk.PhotoImage(image)

    def get_id_font(self):
        candidates = [
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/Library/Fonts/Arial.ttf",
            "arial.ttf",
        ]
        for path in candidates:
            try:
                return ImageFont.truetype(path, 11)
            except OSError:
                continue
        return ImageFont.load_default()

    def get_status_font(self):
        candidates = [
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/Library/Fonts/Arial.ttf",
            "arial.ttf",
        ]
        for path in candidates:
            try:
                return ImageFont.truetype(path, 16)
            except OSError:
                continue
        return ImageFont.load_default()

    def build_ui(self):
        self.add_left_button("上传视频", 36, self.upload_video)
        self.add_left_button("上传语音", 94, self.upload_audio)
        self.add_left_button("批量素材", 152, self.batch_upload_materials)
        self.name_input_button = self.add_left_button("名称: 请输入", 226, self.start_rename_input)
        self.name_input_button.place_forget()
        self.add_left_button("批量改名", 226, self.batch_rename)
        self.bind_all("<Key>", self.on_rename_key)
        self.build_progress_controls()

    def build_progress_controls(self):
        self.play_pause_button = tk.Button(
            self,
            text="暂停",
            font=("Arial", 11),
            command=self.toggle_pause,
        )
        self.progress_button = tk.Button(
            self,
            text="进度 0:00 / 0:00",
            font=("Arial", 11),
        )
        self.progress_bar_button = tk.Button(
            self,
            relief=tk.FLAT,
            bd=0,
            padx=0,
            pady=0,
            highlightthickness=0,
            takefocus=0,
        )
        self.progress_bar_button.bind("<ButtonPress-1>", self.on_progress_press)
        self.progress_bar_button.bind("<B1-Motion>", self.on_progress_drag)
        self.progress_bar_button.bind("<ButtonRelease-1>", self.on_progress_release)

    def add_left_button(self, text, y, command):
        button = tk.Button(
            self,
            text=text,
            font=("Arial", 13),
        )
        if command is not None:
            button.config(command=command)
        button.place(x=22, y=y, width=106, height=28)
        return button

    def show_all_phones(self):
        self.stop_video()
        self.clear_phones()

        for index, phone_id in enumerate(self.phone_ids):
            row = index // 4
            column = index % 4
            x = 165 + column * 245
            y = 24 + row * 148
            self.create_phone(index + 1, phone_id, x, y)

    def clear_phones(self):
        for widget in self.phone_buttons + self.id_buttons:
            widget.destroy()
        self.phone_buttons = []
        self.id_buttons = []
        self.id_row_images = []

    def create_phone(self, number, phone_id, x, y):
        # 使用 Button 作为云手机卡片，因为当前 Mac 环境里按钮控件已经确认可见。
        phone_button = tk.Button(
            self,
            text=f"{number:02d}   Cloud Phone",
            image=self.phone_image,
            compound=tk.CENTER,
            font=("Arial", 15, "bold"),
            fg="#d9dee7",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            command=lambda value=phone_id: self.select_phone(value),
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
        if not capture.isOpened():
            messagebox.showerror("打开失败", "这个视频文件无法打开。")
            return

        fps = capture.get(cv2.CAP_PROP_FPS)
        frame_count = capture.get(cv2.CAP_PROP_FRAME_COUNT)
        duration = frame_count / fps if fps and fps > 1 and frame_count else 0
        if start_seconds > 0:
            capture.set(cv2.CAP_PROP_POS_MSEC, start_seconds * 1000)

        self.video_capture = capture
        self.video_fps = fps if fps and fps > 1 else 25
        self.video_start_seconds = start_seconds
        self.media_kind = "video"
        self.media_duration = int(duration) if duration else 0
        self.is_paused = False
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

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(frame)
        image = ImageOps.fit(image, (PHONE_WIDTH, PHONE_HEIGHT), Image.LANCZOS)
        self.video_frame_image = ImageTk.PhotoImage(image)

        for button in self.phone_buttons:
            button.config(image=self.video_frame_image, text="")

        current_seconds = int(self.video_capture.get(cv2.CAP_PROP_POS_MSEC) / 1000)
        self.update_progress_value(current_seconds)

        delay = max(15, int(1000 / self.video_fps))
        self.video_after_id = self.after(delay, self.play_next_video_frame)

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
        for button in self.phone_buttons:
            button.config(image=self.audio_image, text="")

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
        self.rename_text = ""
        self.rename_editing = True
        self.update_name_input_button()
        self.focus_force()

    def paste_rename_text(self):
        try:
            value = self.clipboard_get().strip()
        except tk.TclError:
            value = ""
        if not value:
            messagebox.showinfo("提示", "剪贴板里没有可用名称。")
            return
        self.rename_text = value[:20]
        self.rename_editing = False
        self.update_name_input_button()

    def on_rename_key(self, event):
        if not self.rename_editing:
            return

        if event.keysym in ("Return", "KP_Enter"):
            self.rename_editing = False
            self.update_name_input_button()
            return "break"
        if event.keysym == "Escape":
            self.rename_editing = False
            self.update_name_input_button()
            return "break"
        if event.keysym == "BackSpace":
            self.rename_text = self.rename_text[:-1]
            self.update_name_input_button()
            return "break"

        if event.char and event.char.isprintable():
            self.rename_text = (self.rename_text + event.char)[:20]
            self.update_name_input_button()
            return "break"

        return None

    def update_name_input_button(self):
        value = self.rename_text or "请输入"
        if len(value) > 6:
            value = value[:6] + "..."
        prefix = "输入中:" if self.rename_editing else "名称:"
        self.name_input_button.config(text=f"{prefix} {value}")

    def batch_rename(self):
        if not self.rename_input_visible:
            self.rename_input_visible = True
            self.name_input_button.place(x=22, y=284, width=106, height=28)
            self.start_rename_input()
            return

        name = self.rename_text.strip()
        if not name:
            messagebox.showinfo("提示", "请先输入要修改的名称。")
            self.start_rename_input()
            return

        self.rename_text = name
        self.rename_editing = False
        self.update_name_input_button()
        self.phone_ids = [name for _ in range(MAX_PHONES)]
        self.refresh_id_rows()
        self.rename_input_visible = False
        self.name_input_button.place_forget()

    def refresh_id_rows(self):
        self.id_row_images = []
        for index, button in enumerate(self.id_buttons):
            image = self.make_id_row_image(self.phone_ids[index])
            button.config(image=image)
            self.id_row_images.append(image)

    def show_progress_controls(self, duration, current_seconds=0):
        self.media_duration = max(1, int(duration))
        self.current_progress_seconds = min(self.media_duration, max(0, int(current_seconds)))
        self.update_progress_text(self.current_progress_seconds)
        self.update_progress_bar_image(self.current_progress_seconds)
        self.play_pause_button.config(text="暂停")
        self.play_pause_button.place(x=22, y=438, width=106, height=28)
        self.progress_button.place(x=22, y=474, width=106, height=28)
        self.progress_bar_button.place(x=14, y=512, width=PROGRESS_WIDTH, height=PROGRESS_HEIGHT)

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

    def update_progress_value(self, seconds):
        if self.is_dragging_progress:
            return
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

        image = Image.new("RGB", (PROGRESS_WIDTH, PROGRESS_HEIGHT), "white")
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


if __name__ == "__main__":
    app = CloudPhoneManager()
    app.mainloop()
