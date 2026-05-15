@echo off
chcp 65001 >nul
echo ===============================================
echo   备忘录壁纸 - 安装开机自启
echo ===============================================
echo.

set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "PROJECT_DIR=%~dp0"

REM Find pythonw.exe
set "PYTHONW="
if exist "%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe" set "PYTHONW=%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe"
if exist "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe" set "PYTHONW=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
if exist "%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe" set "PYTHONW=%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe"
if exist "C:\Python311\pythonw.exe" set "PYTHONW=C:\Python311\pythonw.exe"
if exist "C:\Python312\pythonw.exe" set "PYTHONW=C:\Python312\pythonw.exe"
if exist "C:\Python313\pythonw.exe" set "PYTHONW=C:\Python313\pythonw.exe"

if "%PYTHONW%"=="" (
    echo [错误] 未找到 pythonw.exe
    echo 请手动编辑本文件中的 PYTHONW 变量指向 pythonw.exe 路径。
    pause
    exit /b 1
)

echo Python: %PYTHONW%
echo 项目:   %PROJECT_DIR%wallpaper_engine.py
echo 自启:   %STARTUP_DIR%
echo.

REM Use PowerShell to create a WSH shortcut (.lnk) that runs pythonw silently
powershell -Command ^
  "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%STARTUP_DIR%\memo-wallpaper.lnk'); $s.TargetPath = '%PYTHONW%'; $s.Arguments = '\"%PROJECT_DIR%wallpaper_engine.py\"'; $s.WorkingDirectory = '%PROJECT_DIR%'; $s.WindowStyle = 7; $s.Description = '备忘录壁纸引擎'; $s.Save()"

if exist "%STARTUP_DIR%\memo-wallpaper.lnk" (
    echo [成功] 开机自启已安装！
    echo.
    echo 下次开机时将自动启动壁纸引擎。
    echo 要立即启动，请双击运行: launch_wallpaper.py
    echo 要卸载自启，请运行: uninstall_startup.bat
) else (
    echo [失败] 无法创建快捷方式。
)

pause
