@echo off
echo ========================================================
echo MENJALANKAN PIPELINE PEMROSESAN DATABASE EVAKUASI FINAL
echo ========================================================

echo.
echo [1/5] Memperbarui Kapasitas TES (FEMA P-646 / OSM)...
..\env\Scripts\python.exe 1_update_capacity.py
if errorlevel 1 goto error

echo.
echo [2/5] Membangun Rute ke Zona Aman...
..\env\Scripts\python.exe 2_safe_zone_routes.py
if errorlevel 1 goto error

echo.
echo [3/5] Melakukan Penugasan Warga dan Distribusi Porsi...
..\env\Scripts\python.exe 3_assignment_and_shares.py
if errorlevel 1 goto error

echo.
echo [4/5] Mengecilkan Ukuran Database (Target = 75 MB)...
..\env\Scripts\python.exe 4_shrink_db.py
if errorlevel 1 goto error

echo.
echo [5/5] Melakukan Simulasi Agen Makro & Menghitung Metrik...
..\env\Scripts\python.exe 5_agent_simulation_metrics.py
if errorlevel 1 goto error

echo.
echo ========================================================
echo PIPELINE SELESAI DENGAN SUKSES! Database keluaran: ranah_siaga_v3.db
echo ========================================================
goto end

:error
echo.
echo [ERROR] Pipeline terhenti karena terjadi kesalahan pada skrip Python.
exit /b 1

:end
exit /b 0
