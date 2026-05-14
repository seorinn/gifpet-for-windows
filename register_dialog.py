#!/usr/bin/env python3
"""GIF 펫 등록 / 목록 관리 다이얼로그 — 모던 UI"""

import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

from pet_registry import download_codex_pet, register_local_pet, delete_pet, load_registry

# ── 디자인 토큰 ────────────────────────────────────────────────────────────────
BG      = '#ffffff'
SURFACE = '#f4f4f5'
BORDER  = '#e4e4e7'
ACCENT  = '#6366f1'
TEXT    = '#18181b'
MUTED   = '#71717a'
DANGER  = '#ef4444'

F       = ('Segoe UI', 9)
F_SM    = ('Segoe UI', 8)
F_BOLD  = ('Segoe UI', 9, 'bold')
F_TITLE = ('Segoe UI', 10, 'bold')


def _center(win):
    win.update_idletasks()
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    w = win.winfo_reqwidth()
    h = win.winfo_reqheight()
    win.geometry(f'{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}')


def _entry(parent, var, width=36, **kw):
    """얇은 테두리 입력 필드 (border frame + flat entry)"""
    wrap = tk.Frame(parent, bg=BORDER, padx=1, pady=1)
    e = tk.Entry(
        wrap, textvariable=var, width=width,
        bg=BG, fg=TEXT, insertbackground=TEXT,
        relief='flat', font=F, bd=5,
        highlightthickness=0, **kw,
    )
    e.pack(fill='both', expand=True)
    return wrap, e


def _lbl(parent, text, color=MUTED, font=F_SM, **kw):
    return tk.Label(parent, text=text, bg=BG, fg=color, font=font,
                    anchor='w', **kw)


def _btn(parent, text, command, primary=False, danger=False, **kw):
    bg = ACCENT if primary else (SURFACE if not danger else '#fef2f2')
    fg = '#ffffff' if primary else (DANGER if danger else TEXT)
    abg = '#4f46e5' if primary else (BORDER if not danger else '#fee2e2')
    kw.setdefault('padx', 16)
    kw.setdefault('pady', 7)
    return tk.Button(
        parent, text=text, command=command,
        bg=bg, fg=fg, activebackground=abg, activeforeground=fg,
        relief='flat', bd=0, font=F_BOLD if primary else F,
        cursor='hand2', **kw,
    )


