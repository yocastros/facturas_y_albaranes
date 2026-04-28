@echo off
setlocal enabledelayedexpansion

echo.
echo ===================================================
echo   Sistema de Gestion de Facturas y Albaranes v1.0
echo   Instalador Windows
echo ===================================================
echo.

:: Guardar directorio del bat
set "INSTDIR=%~dp0"
if "%INSTDIR:~-1%"=="\" set "INSTDIR=%INSTDIR:~0,-1%"

:: Verificar administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Ejecuta como Administrador.
    echo     Clic derecho - Ejecutar como administrador
    pause
    exit /b 1
)

:: [1/6] Python
echo [1/6] Verificando Python...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo      Descargando Python 3.11...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '%TEMP%\python_inst.exe'"
    "%TEMP%\python_inst.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_tcltk=1
    del "%TEMP%\python_inst.exe"
    echo [OK] Python instalado
) else (
    python --version
    echo [OK] Python ya instalado
)

:: [2/6] Tesseract
echo.
echo [2/6] Verificando Tesseract OCR...
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    echo [OK] Tesseract ya instalado
) else (
    echo      Descargando Tesseract...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/UB-Mannheim/tesseract/releases/download/v5.5.0.20241111/tesseract-ocr-w64-setup-5.5.0.20241111.exe' -OutFile '%TEMP%\tess.exe'"
    "%TEMP%\tess.exe" /S
    del "%TEMP%\tess.exe"
    echo [OK] Tesseract instalado
)

if not exist "C:\Program Files\Tesseract-OCR\tessdata\spa.traineddata" (
    echo      Descargando idioma espanol...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/tesseract-ocr/tessdata/raw/main/spa.traineddata' -OutFile 'C:\Program Files\Tesseract-OCR\tessdata\spa.traineddata'"
    echo [OK] Idioma espanol instalado
) else (
    echo [OK] Idioma espanol ya instalado
)

:: [3/6] Poppler
echo.
echo [3/6] Verificando Poppler...
if exist "C:\poppler\Library\bin\pdftoppm.exe" (
    echo [OK] Poppler ya instalado
) else (
    echo      Descargando Poppler...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/oschwartz10612/poppler-windows/releases/download/v24.08.0-0/Release-24.08.0-0.zip' -OutFile '%TEMP%\poppler.zip'"
    powershell -Command "Expand-Archive -Path '%TEMP%\poppler.zip' -DestinationPath '%TEMP%\poppler_ext' -Force"
    if exist "C:\poppler" rmdir /s /q "C:\poppler"
    for /d %%i in ("%TEMP%\poppler_ext\*") do xcopy "%%i" "C:\poppler\" /e /i /q >nul
    del "%TEMP%\poppler.zip"
    rmdir /s /q "%TEMP%\poppler_ext" >nul 2>&1
    echo [OK] Poppler instalado
)

:: [4/6] Variables de entorno
echo.
echo [4/6] Configurando variables de entorno...
setx /M TESSDATA_PREFIX "C:\Program Files\Tesseract-OCR\tessdata" >nul 2>&1
echo [OK] Variables configuradas

:: [5/6] Dependencias Python
echo.
echo [5/6] Instalando dependencias Python...
cd /d "%INSTDIR%\backend"
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt -q
python -m pip install pystray pillow pywin32 -q
echo [OK] Dependencias instaladas

:: [6/6] Acceso directo
echo.
echo [6/6] Creando acceso directo...
cd /d "%INSTDIR%"
python crear_acceso_directo.py

echo.
echo ===================================================
echo   Instalacion completada!
echo   Doble clic en el icono del escritorio para
echo   arrancar el sistema.
echo ===================================================
echo.
pause
