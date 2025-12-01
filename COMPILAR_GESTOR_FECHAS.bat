@echo off
REM ============================================
REM  COMPILAR - GESTOR DE FECHAS EXIF (PyInstaller)
REM ============================================

echo Limpiando compilaciones anteriores...

REM Eliminar carpetas build y dist si existen
rmdir /s /q build 2>nul
rmdir /s /q dist  2>nul

REM Eliminar cualquier archivo .spec previo (incluido el antiguo GestorArchivosUnificado.spec)
del /q "*.spec" 2>nul

echo.
echo Compilando ejecutable con PyInstaller...
echo (esto puede tardar unos minutos)

py -m PyInstaller ^
 --onefile ^
 --windowed ^
 --icon="icono.ico" ^
 --noconsole ^
 --name "Gestor de fechas EXIF" ^
 --add-data "icono.ico;." ^
 main.py

echo.
echo ============================================
echo  PROCESO TERMINADO
echo  Busca el ejecutable en la carpeta: dist
echo  Archivo: Gestor de fechas EXIF.exe
echo ============================================
echo.
pause
