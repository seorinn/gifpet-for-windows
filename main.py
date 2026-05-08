#!/usr/bin/env python3
"""
GifPet - 타이핑할수록 신나게 춤추는 햄스터 오버레이
트레이 아이콘 우클릭 → 보이기/숨기기, 속도, 크기, GIF, 종료
"""

import tkinter as tk
import threading
import time
import math
import json
import ctypes
import ctypes.wintypes
import os
import sys
from pathlib import Path

from PIL import Image, ImageTk, ImageDraw
import pystray
from pynput import keyboard as kb

# ── 고정 설정 ─────────────────────────────────────────────────────────────────
CHROMA     = '#fe01fe'
CHROMA_RGB = (254, 1, 254)

SIDE_OFFSET   = 10
BOTTOM_OFFSET = 4
IDLE_DELAY    = 1000          # ms (숨김 상태 폴링 주기)
DECAY_HALF_LIFE = 1.2         # 초: 키 입력 후 속도가 절반이 되는 시간
SPEED_RANGE   = 150           # ms: 기본속도 ~ 최고속도 범위 (고정)

# 속도 옵션 (label, base_delay ms)
SPEED_OPTIONS = [
    ('매우 느리게', 380),
    ('느리게',      280),
    ('보통',        200),
    ('빠르게',      130),
    ('매우 빠르게',  70),
]
# 크기 옵션 (px)
SIZE_OPTIONS = [30, 55, 80, 120, 170]

DEFAULT_BASE_DELAY = 200
DEFAULT_SIZE       = 80


# ── 경로 헬퍼 ─────────────────────────────────────────────────────────────────
def get_app_dir() -> Path:
    path = Path(os.environ.get('APPDATA', Path.home())) / 'GifPet'
    path.mkdir(exist_ok=True)
    return path


def get_bundled_resource(filename: str) -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS) / filename
    return Path(__file__).parent / filename


def get_workarea() -> tuple:
    rc = ctypes.wintypes.RECT()
    ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(rc), 0)
    return rc.left, rc.top, rc.right, rc.bottom