# ══════════════════════════════════════════════════════════════════════════════
class RegisterDialog(tk.Toplevel):

    def __init__(self, parent, app_dir: Path, on_complete=None):
        super().__init__(parent)
        self.app_dir    = app_dir
        self.on_complete = on_complete
        self._tab       = 'codex'      # 'codex' | 'local'

        self.title('펫 추가')
        self.configure(bg=BG)
        self.resizable(False, False)
        self.grab_set()

        self._build()
        _center(self)

        self.bind('<Return>', lambda _: self._submit())
        self.bind('<Escape>', lambda _: self.destroy())
        self._name_entry.focus_set()

    # ── 레이아웃 ──────────────────────────────────────────────────────────────
    def _build(self):
        root = tk.Frame(self, bg=BG, padx=24, pady=20)
        root.pack(fill='both', expand=True)

        # 제목
        _lbl(root, '펫 추가', color=TEXT, font=F_TITLE).pack(anchor='w', pady=(0, 14))

        # 이름
        _lbl(root, '이름').pack(anchor='w', pady=(0, 3))
        self._name_var = tk.StringVar()
        nw, self._name_entry = _entry(root, self._name_var, width=38)
        nw.pack(fill='x', pady=(0, 16))

        # 탭 스위처
        tab_row = tk.Frame(root, bg=BG)
        tab_row.pack(fill='x')
        self._tab_btns: dict[str, tk.Button] = {}
        for key, label in [('codex', 'URL로 등록'), ('local', '로컬 폴더')]:
            b = tk.Button(
                tab_row, text=label, relief='flat', bd=0,
                bg=BG, cursor='hand2', padx=0, pady=6,
                activebackground=BG,
                command=lambda k=key: self._switch(k),
            )
            b.pack(side='left', padx=(0, 20))
            self._tab_btns[key] = b
        self._update_tabs()

        # 탭 구분선
        tk.Frame(root, bg=BORDER, height=1).pack(fill='x', pady=(0, 14))

        # 콘텐츠 컨테이너
        self._content = tk.Frame(root, bg=BG)
        self._content.pack(fill='x')

        # ── URL 패널 ──
        self._url_panel = tk.Frame(self._content, bg=BG)
        _lbl(self._url_panel,
             'codex-pets.net에서 원하는 펫 페이지 URL을 붙여넣으세요'
             ).pack(anchor='w', pady=(0, 6))
        self._url_var = tk.StringVar()
        uw, self._url_entry = _entry(self._url_panel, self._url_var, width=38)
        uw.pack(fill='x')
        _lbl(self._url_panel, '예: https://codex-pets.net/#/pets/needle',
             color='#a1a1aa').pack(anchor='w', pady=(4, 0))
        self._url_panel.pack(fill='x')   # 초기 표시

        # ── 로컬 패널 ──
        self._local_panel = tk.Frame(self._content, bg=BG)
        _lbl(self._local_panel,
             'GIF 파일이 담긴 폴더를 선택하세요\n'
             '파일명에 -idle, -running 등 액션명이 포함되어야 합니다'
             ).pack(anchor='w', pady=(0, 8))
        folder_row = tk.Frame(self._local_panel, bg=BG)
        folder_row.pack(fill='x')
        self._folder_var = tk.StringVar()
        fw, self._folder_entry = _entry(folder_row, self._folder_var, width=28)
        fw.pack(side='left', fill='x', expand=True)
        _btn(folder_row, '찾기', self._browse).pack(side='left', padx=(6, 0))
        # 초기 숨김 (pack하지 않음)

        # 진행 상태
        self._status_var = tk.StringVar()
        self._status_lbl = tk.Label(
            root, textvariable=self._status_var,
            bg=BG, fg=MUTED, font=F_SM,
            anchor='w', justify='left', wraplength=340,
        )
        self._status_lbl.pack(fill='x', pady=(12, 0))

        self._progress = ttk.Progressbar(root, mode='indeterminate', length=340)
        self._progress.pack(fill='x')
        self._progress.pack_forget()

        # 버튼 행
        btn_row = tk.Frame(root, bg=BG)
        btn_row.pack(fill='x', pady=(14, 0))
        self._submit_btn = _btn(btn_row, '등록', self._submit, primary=True)
        self._submit_btn.pack(side='right')
        _btn(btn_row, '취소', self.destroy).pack(side='right', padx=(0, 8))

    # ── 탭 전환 ───────────────────────────────────────────────────────────────
    def _switch(self, key: str):
        self._tab = key
        self._update_tabs()
        if key == 'codex':
            self._local_panel.pack_forget()
            self._url_panel.pack(fill='x')
            self._url_entry.focus_set()
        else:
            self._url_panel.pack_forget()
            self._local_panel.pack(fill='x')

    def _update_tabs(self):
        for key, btn in self._tab_btns.items():
            active = key == self._tab
            btn.config(
                fg=ACCENT if active else MUTED,
                font=F_BOLD if active else F,
            )

    # ── 폴더 찾기 ─────────────────────────────────────────────────────────────
    def _browse(self):
        p = filedialog.askdirectory(parent=self, title='GIF 폴더 선택')
        if p:
            self._folder_var.set(p)

    # ── 제출 ──────────────────────────────────────────────────────────────────
    def _submit(self):
        if str(self._submit_btn['state']) == 'disabled':
            return

        name = self._name_var.get().strip()
        if not name:
            self._set_status('이름을 입력해 주세요', error=True)
            self._name_entry.focus_set()
            return

        self._submit_btn.config(state='disabled')
        self._status_var.set('')
        self._progress.pack(fill='x')
        self._progress.start(10)

        if self._tab == 'codex':
            url = self._url_var.get().strip()
            if not url:
                self._fail('URL을 입력해 주세요')
                return
            threading.Thread(target=self._do_codex, args=(name, url), daemon=True).start()
        else:
            folder = self._folder_var.get().strip()
            if not folder:
                self._fail('폴더를 선택해 주세요')
                return
            threading.Thread(target=self._do_local, args=(name, folder), daemon=True).start()

    def _do_codex(self, name, url):
        try:
            pet = download_codex_pet(
                name, url, self.app_dir,
                progress_cb=lambda msg: self.after(0, self._set_status, msg),
            )
            self.after(0, self._done, pet)
        except Exception as e:
            self.after(0, self._fail, str(e))

    def _do_local(self, name, folder):
        try:
            pet = register_local_pet(name, folder, self.app_dir)
            self.after(0, self._done, pet)
        except Exception as e:
            self.after(0, self._fail, str(e))

    def _done(self, pet):
        self._progress.stop()
        self._progress.pack_forget()
        self._set_status(f'"{pet["name"]}" 등록 완료! ({len(pet["actions"])}개 액션)')
        if self.on_complete:
            self.on_complete(pet)
        self.after(800, self.destroy)

    def _fail(self, msg):
        self._progress.stop()
        self._progress.pack_forget()
        self._submit_btn.config(state='normal')
        self._set_status(msg, error=True)

    def _set_status(self, msg: str, error: bool = False):
        self._status_lbl.config(fg=DANGER if error else MUTED)
        self._status_var.set(msg)


