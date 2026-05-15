@echo off
chcp 65001 >nul
title 重启备忘录壁纸
echo ===============================================
echo   备忘录壁纸 - 安全重启
echo ===============================================
echo.

set "PID_FILE=%APPDATA%\memo-wallpaper\engine.pid"
set "ENGINE=%~dp0wallpaper_engine.py"

REM Find pythonw.exe
set "PYTHONW="
if exist "%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe" set "PYTHONW=%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe"
if exist "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe" set "PYTHONW=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
if exist "%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe" set "PYTHONW=%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe"
if exist "C:\Python311\pythonw.exe" set "PYTHONW=C:\Python311\pythonw.exe"
if exist "C:\Python312\pythonw.exe" set "PYTHONW=C:\Python312\pythonw.exe"
if exist "C:\Python313\pythonw.exe" set "PYTHONW=C:\Python313\pythonw.exe"

if "%PYTHONW%"=="" (
    echo [错误] 未找到 pythonw.exe，请手动设置 PYTHONW 变量。
    pause
    exit /b 1
)

REM 1. 通过 API 优雅关闭
echo [1/4] 向引擎发送关闭请求...
curl -s -X POST http://127.0.0.1:8899/api/shutdown --connect-timeout 3 >nul 2>&1
if %errorlevel% equ 0 (
    echo       已发送关闭指令，等待引擎退出...
    timeout /t 2 /nobreak >nul
) else (
    echo       引擎未响应 API，尝试强制关闭...
)

REM 2. 通过 PID 文件精确关闭
if exist "%PID_FILE%" (
    set /p OLD_PID=<"%PID_FILE%"
    echo [2/4] 终止旧进程 PID: !OLD_PID!
    taskkill /f /pid !OLD_PID! >nul 2>&1
    if !errorlevel! equ 0 (
        echo       已终止
        del "%PID_FILE%" >nul 2>&1
    ) else (
        echo       进程已不存在
        del "%PID_FILE%" >nul 2>&1
    )
) else (
    echo [2/4] 无 PID 文件，跳过
)

REM 3. 兜底：确保端口释放
echo [3/4] 确保端口已释放...
:wait_port
timeout /t 1 /nobreak >nul
curl -s http://127.0.0.1:8899/api/ping --connect-timeout 2 >nul 2>&1
if !errorlevel! equ 0 (
    echo       端口仍被占用，再次强制清理...
    taskkill /f /fi "IMAGENAME eq pythonw.exe" >nul 2>&1
    taskkill /f /fi "IMAGENAME eq python.exe" >nul 2>&1
    timeout /t 2 /nobreak >nul
    goto wait_port
)
echo       端口已释放

REM 4. 启动新引擎
echo [4/4] 启动新引擎...
start "" "%PYTHONW%" "%ENGINE%"

echo.
echo ===============================================
echo   重启完成！新引擎已启动。
echo ===============================================
timeout /t 3 >nul
