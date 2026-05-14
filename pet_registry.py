#!/usr/bin/env python3
"""펫 등록소 – 스프라이트시트 다운로드·슬라이싱, 로컬 GIF 스캔, 레지스트리 관리"""

import io
import json
import os
import re
import urllib.request
from pathlib import Path

from PIL import Image

# ── codex-pets 표준 스프라이트시트 스펙 ────────────────────────────────────────
ACTIONS = [
    'idle', 'running-right', 'running-left', 'waving',
    'jumping', 'failed', 'waiting', 'running', 'review',
]
CELL_W, CELL_H = 192, 208
COLS = 8

# 로컬 파일명 suffix → 표준 액션명
_SUFFIX_MAP: dict[str, str] = {
    'idle':          'idle',
    'running-right': 'running-right', 'running_right': 'running-right',
    'running-left':  'running-left',  'running_left':  'running-left',
    'waving':        'waving',        'wave':           'waving',
    'jumping':       'jumping',       'jump':           'jumping',
    'failed':        'failed',        'fail':           'failed',
    'waiting':       'waiting',       'wait':           'waiting',
    'running':       'running',       'run':            'running',
    'review':        'review',
}


# ── 레지스트리 I/O ──────────────────────────────────────────────────────────────
def load_registry(app_dir: Path) -> dict:
    p = app_dir / 'pets_registry.json'
    if p.exists():
        try:
            with open(p, encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {'active': None, 'pets': []}


def save_registry(app_dir: Path, reg: dict):
    p = app_dir / 'pets_registry.json'
    tmp = p.with_suffix('.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(reg, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)


def _pets_dir(app_dir: Path) -> Path:
    d = app_dir / 'pets'
    d.mkdir(exist_ok=True)
    return d


# ── 스프라이트시트 → GIF 변환 ──────────────────────────────────────────────────
def _is_empty_frame(img: Image.Image, threshold: float = 0.92) -> bool:
    """대부분 투명이면 빈 프레임"""
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    pixels = list(img.split()[3].getdata())
    return sum(1 for a in pixels if a < 10) / len(pixels) >= threshold


def _save_rgba_as_gif(frames: list, out_path: Path, duration: int = 120) -> bool:
    """RGBA 프레임 리스트 → animated GIF (투명 지원)"""
    if not frames:
        return False

    gif_frames = []
    for rgba in frames:
        if rgba.mode != 'RGBA':
            rgba = rgba.convert('RGBA')

        # RGB 부분을 흰 배경에 합성 후 255색 양자화 (인덱스 255 = 투명 예약)
        white_bg = Image.new('RGBA', rgba.size, (255, 255, 255, 255))
        white_bg.paste(rgba, mask=rgba.split()[3])
        p = white_bg.convert('RGB').quantize(colors=255, dither=0)

        pal = p.getpalette()
        while len(pal) < 256 * 3:
            pal.extend([0, 0, 0])
        p.putpalette(pal)

        # 알파 < 128인 픽셀 → 팔레트 인덱스 255 (투명)
        alpha_bytes = bytearray(rgba.split()[3].tobytes())
        p_bytes = bytearray(p.tobytes())
        for i, av in enumerate(alpha_bytes):
            if av < 128:
                p_bytes[i] = 255
        p_fixed = Image.frombytes('P', p.size, bytes(p_bytes))
        p_fixed.putpalette(pal)
        gif_frames.append(p_fixed)

    gif_frames[0].save(
        out_path, save_all=True, append_images=gif_frames[1:],
        loop=0, duration=duration, transparency=255, disposal=2,
    )
    return True


def _extract_row(sheet: Image.Image, row: int, out_path: Path) -> bool:
    """스프라이트시트 row 행 → GIF 파일"""
    frames = []
    for col in range(COLS):
        x, y = col * CELL_W, row * CELL_H
        if y + CELL_H > sheet.height:
            break
        frame = sheet.crop((x, y, x + CELL_W, y + CELL_H)).convert('RGBA')
        if not _is_empty_frame(frame):
            frames.append(frame)
    return _save_rgba_as_gif(frames, out_path)


# ── codex-pets URL 등록 ─────────────────────────────────────────────────────────
def download_codex_pet(name: str, url: str, app_dir: Path,
                       progress_cb=None) -> dict:
    m = re.search(r'/pets/([^/#?]+)', url)
    if not m:
        raise ValueError('URL에서 펫 ID를 찾을 수 없습니다.\n'
                         '예: https://codex-pets.net/#/pets/needle')
    pet_id = m.group(1).strip()

    if progress_cb:
        progress_cb('API 정보 가져오는 중...')
    req = urllib.request.Request(
        f'https://codex-pets.net/api/pets/{pet_id}',
        headers={'User-Agent': 'GifPet/1.0'},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read().decode())

    # API 응답은 {'pet': {...}} 구조
    pet_data = data.get('pet', data)
    spritesheet_url = pet_data.get('spritesheetUrl', '')
    if not spritesheet_url:
        raise ValueError(f'"{pet_id}" 펫을 찾을 수 없습니다.\nURL을 다시 확인해 주세요.')

    if progress_cb:
        progress_cb('스프라이트시트 다운로드 중...')
    req2 = urllib.request.Request(spritesheet_url, headers={'User-Agent': 'GifPet/1.0'})
    with urllib.request.urlopen(req2, timeout=30) as r:
        sheet_data = r.read()

    sheet = Image.open(io.BytesIO(sheet_data))
    total_rows = min(sheet.height // CELL_H, len(ACTIONS))

    pet_dir = _pets_dir(app_dir) / pet_id
    pet_dir.mkdir(exist_ok=True)

    actions: dict[str, str] = {}
    for i in range(total_rows):
        action = ACTIONS[i]
        if progress_cb:
            progress_cb(f'GIF 생성 중: {action}  ({i + 1}/{total_rows})')
        out = pet_dir / f'{action}.gif'
        if _extract_row(sheet, i, out):
            actions[action] = str(out)

    if not actions:
        raise RuntimeError('액션 GIF를 하나도 추출하지 못했습니다')

    pet_entry = {'name': name, 'id': pet_id, 'source': 'codex',
                 'url': url, 'actions': actions}
    _upsert(app_dir, pet_entry)
    return pet_entry


# ── 로컬 폴더 등록 ─────────────────────────────────────────────────────────────
def register_local_pet(name: str, folder: str, app_dir: Path) -> dict:
    fp = Path(folder)
    if not fp.is_dir():
        raise ValueError(f'폴더를 찾을 수 없습니다:\n{folder}')
    gifs = list(fp.glob('*.gif'))
    if not gifs:
        raise ValueError('폴더에 GIF 파일이 없습니다')

    actions: dict[str, str] = {}
    for gif in gifs:
        stem = gif.stem.lower()
        for suffix, canonical in _SUFFIX_MAP.items():
            if stem.endswith(f'-{suffix}') or stem.endswith(f'_{suffix}'):
                actions.setdefault(canonical, str(gif))
                break

    if not actions:
        raise ValueError(
            '파일명에서 액션을 인식할 수 없습니다.\n'
            '예: "이름-idle.gif", "이름-running.gif" 형식으로 저장 후 다시 시도하세요.'
        )

    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    if not slug:
        import hashlib
        slug = hashlib.md5(name.encode()).hexdigest()[:8]
    pet_id = slug + '-local'
    pet_entry = {'name': name, 'id': pet_id, 'source': 'local',
                 'folder': folder, 'actions': actions}
    _upsert(app_dir, pet_entry)
    return pet_entry


# ── 레지스트리 헬퍼 ────────────────────────────────────────────────────────────
def _upsert(app_dir: Path, pet_entry: dict):
    reg = load_registry(app_dir)
    reg['pets'] = [p for p in reg['pets'] if p['id'] != pet_entry['id']]
    reg['pets'].append(pet_entry)
    if reg['active'] is None:
        reg['active'] = pet_entry['id']
    save_registry(app_dir, reg)


def delete_pet(app_dir: Path, pet_id: str):
    reg = load_registry(app_dir)
    reg['pets'] = [p for p in reg['pets'] if p['id'] != pet_id]
    if reg['active'] == pet_id:
        reg['active'] = reg['pets'][0]['id'] if reg['pets'] else None
    save_registry(app_dir, reg)
    # codex 펫 캐시 폴더 삭제
    import shutil
    pet_dir = _pets_dir(app_dir) / pet_id
    if pet_dir.exists():
        shutil.rmtree(pet_dir, ignore_errors=True)


def set_active_pet(app_dir: Path, pet_id: str):
    reg = load_registry(app_dir)
    reg['active'] = pet_id
    save_registry(app_dir, reg)


def get_active_pet(app_dir: Path) -> dict | None:
    reg = load_registry(app_dir)
    active = reg.get('active')
    if not active:
        return None
    return next((p for p in reg['pets'] if p['id'] == active), None)
