# 🐹 GifPet for Windows

타이핑할수록 신나게 춤추는 GIF 오버레이 (Windows)

화면 위에 상주하며, 키보드 입력 속도에 따라 애니메이션 속도가 실시간으로 반응합니다.

## 설치 방법

[Releases](../../releases) 에서 `GifPet_Setup_v1.1.0.exe` 다운로드 후 실행.

- 설치 중 **"Windows 시작 시 자동 실행"** 체크 시 컴퓨터를 켤 때마다 자동으로 시작됩니다.
- Python 등 별도 설치 불필요.
- Windows 전용

## 기능

- 타이핑 속도에 비례하는 댄스 애니메이션
- 시스템 트레이 아이콘 (우클릭 메뉴)
- GIF 커스터마이징 지원
- 기본 속도 / 크기 조절 (설정 자동 저장)
- 드래그로 자유 위치 이동 (다중 모니터 지원)
- 클릭 시 하트 이펙트 (쓰다듬기)
- Windows 자동 시작 등록

## 트레이 아이콘 메뉴

| 메뉴 | 동작 |
|------|------|
| 보이기 / 숨기기 | 오버레이 표시 토글 |
| 기본 속도 | 매우 느리게 / 느리게 / 보통 / 빠르게 / 매우 빠르게 |
| 크기 | 30 / 55 / 80 / 120 / 170 px |
| GIF 폴더 열기 | 커스텀 GIF 저장 폴더 열기 |
| 종료 | 앱 종료 |

## 위치 이동

오버레이를 드래그하면 자유롭게 위치를 옮길 수 있습니다. 다중 모니터 환경도 지원하며, 위치는 자동 저장됩니다.

## 쓰다듬기

펫을 클릭하면 하트가 위로 떠오릅니다. 클릭할 때마다 하트 밝기가 랜덤하게 달라집니다.

## GIF 커스터마이징

1. 트레이 아이콘 우클릭 → **GIF 폴더 열기**
2. 원하는 GIF 파일을 `pet.gif` 이름으로 저장
3. 앱 재시작

- 어떤 크기의 GIF든 선택한 표시 크기로 자동 리사이즈됨
- 투명 배경 GIF 권장

## 개발 환경에서 실행

```bash
pip install -r requirements.txt
python main.py
```

### 빌드

```bash
pip install -r requirements-build.txt
python create_assets.py
python -m PyInstaller --clean -y --onedir --windowed --name GifPet --icon icon.ico --add-data "pet.gif;." main.py
# 이후 Inno Setup으로 setup.iss 컴파일
```
