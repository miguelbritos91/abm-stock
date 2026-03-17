@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

:: Siempre ejecutar desde la carpeta raíz del proyecto
cd /d "%~dp0"

title ABM Stock - Build

echo.
echo  ====================================================
echo   ABM Stock - Compilacion e Instalador para Windows
echo  ====================================================
echo.

:: ============================================================
::  PASO 1/5 — Verificar Python
:: ============================================================
echo  [1/5] Verificando Python...

set PYTHON=

python --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON=python
    goto :python_ok
)

py --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON=py
    goto :python_ok
)

echo.
echo  ERROR: Python no encontrado en el sistema.
echo.
echo         Instala Python 3.10 o superior desde:
echo           https://python.org/downloads
echo.
echo         Durante la instalacion marca la opcion:
echo           "Add Python to PATH"
echo.
pause
exit /b 1

:python_ok
for /f "tokens=*" %%v in ('!PYTHON! --version 2^>^&1') do (
    echo         %%v detectado.
)

:: ============================================================
::  PASO 2/5 — Instalar dependencias de compilacion
:: ============================================================
echo.
echo  [2/5] Instalando dependencias de compilacion...

!PYTHON! -m pip install --quiet --upgrade pip >nul 2>&1
!PYTHON! -m pip install --quiet --upgrade pyinstaller pillow

if errorlevel 1 (
    echo.
    echo  ERROR: No se pudieron instalar las dependencias.
    echo         Verifica tu conexion a internet e intenta de nuevo.
    pause & exit /b 1
)

echo         pyinstaller + pillow: OK

:: ============================================================
::  PASO 3/5 — Limpiar artefactos anteriores
:: ============================================================
echo.
echo  [3/5] Limpiando compilaciones anteriores...

if exist dist         rmdir /s /q dist
if exist build        rmdir /s /q build
if exist ABMStock.spec del /q ABMStock.spec

if not exist builds   mkdir builds

echo         Limpieza: OK

:: ============================================================
::  PASO 4/5 — Compilar con PyInstaller
:: ============================================================
echo.
echo  [4/5] Compilando aplicacion con PyInstaller...
echo         (este proceso puede demorar varios minutos)
echo.

:: Icono opcional
set ICON_ARG=
if exist "assets\icon.ico" (
    set ICON_ARG=--icon "assets\icon.ico"
    echo         Usando icono: assets\icon.ico
)

!PYTHON! -m PyInstaller ^
    --name "ABMStock" ^
    --windowed ^
    --noconfirm ^
    --clean ^
    --paths "." ^
    !ICON_ARG! ^
    --add-data "assets;assets" ^
    --collect-all PIL ^
    --hidden-import tkinter ^
    --hidden-import tkinter.ttk ^
    --hidden-import sqlite3 ^
    main.py

if errorlevel 1 (
    echo.
    echo  ERROR: PyInstaller fallo durante la compilacion.
    echo         Revisa los mensajes anteriores para mas detalles.
    pause & exit /b 1
)

:: Crear carpetas que la app espera encontrar al ejecutarse
if not exist "dist\ABMStock\images"  mkdir "dist\ABMStock\images"
if not exist "dist\ABMStock\assets"  mkdir "dist\ABMStock\assets"

:: Copiar archivos extras al bundle
if exist "LICENSE"    copy /y "LICENSE"    "dist\ABMStock\LICENSE"    >nul
if exist "README.md"  copy /y "README.md"  "dist\ABMStock\README.md"  >nul

echo.
echo         Compilacion exitosa.
echo         Binarios generados en: dist\ABMStock\

:: ============================================================
::  PASO 5/5 — Generar instalador (.exe) o ZIP portable
:: ============================================================
echo.
echo  [5/5] Generando instalador Windows...
echo.

!PYTHON! scripts\build_installer.py

if errorlevel 1 (
    echo.
    echo  ADVERTENCIA: El instalador no pudo generarse.
    echo  Los binarios compilados siguen disponibles en dist\ABMStock\
    echo.
    pause & exit /b 0
)

:: ============================================================
::  Resultado final
:: ============================================================
echo.
echo  ====================================================
echo   BUILD COMPLETADO EXITOSAMENTE
echo  ====================================================
echo.

for %%f in (builds\ABMStock_Setup_*.exe) do (
    echo   Instalador Windows : builds\%%~nxf
)
for %%f in (builds\ABMStock_*_portable.zip) do (
    echo   ZIP portable       : builds\%%~nxf
)

echo.
echo  Para instalar la aplicacion ejecuta el archivo
echo  ABMStock_Setup_*.exe como Administrador.
echo.
pause
