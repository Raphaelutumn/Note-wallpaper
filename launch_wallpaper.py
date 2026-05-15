"""
备忘录壁纸启动器
功能：以无边框桌面窗口方式运行 memo-wallpaper.html，模拟壁纸体验。
用法：双击此文件，或 python launch_wallpaper.py
退出：按 Alt+F4 或从任务栏关闭窗口。
"""
import subprocess
import os
import sys
import shutil

HTML_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'memo-wallpaper.html')


def find_browser():
    """按优先级查找可用的浏览器"""
    candidates = [
        # Chrome
        shutil.which('chrome'),
        shutil.which('google-chrome'),
        shutil.which('google-chrome-stable'),
        os.path.expandvars(r'%ProgramFiles%\Google\Chrome\Application\chrome.exe'),
        os.path.expandvars(r'%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe'),
        os.path.expandvars(r'%LocalAppData%\Google\Chrome\Application\chrome.exe'),
        # Edge (Chromium)
        shutil.which('msedge'),
        os.path.expandvars(r'%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe'),
        # Brave
        shutil.which('brave'),
        os.path.expandvars(r'%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe'),
        # Vivaldi
        shutil.which('vivaldi'),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None


def launch():
    browser = find_browser()
    if not browser:
        print("未找到 Chrome/Edge/Brave 浏览器，正在使用默认浏览器打开...")
        os.startfile(HTML_FILE)
        print("提示：用 Chrome 或 Edge 打开可获得更好的壁纸体验。")
        return

    # 获取屏幕尺寸
    try:
        import ctypes
        user32 = ctypes.windll.user32
        sw = user32.GetSystemMetrics(0)
        sh = user32.GetSystemMetrics(1)
    except Exception:
        sw, sh = 1920, 1080

    file_url = 'file:///' + HTML_FILE.replace('\\', '/')

    subprocess.Popen([
        browser,
        f'--app={file_url}',
        '--window-position=0,0',
        f'--window-size={sw},{sh}',
        '--disable-extensions',
        '--disable-sync',
    ],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL)

    print(f"备忘录壁纸已启动（{os.path.basename(browser)} 无边框模式）")
    print("按 Alt+F4 或从任务栏关闭窗口即可退出。")


if __name__ == '__main__':
    launch()
