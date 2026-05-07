#!/usr/bin/env python3
"""
빌드 전에 실행하여 기본 에셋 생성:
  - hamster.gif  (기본 픽셀아트 햄스터 애니메이션)
  - icon.ico     (exe / 설치파일 아이콘)
"""

from pathlib import Path
from main import draw_hamster_frame, create_tray_icon_image
from PIL import Image


def create_hamster_gif(path: Path) -> None:
    print(f'  hamster.gif 생성 중... → {path}')
    frames = [draw_hamster_frame(i) for i in range(8)]
    frames[0].save(
        str(path),
        save_all=True,
        append_images=frames[1:],
        loop=0,
        duration=[120] * 8,
        format='GIF',
    )
    print('  완료!')


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
    print('=== HamsterDancer 에셋 생성 ===')
    create_hamster_gif(base / 'hamster.gif')
    create_ico(base / 'icon.ico')
    print('\n모든 에셋 생성 완료!')
