@echo off
chcp 65001 > nul
title VLESS-Checker

:: 1. Проверяем, установлен ли Python
python --version >nul 2>&1
if %errorlevel% equ 0 goto RUN_CHECKER

py --version >nul 2>&1
if %errorlevel% equ 0 goto RUN_CHECKER_PY

:: 2. Если Python не найден — спрашиваем разрешение
echo.
echo [!] Python не найден в вашей системе!
echo Для работы программы требуется интерпретатор Python 3.
echo.
set /p "USER_CHOICE=Скачать и установить Python автоматически? (Y/N / Д/Н): "

:: Проверка ответа пользователя
if /i "%USER_CHOICE%"=="Y" goto INSTALL_PYTHON
if /i "%USER_CHOICE%"=="YES" goto INSTALL_PYTHON
if /i "%USER_CHOICE%"=="Д" goto INSTALL_PYTHON
if /i "%USER_CHOICE%"=="ДА" goto INSTALL_PYTHON

echo.
echo [!] Отказ от установки. Программа завершает работу.
timeout /t 3 >nul
exit /b

:INSTALL_PYTHON
echo.
echo [1/2] Загрузка официального инсталлятора Python...
powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.14.0/python-3.14.0-amd64.exe' -OutFile '%TEMP%\python_installer.exe'"

if not exist "%TEMP%\python_installer.exe" (
echo.
echo [!] Ошибка скачивания. Проверьте интернет-соединение.
pause
exit /b
)

echo [2/2] Установка Python (добавление в систему)...
"%TEMP%\python_installer.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
del "%TEMP%\python_installer.exe"

echo.
echo [✓] Python успешно установлен!
echo.

:: Обновляем пути в текущей сессии для первого запуска
set "PATH=%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;%PATH%"

:RUN_CHECKER
python checker.py
goto END

:RUN_CHECKER_PY
py checker.py
goto END

:END
if %errorlevel% neq 0 (
echo.
echo [!] Программа завершилась с ошибкой.
pause
)