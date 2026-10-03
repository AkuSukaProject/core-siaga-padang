@echo off
rem Jalankan dari folder skrip ini agar jalur relatif ..\ selalu benar.
cd /d "%~dp0"
echo ========================================================
echo MEMBANGUN DB RILIS APLIKASI (ranah_siaga_rilis.db)
echo ========================================================
echo Sumber: ranah_siaga_v2.db (core.py + build_db_v2_with_tea.py)
echo Langkah: rute kawasan aman (2) lalu pengecilan NF-03 (4).
echo Langkah 1 (kapasitas) dan 3 (porsi opsi A) tidak ikut; lihat README.

set SUMBER=..\ranah_siaga_v2.db
set RILIS=..\ranah_siaga_rilis.db

if not exist %SUMBER% (
    echo [ERROR] %SUMBER% tidak ditemukan. Ekstrak ranah_siaga_v2.db.zip atau jalankan build_db_v2_with_tea.py.
    exit /b 1
)
copy /Y %SUMBER% %RILIS% >nul
if errorlevel 1 goto error

echo.
echo [1/2] Rute ke kawasan aman...
..\env\Scripts\python.exe 2_safe_zone_routes.py --db %RILIS%
if errorlevel 1 goto error

echo.
echo [2/2] Pengecilan DB...
..\env\Scripts\python.exe 4_shrink_db.py --db %RILIS%
if errorlevel 1 goto error

echo.
..\env\Scripts\python.exe -c "import hashlib, os; p = r'%RILIS%'; print('SHA-256 :', hashlib.sha256(open(p, 'rb').read()).hexdigest()); print('Ukuran  :', os.path.getsize(p), 'byte')"
echo Salin berkas ini ke android/app/src/main/assets/ranah_siaga.db dan perbarui dataset_manifest.json aplikasi.
exit /b 0

:error
echo.
echo [ERROR] Pembuatan DB rilis terhenti.
exit /b 1