# ══════════════════════════════════════════════════════════════════════════════
class ManagePetsDialog(tk.Toplevel):

    def __init__(self, parent, app_dir: Path, on_change=None):
        super().__init__(parent)
        self.app_dir   = app_dir
        self.on_change = on_change

        self.title('등록된 펫')
        self.configure(bg=BG)
        self.resizable(False, False)
        self.grab_set()

        self._build()
        self.update_idletasks()
        _center(self)
        self.bind('<Escape>', lambda _: self.destroy())

    # ── 레이아웃 ──────────────────────────────────────────────────────────────
    def _build(self):
        self.minsize(400, 0)

        root = tk.Frame(self, bg=BG, padx=24, pady=20)
        root.pack(fill='both', expand=True)

        _lbl(root, '등록된 펫', color=TEXT, font=F_TITLE).pack(anchor='w', pady=(0, 4))
        _lbl(root, '이름 변경 또는 삭제할 수 있습니다',
             color=MUTED, font=F_SM).pack(anchor='w', pady=(0, 14))

        self._list_wrap = tk.Frame(root, bg=BG)
        self._list_wrap.pack(fill='x')
        self._refresh()

        tk.Frame(root, bg=BORDER, height=1).pack(fill='x', pady=(16, 12))
        _btn(root, '닫기', self.destroy).pack(side='right')

    def _refresh(self):
        for w in self._list_wrap.winfo_children():
            w.destroy()

        reg  = load_registry(self.app_dir)
        pets = reg.get('pets', [])

        if not pets:
            _lbl(self._list_wrap,
                 '등록된 펫이 없습니다\nGIF 등록... 으로 추가하세요',
                 color=MUTED, font=F).pack(pady=(0, 6))
            return

        for pet in pets:
            self._pet_row(pet, pet['id'] == reg.get('active'))

    # ── 펫 행 ─────────────────────────────────────────────────────────────────
    def _pet_row(self, pet: dict, is_active: bool):
        container = tk.Frame(self._list_wrap, bg=BG)
        container.pack(fill='x', pady=3)

        # ── view 모드 ──────────────────────────────────────────────────────────
        view = tk.Frame(container, bg=BG)
        view.pack(fill='x')

        # 오른쪽 버튼을 먼저 pack해야 expand 위젯에 밀리지 않음
        v_right = tk.Frame(view, bg=BG)
        v_right.pack(side='right')
        rename_btn = _btn(v_right, '이름 변경', None, padx=8, pady=3)
        rename_btn.pack(side='left', padx=(0, 6))
        _btn(v_right, '삭제', lambda pid=pet['id']: self._delete(pid),
             danger=True, padx=8, pady=3).pack(side='left')

        # 왼쪽: 활성 dot + 이름 (오른쪽 이후에 pack)
        v_left = tk.Frame(view, bg=BG)
        v_left.pack(side='left', fill='x', expand=True)
        tk.Frame(v_left, bg=ACCENT if is_active else BORDER,
                 width=6, height=6).pack(side='left', padx=(0, 10), pady=8)
        tk.Label(v_left, text=pet['name'], bg=BG, fg=TEXT,
                 font=F_BOLD, anchor='w').pack(side='left')

        # ── edit 모드 (초기 숨김) ──────────────────────────────────────────────
        edit = tk.Frame(container, bg=BG)

        # 오른쪽 버튼 먼저
        e_right = tk.Frame(edit, bg=BG)
        e_right.pack(side='right')
        save_btn   = _btn(e_right, '저장', None, primary=True, padx=8, pady=3)
        cancel_btn = _btn(e_right, '취소', None, padx=8, pady=3)
        save_btn.pack(side='left', padx=(0, 6))
        cancel_btn.pack(side='left')

        # 왼쪽: dot + 입력창
        e_left = tk.Frame(edit, bg=BG)
        e_left.pack(side='left', fill='x', expand=True)
        tk.Frame(e_left, bg=ACCENT if is_active else BORDER,
                 width=6, height=6).pack(side='left', padx=(0, 10), pady=8)
        var = tk.StringVar(value=pet['name'])
        ew, entry = _entry(e_left, var, width=18)
        ew.pack(side='left', fill='x', expand=True)

        # ── 콜백 ──────────────────────────────────────────────────────────────
        def start_edit():
            view.pack_forget()
            var.set(pet['name'])
            edit.pack(fill='x')
            entry.focus_set()
            entry.select_range(0, 'end')

        def do_save(_=None):
            new_name = var.get().strip()
            if new_name and new_name != pet['name']:
                self._rename(pet['id'], new_name)
            else:
                do_cancel()

        def do_cancel(_=None):
            edit.pack_forget()
            view.pack(fill='x')

        rename_btn.config(command=start_edit)
        save_btn.config(command=do_save)
        cancel_btn.config(command=do_cancel)
        entry.bind('<Return>', do_save)
        entry.bind('<Escape>', do_cancel)

    # ── 이름 변경 / 삭제 ──────────────────────────────────────────────────────
    def _rename(self, pet_id: str, new_name: str):
        from pet_registry import save_registry
        reg = load_registry(self.app_dir)
        for p in reg['pets']:
            if p['id'] == pet_id:
                p['name'] = new_name
                break
        save_registry(self.app_dir, reg)
        self._refresh()
        if self.on_change:
            self.on_change()

    def _delete(self, pet_id: str):
        if not messagebox.askyesno('펫 삭제', '이 펫을 삭제할까요?', parent=self):
            return
        delete_pet(self.app_dir, pet_id)
        self._refresh()
        if self.on_change:
            self.on_change()
