#!/usr/bin/env python3
"""
HamsterDancer - 타이핑할수록 신나게 춤추는 햄스터 오버레이
트레이 아이콘 우클릭 → 보이기/숨기기, 종료
"""

import tkinter as tk
import threading
import time
import math
import ctypes
import ctypes.wintypes
import os
import sys
from pathlib import Path
from collections import deque

from PIL import Image, ImageTk, ImageDraw
import pystray
from pynput import keyboard as kb

# ── 설정 ──────────────────────────────────────────────────────────────────────
CHROMA     = '#fe01fe'           # 투명으로 처리할 크로마키 색상
CHROMA_RGB = (254, 1, 254)

SIDE_OFFSET = 10                 # 우측 끝에서의 간격 (px)
BOTTOM_OFFSET = 4                # 작업 영역 하단에서의 추가 간격 (px)

MIN_DELAY        = 40            # ms (최고속, ~25fps)
MAX_DELAY        = 200           # ms (기본 속도, ~5fps)
IDLE_DELAY       = 1000          # ms (숨김 상태 폴링 주기)
DECAY_HALF_LIFE  = 1.2           # 초: 키 입력 후 속도가 절반이 되는 시간


# ── 경로 헬퍼 ─────────────────────────────────────────────────────────────────
def get_app_dir() -> Path:
    """%APPDATA%\\HamsterDancer 디렉토리 반환 (없으면 생성)"""
    path = Path(os.environ.get('APPDATA', Path.home())) / 'HamsterDancer'
    path.mkdir(exist_ok=True)
    return path


