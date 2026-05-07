@echo off
chcp 65001 > nul
echo ===== HamsterDancer 빌드 =====
echo.

echo [1/3] 의존성 설치...
pip install -r requirements.txt
if errorlevel 1 (
    echo 오류: pip install 실패
    pause & exit /b 1
)

echo.
echo [2/3] 에셋 생성 (hamster.gif, icon.ico)...
python create_assets.py
if errorlevel 1 (
    echo 오류: 에셋 생성 실패
    pause & exit /b 1
)

echo.
echo [3/3] PyInstaller로 exe 빌드...
pyinstaller ^
  --clean ^
  --onedir ^
  --windowed ^
  --name HamsterDancer ^
  --icon icon.ico ^
  --add-data "hamster.gif;." ^
  main.py
if errorlevel 1 (
    echo 오류: PyInstaller 빌드 실패
    pause & exit /b 1
)

echo.
echo ============================
echo  빌드 완료!
echo  결과물: dist\HamsterDancer\
echo  다음 단계: Inno Setup으로 setup.iss 컴파일
echo ============================
pause