# ── 설정 저장/불러오기 ────────────────────────────────────────────────────────
def load_config() -> dict:
    p = get_app_dir() / 'config.json'
    if p.exists():
        try:
            with open(p, encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


_config_lock = threading.Lock()


def save_config(cfg: dict):
    p = get_app_dir() / 'config.json'
    try:
        tmp = p.with_suffix('.tmp')
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(cfg, f)
        os.replace(tmp, p)   # atomic write
    except Exception:
        pass


def update_config(**kwargs):
    """스레드 안전하게 config 일부 키를 업데이트"""
    with _config_lock:
        cfg = load_config()
        cfg.update(kwargs)
        save_config(cfg)



def create_tray_icon_image() -> Image.Image:
    """🐹 이모지를 Segoe UI Emoji 폰트로 렌더링. 실패 시 손그림 폴백."""
    size = 64
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    try:
        from PIL import ImageFont
        font = ImageFont.truetype(r'C:\Windows\Fonts\seguiemj.ttf', 52)
        bbox = d.textbbox((0, 0), '🐹', font=font, embedded_color=True)
        x = (size - (bbox[2] - bbox[0])) // 2 - bbox[0]
        y = (size - (bbox[3] - bbox[1])) // 2 - bbox[1]
        d.text((x, y), '🐹', font=font, embedded_color=True)
    except Exception:
        # 폴백: 손그림 햄스터 얼굴
        d.ellipse([ 2,  2, 62, 62], fill=(180, 130,  80, 255))
        d.ellipse([ 8, 10, 56, 55], fill=(240, 210, 170, 255))
        d.ellipse([ 2,  0, 18, 16], fill=(180, 130,  80, 255))
        d.ellipse([46,  0, 62, 16], fill=(180, 130,  80, 255))
        d.ellipse([16, 22, 25, 31], fill=( 20,  10,   5, 255))
        d.ellipse([39, 22, 48, 31], fill=( 20,  10,   5, 255))
        d.ellipse([28, 36, 36, 43], fill=(240, 150, 150, 255))
    return img


# ── GIF 프레임 로더 ───────────────────────────────────────────────────────────
def _rgba_to_chroma(img: Image.Image, size: tuple) -> ImageTk.PhotoImage:
    """
    RGBA → 크로마키 배경 합성 PhotoImage.
    알파 임계처리(128)로 반투명 픽셀을 완전 투명으로 처리 → 핑크 테두리 방지.
    """
    if img.size != size:
        img = img.resize(size, Image.LANCZOS)
    r, g, b, a = img.split()
    # 반투명 픽셀 → 완전 투명(0) or 불투명(255) 으로 이분화
    a_clean = a.point(lambda v: 0 if v < 128 else 255)
    bg = Image.new('RGB', size, CHROMA_RGB)
    bg.paste(Image.merge('RGB', (r, g, b)), mask=a_clean)
    return ImageTk.PhotoImage(bg)



def load_gif_frames(gif_path: Path, size: tuple) -> list:
    frames = []
    with Image.open(str(gif_path)) as gif:
        n = getattr(gif, 'n_frames', 1)
        for i in range(n):
            gif.seek(i)
            frames.append(_rgba_to_chroma(gif.copy().convert('RGBA'), size))
    return frames if frames else []


# ── 메인 앱 ──────────────────────────────────────────────────────────────────
class GifPet:
    def __init__(self):
        cfg = load_config()
        self._base_delay   = cfg.get('base_delay', DEFAULT_BASE_DELAY)
        self._display_size = cfg.get('size', DEFAULT_SIZE)

        self._last_key_time: float = 0.0
        self.running       = True
        self.visible       = True
        self.current_frame = 0
        self.frames        = []

        self._drag_x = 0
        self._drag_y = 0

        self._resolve_gif_path()
        self._init_window()
        self._load_frames()
        self._init_tray()
        self._init_keyboard()

    # ── GIF 경로 확인 ─────────────────────────────────────────────────────────
    def _resolve_gif_path(self):
        user_gif = get_app_dir() / 'pet.gif'
        if user_gif.exists():
            self._custom_gif = user_gif
        else:
            bundled = get_bundled_resource('pet.gif')
            self._custom_gif = bundled if bundled.exists() else None

    # ── 프레임 로드 ───────────────────────────────────────────────────────────
    def _load_frames(self):
        size = (self._display_size, self._display_size)
        if self._custom_gif:
            self.frames = load_gif_frames(self._custom_gif, size)
        else:
            raise RuntimeError('pet.gif를 찾을 수 없습니다. GIF 폴더에 pet.gif를 추가하세요.')
        if not self.frames:
            raise RuntimeError('프레임 로드 실패')

    # ── 윈도우 초기화 ─────────────────────────────────────────────────────────
    def _init_window(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.wm_attributes('-topmost', True)
        self.root.wm_attributes('-transparentcolor', CHROMA)
        self.root.configure(bg=CHROMA)
        self.root.resizable(False, False)

        self._reposition()

        self.canvas = tk.Canvas(
            self.root, width=self._display_size, height=self._display_size,
            bg=CHROMA, highlightthickness=0, bd=0,
        )
        self.canvas.pack()
        self._canvas_img_id = None

        # 드래그로 위치 이동 + 클릭 시 하트
        self.canvas.bind('<ButtonPress-1>',   self._drag_start)
        self.canvas.bind('<B1-Motion>',       self._drag_move)
        self.canvas.bind('<ButtonRelease-1>', self._on_click_release)

        self._heart_pts_cache: dict = {}  # size → 정규화된 하트 좌표 캐시

        self.root.after(50, self._animate)

    def _reposition(self):
        """저장된 위치가 있으면 복원, 없으면 기본값(우측 하단)"""
        s   = self._display_size
        cfg = load_config()
        if 'x' in cfg and 'y' in cfg:
            x, y = cfg['x'], cfg['y']
        else:
            _, _, wa_right, wa_bottom = get_workarea()
            x = wa_right  - s - SIDE_OFFSET
            y = wa_bottom - s - BOTTOM_OFFSET
        self.root.geometry(f'{s}x{s}+{x}+{y}')

    def _drag_start(self, event):
        self._drag_x = event.x_root - self.root.winfo_x()
        self._drag_y = event.y_root - self.root.winfo_y()

    def _drag_move(self, event):
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self.root.geometry(f'+{x}+{y}')

    def _drag_end(self, event):
        update_config(x=self.root.winfo_x(), y=self.root.winfo_y())

    def _on_click_release(self, event):
        dx = abs(event.x_root - (self.root.winfo_x() + self._drag_x))
        dy = abs(event.y_root - (self.root.winfo_y() + self._drag_y))
        if dx < 5 and dy < 5:   # 드래그 아닌 클릭
            self._spawn_heart(event.x, event.y)
        else:
            self._drag_end(event)

    def _heart_polygon(self, cx: int, cy: int, size: int) -> list:
        """파라메트릭 하트 곡선 좌표 반환 (캔버스 절대 좌표). 크기별 캐시."""
        if size not in self._heart_pts_cache:
            steps = 80
            pad   = size * 0.05
            raw   = []
            for i in range(steps):
                a = 2 * math.pi * i / steps
                raw.append((
                    16 * math.sin(a) ** 3,
                    -(13 * math.cos(a) - 5 * math.cos(2*a)
                      - 2 * math.cos(3*a) - math.cos(4*a)),
                ))
            xs = [p[0] for p in raw]; ys = [p[1] for p in raw]
            mn_x, mx_x = min(xs), max(xs)
            mn_y, mx_y = min(ys), max(ys)
            sc = min((size - pad*2) / (mx_x - mn_x),
                     (size - pad*2) / (mx_y - mn_y))
            ox = pad + ((size - pad*2) - (mx_x - mn_x) * sc) / 2
            oy = pad + ((size - pad*2) - (mx_y - mn_y) * sc) / 2
            # 원점 기준 정규화 좌표 저장
            self._heart_pts_cache[size] = [
                (ox + (px - mn_x) * sc - size/2,
                 oy + (py - mn_y) * sc - size/2)
                for px, py in raw
            ]
        return [(cx + dx, cy + dy)
                for dx, dy in self._heart_pts_cache[size]]

    def _spawn_heart(self, cx: int, cy: int):
        """클릭 위치에 하트 폴리곤을 띄우고 위로 떠오르며 페이드아웃"""
        FRAMES = 18
        size   = max(10, self._display_size // 6)
        pos    = [cx, cy - size // 2]

        pts  = self._heart_polygon(pos[0], pos[1], size)
        item = self.canvas.create_polygon(pts, fill='#dc1432', outline='', smooth=False)

        step = 0

        def _tick():
            nonlocal step
            if step >= FRAMES:
                self.canvas.delete(item)
                return
            t      = 1.0 - step / FRAMES
            r_val  = int(220 * t + CHROMA_RGB[0] * (1 - t))
            g_val  = int(20  * t + CHROMA_RGB[1] * (1 - t))
            b_val  = int(50  * t + CHROMA_RGB[2] * (1 - t))
            color  = f'#{r_val:02x}{g_val:02x}{b_val:02x}'
            pos[1] -= 2
            new_pts = self._heart_polygon(pos[0], pos[1], size)
            self.canvas.coords(item, [c for pt in new_pts for c in pt])
            self.canvas.itemconfigure(item, fill=color)
            step += 1
            self.root.after(30, _tick)

        _tick()

    # ── 애니메이션 루프 ───────────────────────────────────────────────────────
    def _animate(self):
        if not self.running:
            return
        if self.visible and self.frames:
            frame = self.frames[self.current_frame]
            if self._canvas_img_id is None:
                self._canvas_img_id = self.canvas.create_image(0, 0, anchor='nw', image=frame)
            else:
                self.canvas.itemconfigure(self._canvas_img_id, image=frame)
            self.current_frame = (self.current_frame + 1) % len(self.frames)
            self.root.after(self._frame_delay(), self._animate)
        else:
            self.root.after(IDLE_DELAY, self._animate)

    def _frame_delay(self) -> int:
        """기본 속도에서 타이핑에 반응해 빨라지고, 멈추면 지수 감쇠로 복귀"""
        elapsed = time.time() - self._last_key_time
        speed   = math.exp(-elapsed * math.log(2) / DECAY_HALF_LIFE)
        min_d   = max(20, self._base_delay - SPEED_RANGE)
        return int(self._base_delay - speed * (self._base_delay - min_d))

    # ── 키보드 리스너 ─────────────────────────────────────────────────────────
    def _on_key_press(self, key):
        self._last_key_time = time.time()

    def _init_keyboard(self):
        try:
            self.listener = kb.Listener(on_press=self._on_key_press)
            self.listener.daemon = True
            self.listener.start()
        except Exception:
            pass

    # ── 시스템 트레이 ─────────────────────────────────────────────────────────
    def _init_tray(self):
        menu = pystray.Menu(
            pystray.MenuItem('보이기 / 숨기기', self._toggle, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('기본 속도', self._speed_menu()),
            pystray.MenuItem('크기',     self._size_menu()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('GIF 폴더 열기', self._open_gif_folder),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('종료', self._quit),
        )
        self.tray = pystray.Icon(
            'GifPet', create_tray_icon_image(), 'GifPet', menu
        )
        threading.Thread(target=self.tray.run, daemon=True).start()

    def _speed_menu(self):
        items = []
        for label, delay in SPEED_OPTIONS:
            d = delay
            items.append(pystray.MenuItem(
                label,
                lambda *args, d=d: self._set_speed(d),
                checked=lambda *args, d=d: self._base_delay == d,
                radio=True,
            ))
        return pystray.Menu(*items)

    def _size_menu(self):
        items = []
        for s in SIZE_OPTIONS:
            items.append(pystray.MenuItem(
                f'{s}px',
                lambda *args, s=s: self._set_size(s),
                checked=lambda *args, s=s: self._display_size == s,
                radio=True,
            ))
        return pystray.Menu(*items)

    def _set_speed(self, base_delay: int):
        # pystray 스레드 → 메인 스레드에서 상태 변경
        def _apply():
            self._base_delay = base_delay
        self.root.after(0, _apply)
        update_config(base_delay=base_delay)

    def _set_size(self, size: int):
        update_config(size=size)
        self.root.after(0, lambda: self._apply_size(size))

    def _apply_size(self, size: int):
        """크기 변경 (메인 스레드에서 실행)"""
        self._display_size = size
        self._load_frames()
        self.current_frame = 0        # 범위 초과 방지
        self.canvas.config(width=size, height=size)
        self._canvas_img_id = None
        self._reposition()

    def _toggle(self, *_):
        self.visible = not self.visible
        if self.visible:
            self.root.after(0, self.root.deiconify)   # _animate는 IDLE 루프에서 자동 재개
        else:
            self.root.after(0, self.root.withdraw)

    def _open_gif_folder(self, *_):
        import subprocess
        subprocess.Popen(['explorer', str(get_app_dir())])

    def _quit(self, *_):
        self.running = False
        def _do_quit():
            self.tray.stop()
            self.root.destroy()
        self.root.after(0, _do_quit)

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    app = GifPet()
    app.run()