def get_bundled_resource(filename: str) -> Path:
    """PyInstaller 번들 내 리소스 경로, 개발 중엔 스크립트 옆"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS) / filename
    return Path(__file__).parent / filename


def get_workarea() -> tuple:
    """
    Windows 작업 영역(작업표시줄 제외) 반환: (left, top, right, bottom).
    SPI_GETWORKAREA(0x30) 사용 → 멀티모니터/DPI 스케일링 대응.
    """
    rc = ctypes.wintypes.RECT()
    ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(rc), 0)
    return rc.left, rc.top, rc.right, rc.bottom


# ── 픽셀아트 햄스터 프레임 생성 ───────────────────────────────────────────────
def draw_hamster_frame(frame_idx: int) -> Image.Image:
    """
    8프레임 애니메이션 중 하나를 그려 RGBA Image 반환.
    0~3프레임: 팔 위로 흔들기 / 4~7프레임: 팔 아래로 스윙
    """
    W, H = 80, 80
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    C = {
        'body':  (180, 130,  80, 255),
        'cream': (240, 210, 170, 255),
        'dark':  ( 90,  55,  20, 255),
        'eye':   ( 20,  10,   5, 255),
        'pink':  (240, 150, 150, 255),
        'blush': (255, 180, 180, 130),
        'shine': (255, 255, 255, 200),
    }

    bounces = [0, -2, -3, -2, 0, 2, 3, 2]
    b = bounces[frame_idx % 8]   # 상하 바운스 오프셋
    arm_up = frame_idx < 4       # 팔 방향

    # 몸통
    d.ellipse([20, 42+b, 60, 68+b], fill=C['body'], outline=C['dark'], width=2)
    d.ellipse([25, 46+b, 55, 66+b], fill=C['cream'])
    # 머리
    d.ellipse([16, 14+b, 64, 52+b], fill=C['body'], outline=C['dark'], width=2)
    d.ellipse([22, 20+b, 58, 47+b], fill=C['cream'])
    # 왼쪽 귀
    d.ellipse([10,  4+b, 27, 22+b], fill=C['body'], outline=C['dark'], width=1)
    d.ellipse([13,  7+b, 24, 19+b], fill=C['pink'])
    # 오른쪽 귀
    d.ellipse([53,  4+b, 70, 22+b], fill=C['body'], outline=C['dark'], width=1)
    d.ellipse([56,  7+b, 67, 19+b], fill=C['pink'])
    # 눈
    d.ellipse([26, 26+b, 35, 35+b], fill=C['eye'])
    d.ellipse([27, 27+b, 30, 30+b], fill=C['shine'])
    d.ellipse([45, 26+b, 54, 35+b], fill=C['eye'])
    d.ellipse([46, 27+b, 49, 30+b], fill=C['shine'])
    # 코
    d.ellipse([36, 37+b, 44, 43+b], fill=C['pink'])
    # 볼터치
    d.ellipse([20, 35+b, 30, 43+b], fill=C['blush'])
    d.ellipse([50, 35+b, 60, 43+b], fill=C['blush'])
    # 입 (미소)
    d.arc([33, 42+b, 47, 50+b], 10, 170, fill=C['dark'], width=1)

    # 팔
    if arm_up:
        wave = [0, 4, 0, -4][frame_idx % 4]
        d.line([20, 44+b,  4, 30+b+wave], fill=C['body'], width=5)
        d.ellipse([ 1, 27+b+wave,  7, 33+b+wave], fill=C['body'], outline=C['dark'])
        d.line([60, 44+b, 76, 30+b-wave], fill=C['body'], width=5)
        d.ellipse([73, 27+b-wave, 79, 33+b-wave], fill=C['body'], outline=C['dark'])
    else:
        swing = [0, 5, 0, -5][(frame_idx - 4) % 4]
        d.line([20, 48+b,  4, 62+b+swing], fill=C['body'], width=5)
        d.ellipse([ 1, 59+b+swing,  7, 65+b+swing], fill=C['body'], outline=C['dark'])
        d.line([60, 48+b, 76, 62+b-swing], fill=C['body'], width=5)
        d.ellipse([73, 59+b-swing, 79, 65+b-swing], fill=C['body'], outline=C['dark'])

    # 발
    d.ellipse([22, 66+b, 35, 75+b], fill=C['body'], outline=C['dark'], width=1)
    d.ellipse([45, 66+b, 58, 75+b], fill=C['body'], outline=C['dark'], width=1)

    return img


def create_default_hamster_gif(path: Path) -> None:
    """기본 픽셀아트 햄스터 GIF를 생성하여 저장"""
    frames = [draw_hamster_frame(i) for i in range(8)]
    frames[0].save(
        str(path),
        save_all=True,
        append_images=frames[1:],
        loop=0,
        duration=[120] * 8,
        format='GIF',
    )


def create_tray_icon_image() -> Image.Image:
    """시스템 트레이용 작은 햄스터 얼굴 아이콘"""
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([ 2,  2, 62, 62], fill=(180, 130,  80, 255))
    d.ellipse([ 8, 10, 56, 55], fill=(240, 210, 170, 255))
    d.ellipse([ 2,  0, 18, 16], fill=(180, 130,  80, 255))
    d.ellipse([46,  0, 62, 16], fill=(180, 130,  80, 255))
    d.ellipse([16, 22, 25, 31], fill=( 20,  10,   5, 255))
    d.ellipse([39, 22, 48, 31], fill=( 20,  10,   5, 255))
    d.ellipse([28, 36, 36, 43], fill=(240, 150, 150, 255))
    return img


# ── GIF 프레임 로더 ───────────────────────────────────────────────────────────
def _rgba_to_chroma(img: Image.Image) -> ImageTk.PhotoImage:
    """RGBA 이미지를 크로마키 배경에 합성해 PhotoImage 반환"""
    bg = Image.new('RGB', img.size, CHROMA_RGB)
    bg.paste(img, mask=img.split()[3])
    return ImageTk.PhotoImage(bg)


def load_builtin_frames() -> list:
    """
    기본 햄스터 프레임을 GIF 라운드트립 없이 직접 생성.
    GIF 포맷 변환 손실·disposal 오류 원천 차단.
    """
    return [_rgba_to_chroma(draw_hamster_frame(i)) for i in range(8)]


def load_gif_frames(gif_path: Path) -> list:
    """
    사용자 커스텀 GIF 로드.
    seek() 방식으로 각 프레임의 disposal을 PIL이 올바르게 적용한 뒤 추출.
    ImageSequence.Iterator는 disposal 처리가 불완전해 잔상 발생 가능.
    """
    frames = []
    with Image.open(str(gif_path)) as gif:
        n = getattr(gif, 'n_frames', 1)
        for i in range(n):
            gif.seek(i)
            frame = gif.copy().convert('RGBA')
            if frame.size != (80, 80):
                frame = frame.resize((80, 80), Image.LANCZOS)
            frames.append(_rgba_to_chroma(frame))
    return frames if frames else []


# ── 메인 앱 ──────────────────────────────────────────────────────────────────
class HamsterDancer:
    def __init__(self):
        self._last_key_time: float = 0.0   # 마지막 키 입력 시각
        self.running  = True
        self.visible  = True
        self.current_frame = 0
        self.frames = []
        self.gif_w = self.gif_h = 80

        self._resolve_gif_path()   # GIF 경로/크기만 확인 (PhotoImage 생성 X)
        self._init_window()        # tkinter 루트 먼저 생성
        self._load_gif_frames()    # 루트 생성 후 PhotoImage 생성
        self._init_tray()
        self._init_keyboard()

    # ── GIF 경로 확인 (tkinter 루트 불필요) ──────────────────────────────────
    def _resolve_gif_path(self):
        user_gif = get_app_dir() / 'hamster.gif'

        self.gif_w, self.gif_h = 80, 80             # 항상 고정 크기
        self._custom_gif = user_gif if user_gif.exists() else None

    # ── GIF 프레임 로드 (tkinter 루트 생성 후 호출) ───────────────────────────
    def _load_gif_frames(self):
        if self._custom_gif:
            self.frames = load_gif_frames(self._custom_gif)
        else:
            self.frames = load_builtin_frames()  # GIF 없이 직접 렌더 → 잔상 없음
        if not self.frames:
            raise RuntimeError('프레임 로드 실패')

    # ── 윈도우 초기화 ─────────────────────────────────────────────────────────
    def _init_window(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)           # 타이틀바 제거
        self.root.wm_attributes('-topmost', True)  # 항상 위
        self.root.wm_attributes('-transparentcolor', CHROMA)  # 크로마키 투명
        self.root.configure(bg=CHROMA)
        self.root.resizable(False, False)

        # 작업 영역 기반으로 우측 하단 위치 계산 (작업표시줄 자동 제외)
        _, _, wa_right, wa_bottom = get_workarea()
        x = wa_right  - self.gif_w - SIDE_OFFSET
        y = wa_bottom - self.gif_h - BOTTOM_OFFSET
        self.root.geometry(f'{self.gif_w}x{self.gif_h}+{x}+{y}')

        # Canvas: 프레임마다 배경부터 다시 그려 잔상 방지
        self.canvas = tk.Canvas(
            self.root, width=self.gif_w, height=self.gif_h,
            bg=CHROMA, highlightthickness=0, bd=0,
        )
        self.canvas.pack()
        self._canvas_img_id = None

        self.root.after(50, self._animate)

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
            # 숨김 상태: 긴 주기로 폴링 (CPU 낭비 방지)
            self.root.after(IDLE_DELAY, self._animate)

    def _frame_delay(self) -> int:
        """
        마지막 키 입력 후 경과 시간 기반 지수 감쇠.
        키 누르는 순간 즉시 MIN_DELAY, 이후 DECAY_HALF_LIFE마다 절반씩 감소.
        """
        elapsed = time.time() - self._last_key_time
        speed   = math.exp(-elapsed * math.log(2) / DECAY_HALF_LIFE)
        return int(MAX_DELAY - speed * (MAX_DELAY - MIN_DELAY))

    # ── 키보드 리스너 ─────────────────────────────────────────────────────────
    def _on_key_press(self, key):
        self._last_key_time = time.time()   # float 대입은 GIL로 원자적

    def _init_keyboard(self):
        try:
            self.listener = kb.Listener(on_press=self._on_key_press)
            self.listener.daemon = True
            self.listener.start()
        except Exception:
            pass  # 권한 부족 시에도 앱은 실행 (춤 반응만 안 됨)

    # ── 시스템 트레이 ─────────────────────────────────────────────────────────
    def _init_tray(self):
        icon_img = create_tray_icon_image()
        menu = pystray.Menu(
            pystray.MenuItem('보이기 / 숨기기', self._toggle, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('종료', self._quit),
        )
        self.tray = pystray.Icon('HamsterDancer', icon_img, 'HamsterDancer', menu)
        threading.Thread(target=self.tray.run, daemon=True).start()

    def _toggle(self, *_):
        self.visible = not self.visible
        if self.visible:
            def _show():
                self.root.deiconify()
                self._animate()   # 숨김 폴링에서 복귀 시 애니메이션 재시작
            self.root.after(0, _show)
        else:
            self.root.after(0, self.root.withdraw)

    def _quit(self, *_):
        """tray 스레드에서 호출 → 메인 스레드에서 정리"""
        self.running = False
        def _do_quit():
            self.tray.stop()
            self.root.destroy()
        self.root.after(0, _do_quit)

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    app = HamsterDancer()
    app.run()
