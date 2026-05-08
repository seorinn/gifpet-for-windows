#!/usr/bin/env python3
"""
빌드 전에 실행하여 기본 에셋 생성:
  - icon.ico  (exe / 설치파일 아이콘)
"""

from pathlib import Path
from main import create_tray_icon_image
from PIL import Image


def create_ico(path: Path) -> None:
    print(f'  icon.ico 생성 중... → {path}')
    base_img = create_tray_icon_image()   # 64x64 🐹 이모지
    sizes = [16, 32, 48, 64]
    imgs  = [base_img.resize((s, s), Image.LANCZOS) for s in sizes]
    imgs[0].save(
        str(path),
        format='ICO',
        append_images=imgs[1:],
    )
    print('  완료!')


if __name__ == '__main__':
    base = Path(__file__).parent
    print('=== GifPet 에셋 생성 ===')
    create_ico(base / 'icon.ico')
    print('\n모든 에셋 생성 완료!')
