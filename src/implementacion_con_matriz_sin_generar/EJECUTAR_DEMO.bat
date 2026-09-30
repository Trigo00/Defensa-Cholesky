@echo off
setlocal
title Cholesky MPI - demostracion con matriz externa

rem Cambia solo MATRIZ_AQUI.txt. Este script usa dos procesos MPI.
set "DIRECTORIO_WINDOWS=%~dp0"
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
echo Matriz de entrada: MATRIZ_AQUI.txt
echo Factor generado:   RESULTADO_L.txt
echo Procesos MPI:      2
echo.

wsl.exe -e sh -lc "cd '%DIRECTORIO_WSL%' && make && mpirun --bind-to core --map-by core -np 2 ./cholesky_app MATRIZ_AQUI.txt RESULTADO_L.txt --validate"
if errorlevel 1 (
    echo.
    echo La matriz fue rechazada o ocurrio un error. Lee el mensaje anterior.
    echo No se genero un nuevo factor L valido.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Listo: abrí RESULTADO_L.txt para ver el factor L.
echo ============================================================
pause
