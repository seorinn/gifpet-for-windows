# 🐹 HamsterDancer

타이핑할수록 신나게 춤추는 햄스터 오버레이 (Windows)

화면 우측 하단에 상주하며, 키보드 입력 속도에 따라 애니메이션 속도가 실시간으로 반응합니다.

## 기능

- 타이핑 속도에 비례하는 댄스 애니메이션
- 시스템 트레이 아이콘 (우클릭 → 보이기/숨기기, 종료)
- GIF 커스터마이징 지원
- 설치 시 Windows 자동 시작 등록 가능

## 실행 방법

### 개발 환경에서 바로 실행

```bash
pip install -r requirements.txt
python main.py
```

### 빌드 및 설치파일 생성

1. `build.bat` 실행 → `dist\HamsterDancer\` 생성
2. [Inno Setup](https://jrsoftware.org/isdl.php) 설치 후 `setup.iss` 컴파일
3. `installer\HamsterDancer_Setup_v1.0.0.exe` 실행

## GIF 커스터마이징

`%APPDATA%\HamsterDancer\` 폴더에 원하는 GIF 파일을 `hamster.gif` 이름으로 저장 후 앱 재시작.

- 탐색기 주소창에 `%APPDATA%\HamsterDancer` 입력하면 바로 열림
- 어떤 크기의 GIF든 80×80으로 자동 리사이즈됨
- 투명 배경 GIF 권장

## 트레이 아이콘

| 메뉴 | 동작 |
|------|------|
| 보이기 / 숨기기 | 햄스터 표시 토글 |
| 종료 | 앱 종료 |
