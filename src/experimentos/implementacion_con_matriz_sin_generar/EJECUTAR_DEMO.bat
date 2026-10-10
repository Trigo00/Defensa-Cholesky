@echo off
setlocal
title Cholesky MPI - demostracion con matriz externa

rem Cambia solo MATRIZ.txt. Este script usa dos procesos MPI.
set "DIRECTORIO_WINDOWS=%~dp0."
set "DIRECTORIO_WSL="
if exist "%~dp0RESULTADO_L.txt" del /q "%~dp0RESULTADO_L.txt"
if exist "%~dp0RESULTADO_L.txt" (
    echo ERROR: no se pudo eliminar el resultado anterior. Cierra el archivo y reintenta.
    pause
    exit /b 1
)
for /f "usebackq delims=" %%D in (`wsl.exe wslpath -a "%DIRECTORIO_WINDOWS%"`) do set "DIRECTORIO_WSL=%%D"

if not defined DIRECTORIO_WSL (
    echo ERROR: no se pudo acceder a WSL.
    echo Esta demostracion requiere la misma instalacion WSL/MPI usada para compilar el proyecto.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Cholesky MPI: matriz externa
echo ============================================================
echo.
echo Matriz de entrada: MATRIZ.txt
echo Factor generado:   RESULTADO_L.txt
echo Procesos MPI:      2
echo.

wsl.exe -e sh -lc "cd '%DIRECTORIO_WSL%' && sh ejecutar_demo.sh"
if errorlevel 1 (
    echo.
    echo La matriz fue rechazada o ocurrio un error. Lee el mensaje anterior.
    if exist "%~dp0RESULTADO_L.txt" del /q "%~dp0RESULTADO_L.txt"
    echo No se genero un nuevo factor L valido.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Listo: abre RESULTADO_L.txt para ver el factor L.
echo ============================================================
pause
