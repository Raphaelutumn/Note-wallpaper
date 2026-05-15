@echo off
chcp 65001 >nul
echo ===============================================
echo   备忘录壁纸 - 卸载开机自启
echo ===============================================
echo.

set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

if exist "%STARTUP_DIR%\memo-wallpaper.lnk" (
    del "%STARTUP_DIR%\memo-wallpaper.lnk"
    echo [成功] 开机自启已移除。
) else (
    echo 未找到开机自启项，无需操作。
)

echo.
echo 壁纸引擎进程仍在后台运行的话，请从任务管理器结束 pythonw.exe。
pause
