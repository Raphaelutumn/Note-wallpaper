"""
备忘录壁纸引擎
- 将事件网格渲染为 Windows 桌面壁纸
- 运行本地 HTTP 服务，供 HTML 编辑器读写事件
- 事件变更后自动刷新壁纸
- 开机自启：运行 install_startup.bat
"""
import json
import os
import sys
import time
import ctypes
import threading
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from io import BytesIO
from urllib.parse import urlparse, parse_qs

from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ==================== CONFIG ====================
PORT = 8899
APP_DIR = Path(os.environ.get('APPDATA', os.path.expanduser('~'))) / 'memo-wallpaper'
APP_DIR.mkdir(parents=True, exist_ok=True)
DATA_FILE = APP_DIR / 'events.json'
WALLPAPER_FILE = APP_DIR / 'wallpaper.bmp'  # BMP 格式兼容性最好
PID_FILE = APP_DIR / 'engine.pid'
HTML_FILE = Path(__file__).parent / 'memo-wallpaper.html'

SCORE_MIN, SCORE_MAX = 2, 40
COLOR_MAP = {
    'red':   {'fill': (213, 96, 103),  'glow': (213, 96, 103, 100)},
    'blue':  {'fill': (97, 166, 226),  'glow': (97, 166, 226, 100)},
    'green': {'fill': (89, 197, 112),  'glow': (89, 197, 112, 100)},
    'white': {'fill': (197, 193, 187), 'glow': (197, 193, 187, 50)},
}

FONT_PATHS = [
    'C:/Windows/Fonts/msyh.ttc',
    'C:/Windows/Fonts/msyhbd.ttc',
    'C:/Windows/Fonts/simhei.ttf',
    'C:/Windows/Fonts/simsun.ttc',
    'C:/Windows/Fonts/seguiemj.ttf',
]

ELEGANT_FONT_PATHS = [
    'C:/Windows/Fonts/STKAITI.TTF',   # 华文楷体
    'C:/Windows/Fonts/simkai.ttf',     # 楷体
    'C:/Windows/Fonts/STFANGSO.TTF',   # 华文仿宋
    'C:/Windows/Fonts/simfang.ttf',    # 仿宋
    'C:/Windows/Fonts/STXINGKA.TTF',   # 华文行楷
]


def get_color(total):
    if total >= 28: return 'red'
    if total >= 20: return 'blue'
    if total >= 12: return 'green'
    return 'white'


def load_font(size, elegant=False):
    paths = ELEGANT_FONT_PATHS + FONT_PATHS if elegant else FONT_PATHS
    for fp in paths:
        try:
            return ImageFont.truetype(fp, size)
        except Exception:
            continue
    return ImageFont.load_default()


# ==================== EVENT STORE ====================
class EventStore:
    def __init__(self):
        self.events = []
        self._lock = threading.Lock()
        self.load()

    def load(self):
        try:
            if DATA_FILE.exists():
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    self.events = json.load(f)
        except Exception:
            self.events = []
        self.events.sort(key=lambda e: e.get('createdAt', 0))

    def save(self):
        with self._lock:
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.events, f, ensure_ascii=False, indent=2)

    def get_all(self):
        return list(self.events)

    def add(self, ev):
        ev['id'] = str(int(time.time() * 1000)) + str(int(time.perf_counter_ns() % 100000))
        ev['createdAt'] = int(time.time() * 1000)
        self.events.append(ev)
        self.events.sort(key=lambda e: e.get('createdAt', 0))
        self.save()
        return ev

    def update(self, ev_id, data):
        for ev in self.events:
            if ev['id'] == ev_id:
                ev.update(data)
                ev['id'] = ev_id
                self.events.sort(key=lambda e: e.get('createdAt', 0))
                self.save()
                return ev
        return None

    def delete(self, ev_id):
        before = len(self.events)
        self.events = [e for e in self.events if e['id'] != ev_id]
        if len(self.events) != before:
            self.save()
            return True
        return False

    def clear(self):
        self.events = []
        self.save()

    def import_all(self, events):
        for ev in events:
            if 'id' not in ev:
                ev['id'] = str(int(time.time() * 1000))
            if 'createdAt' not in ev:
                ev['createdAt'] = int(time.time() * 1000)
        self.events = events
        self.events.sort(key=lambda e: e.get('createdAt', 0))
        self.save()


# ==================== WALLPAPER RENDERER ====================
class WallpaperRenderer:
    def __init__(self, store):
        self.store = store
        self.sw, self.sh = self._get_screen_size()

    def _get_screen_size(self):
        try:
            # Enable high-DPI awareness to get true physical resolution
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PerMonitorV2
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass
        try:
            user32 = ctypes.windll.user32
            sw = user32.GetSystemMetrics(0)
            sh = user32.GetSystemMetrics(1)
            return max(sw, 800), max(sh, 600)
        except Exception:
            return 1920, 1080

    def render(self):
        sw, sh = self.sw, self.sh
        RENDER_SCALE = 4
        UI_SCALE = 1.55
        S = RENDER_SCALE * UI_SCALE
        RS = RENDER_SCALE

        # 与 HTML 完全一致的色板
        BG      = (255, 252, 245)  # #fffcf5
        GRID_C  = (228, 223, 210)  # #e4dfd2
        AXIS_C  = (212, 203, 168)  # #d4cba8
        LABEL_C = (200, 176, 96)   # #c8b060
        GOLD    = (180, 140, 50)   # #b48c32 — 轴标题/金边框
        GOLD_S  = (210, 190, 145)  # #d2be91 — 标题阴影/提示
        GOLD_M  = (170, 120, 35)   # #aa7823 — 标题主色
        CLOCK_T = (180, 140, 50)   # #b48c32 — 时间
        CLOCK_D = (200, 170, 100)  # #c8aa64 — 日期

        rsw = int(sw * RS)
        rsh = int(sh * RS)
        img = Image.new('RGB', (rsw, rsh), BG)
        draw = ImageDraw.Draw(img)

        # Margins
        margin = {
            'top': int(50 * S), 'right': int(30 * S),
            'bottom': int(60 * S), 'left': int(70 * S)
        }
        grid_w = rsw - margin['left'] - margin['right']
        grid_h = rsh - margin['top'] - margin['bottom']
        cell_size = min(grid_w, grid_h) // 19
        grid_w = cell_size * 19
        grid_h = cell_size * 19
        left = margin['left']
        top = margin['top']
        right = left + grid_w
        bottom = top + grid_h

        # Grid lines — #e4dfd2
        grid_lw = max(1, int(RS * 0.8))
        for i in range(20):
            x = left + i * cell_size
            y = top + i * cell_size
            draw.line([(x, top), (x, bottom)], fill=GRID_C, width=grid_lw)
            draw.line([(left, y), (right, y)], fill=GRID_C, width=grid_lw)

        # Axes — #d4cba8
        axis_lw = max(2, int(RS * 1.5))
        draw.line([(left, top), (left, bottom)], fill=AXIS_C, width=axis_lw)
        draw.line([(left, bottom), (right, bottom)], fill=AXIS_C, width=axis_lw)

        # Arrow heads — #d4cba8
        a_tip = int(10 * S)
        a_hw = int(6 * S)
        a_bo = int(4 * S)
        draw.polygon([(left, top - a_tip), (left - a_hw, top + a_bo), (left + a_hw, top + a_bo)], fill=AXIS_C)
        draw.polygon([(right + a_tip, bottom), (right - a_bo, bottom - a_hw), (right - a_bo, bottom + a_hw)], fill=AXIS_C)

        # Fonts
        font_label = load_font(max(9, int(cell_size * UI_SCALE / 4)))
        font_title = load_font(max(11, int(cell_size * UI_SCALE / 3)))
        font_badge = load_font(max(8, int(cell_size * UI_SCALE / 5)))

        # Axis numbers — #c8b060, placed at grid line intersections
        for i in range(1, 21):
            if i % 2 == 1 and i not in (1, 20):
                continue
            x = left + (i - 1) * cell_size
            draw.text((x, bottom + int(10 * S)), str(i), fill=LABEL_C, font=font_label, anchor='mt')
            y = top + (20 - i) * cell_size
            draw.text((left - int(12 * S), y), str(i), fill=LABEL_C, font=font_label, anchor='rm')

        # Axis titles — #b48c32
        draw.text((left + grid_w // 2, bottom + int(45 * S)), '紧迫度 →', fill=GOLD, font=font_title, anchor='mm')
        txt_img = Image.new('RGBA', (int(200 * S), int(30 * S)), (0, 0, 0, 0))
        txt_draw = ImageDraw.Draw(txt_img)
        txt_draw.text((int(100 * S), int(15 * S)), '重要度 →', fill=GOLD, font=font_title, anchor='mm')
        txt_img = txt_img.rotate(90, expand=True)
        img.paste(txt_img, (int(6 * S), top + grid_h // 2 - txt_img.height // 2), txt_img)

        # Title — #d2be91 shadow + #aa7823 main
        title_font = load_font(int(28 * S))
        draw.text((int(29 * S), int(13 * S)), '事 件 备 忘', fill=GOLD_S, font=title_font, anchor='lt')
        draw.text((int(28 * S), int(12 * S)), '事 件 备 忘', fill=GOLD_M, font=title_font, anchor='lt')

        # Hint — #d2be91
        hint_font = load_font(int(11 * S))
        hint_text = '双击桌面「备忘录编辑器」快捷方式  或  浏览器打开 http://127.0.0.1:8899'
        draw.text((rsw - int(30 * S), rsh - int(16 * S)), hint_text, fill=GOLD_S, font=hint_font, anchor='rb')

        # Clock — minute resolution (refreshed every 60s by background thread)
        now = time.localtime()
        time_str = time.strftime('%H:%M', now)
        date_str = time.strftime('%Y-%m-%d %A', now)
        clock_font_lg = load_font(int(16 * S))
        clock_font_sm = load_font(int(12 * S))
        draw.text((rsw - int(30 * S), int(12 * S)), time_str, fill=CLOCK_T, font=clock_font_lg, anchor='rt')
        draw.text((rsw - int(30 * S), int(34 * S)), date_str, fill=CLOCK_D, font=clock_font_sm, anchor='rt')

        # Events
        events = self.store.get_all()
        min_cell = int(15 * RS)
        if cell_size >= min_cell and events:
            pos_map = {}
            for ev in events:
                key = (ev.get('urgency', 10), ev.get('importance', 10))
                pos_map.setdefault(key, []).append(ev)

            dot_radius = max(int(8 * S), min(int(18 * S), int(cell_size * UI_SCALE / 3)))
            font_dot = load_font(max(int(20 * S), int(dot_radius * 1.1)), elegant=True)

            GOLD_RGB = (180, 140, 50)

            for (u, i), evs in pos_map.items():
                cx = left + (u - 1) * cell_size
                cy = top + (20 - i) * cell_size
                count = len(evs)

                sorted_evs = sorted(evs, key=lambda e: e.get('createdAt', 0), reverse=True)

                for idx, ev in enumerate(sorted_evs):
                    offset = (idx - (count - 1) / 2) * max(2, cell_size // 30) if count > 1 else 0
                    dx = int(offset)
                    dy = int(offset)

                    total = ev.get('urgency', 10) + ev.get('importance', 10)
                    color_name = get_color(total)
                    color = COLOR_MAP[color_name]

                    # Dot body — solid color
                    r = dot_radius
                    draw.ellipse([cx + dx - r, cy + dy - r, cx + dx + r, cy + dy + r],
                                 fill=color['fill'])

                    # Gold border
                    border_w = max(int(2 * RS), cell_size // 40)
                    draw.ellipse([cx + dx - r, cy + dy - r, cx + dx + r, cy + dy + r],
                                 outline=GOLD_RGB, width=border_w)

                    # Abbreviation — pure black, 1-3 chars single line, 4-6 split into two lines, unified font
                    abbr = ev.get('abbreviation', '').strip()
                    if abbr:
                        if len(abbr) <= 3:
                            draw.text((cx + dx, cy + dy), abbr, fill=(0, 0, 0),
                                      font=font_dot, anchor='mm')
                            draw.text((cx + dx + 1, cy + dy), abbr, fill=(0, 0, 0),
                                      font=font_dot, anchor='mm')
                        else:
                            split = (len(abbr) + 1) // 2
                            line1, line2 = abbr[:split], abbr[split:]
                            line_h = int(dot_radius * 0.50)
                            draw.text((cx + dx, cy + dy - line_h), line1, fill=(0, 0, 0),
                                      font=font_dot, anchor='mm')
                            draw.text((cx + dx + 1, cy + dy - line_h), line1, fill=(0, 0, 0),
                                      font=font_dot, anchor='mm')
                            draw.text((cx + dx, cy + dy + line_h), line2, fill=(0, 0, 0),
                                      font=font_dot, anchor='mm')
                            draw.text((cx + dx + 1, cy + dy + line_h), line2, fill=(0, 0, 0),
                                      font=font_dot, anchor='mm')

                # Overlap badge — gold
                if count > 1:
                    bx = cx + dot_radius + int(8 * S)
                    by = cy - dot_radius - int(8 * S)
                    badge_r = int(10 * S)
                    draw.ellipse([bx - badge_r, by - badge_r, bx + badge_r, by + badge_r],
                                 fill=(220, 180, 40), outline=GOLD_RGB, width=max(1, int(RS)))
                    draw.text((bx, by), str(count), fill=(255, 255, 255), font=font_badge, anchor='mm')

        # Downscale to physical resolution with high-quality filter
        img = img.resize((sw, sh), Image.LANCZOS)
        img.save(WALLPAPER_FILE, 'BMP')
        return WALLPAPER_FILE

    def set_wallpaper(self, image_path):
        path = str(image_path)
        SPI_SETDESKWALLPAPER = 20
        SPIF_UPDATEINIFILE = 1
        SPIF_SENDCHANGE = 2
        ctypes.windll.user32.SystemParametersInfoW(
            SPI_SETDESKWALLPAPER, 0, path, SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
        )

    def apply(self):
        """Render and set wallpaper."""
        try:
            path = self.render()
            self.set_wallpaper(path)
            return True
        except Exception:
            traceback.print_exc()
            return False


def clock_refresh_thread(renderer):
    """每分钟刷新壁纸以更新时钟显示"""
    while True:
        time.sleep(60)
        try:
            renderer.apply()
        except Exception:
            pass


# ==================== HTTP SERVER ====================
class RequestHandler(BaseHTTPRequestHandler):
    store: EventStore = None
    renderer: WallpaperRenderer = None

    def log_message(self, format, *args):
        pass  # Suppress logs

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        return json.loads(self.rfile.read(length)) if length else {}

    def _serve_file(self, path, content_type):
        try:
            with open(path, 'rb') as f:
                data = f.read()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', len(data))
            self.end_headers()
            self.wfile.write(data)
        except FileNotFoundError:
            self.send_error(404)

    @staticmethod
    def _delayed_shutdown():
        time.sleep(0.5)
        PID_FILE.unlink(missing_ok=True)
        os._exit(0)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/':
            self._serve_file(HTML_FILE, 'text/html; charset=utf-8')
        elif path == '/api/events':
            self._send_json(self.store.get_all())
        elif path == '/api/ping':
            self._send_json({'status': 'ok'})
        else:
            # Serve static files next to HTML
            fp = HTML_FILE.parent / path.lstrip('/')
            if fp.exists():
                ct = 'text/html' if fp.suffix == '.html' else 'application/octet-stream'
                self._serve_file(fp, ct)
            else:
                self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == '/api/events':
            data = self._read_body()
            if isinstance(data, list):
                self.store.import_all(data)
                self._send_json({'ok': True, 'count': len(data)})
            else:
                ev = self.store.add(data)
                self.renderer.apply()
                self._send_json(ev, 201)
        elif path == '/api/refresh':
            self.renderer.apply()
            self._send_json({'ok': True})
        elif path == '/api/shutdown':
            self._send_json({'ok': True, 'message': '引擎正在关闭...'})
            threading.Thread(target=self._delayed_shutdown, daemon=True).start()
        else:
            self.send_error(404)

    def do_PUT(self):
        path = urlparse(self.path).path
        if path.startswith('/api/events/'):
            ev_id = path.split('/')[-1]
            data = self._read_body()
            result = self.store.update(ev_id, data)
            if result:
                self.renderer.apply()
                self._send_json(result)
            else:
                self._send_json({'error': 'not found'}, 404)
        else:
            self.send_error(404)

    def do_DELETE(self):
        path = urlparse(self.path).path
        if path.startswith('/api/events/'):
            ev_id = path.split('/')[-1]
            if self.store.delete(ev_id):
                self.renderer.apply()
                self._send_json({'ok': True})
            else:
                self._send_json({'error': 'not found'}, 404)
        else:
            self.send_error(404)


# ==================== MAIN ====================
def find_browser():
    import shutil
    candidates = [
        os.path.expandvars(r'%ProgramFiles%\Google\Chrome\Application\chrome.exe'),
        os.path.expandvars(r'%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe'),
        os.path.expandvars(r'%LocalAppData%\Google\Chrome\Application\chrome.exe'),
        os.path.expandvars(r'%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe'),
        shutil.which('chrome'), shutil.which('msedge'), shutil.which('brave'),
    ]
    for p in candidates:
        if p and os.path.exists(p):
            return p
    return None


def open_editor():
    """用浏览器打开 HTML 编辑器，优先以 app 模式（无边框）打开"""
    browser = find_browser()
    file_url = 'file:///' + str(HTML_FILE).replace('\\', '/')
    if browser:
        subprocess.Popen(
            [browser, f'--app={file_url}', '--window-size=1000,750', '--window-position=50,50'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    else:
        os.startfile(str(HTML_FILE))


def create_shortcut():
    """在桌面创建编辑器快捷方式"""
    try:
        import pythoncom
        from win32com.client import Dispatch
        desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
        shortcut_path = os.path.join(desktop, '备忘录编辑器.lnk')
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.TargetPath = str(HTML_FILE)
        shortcut.WorkingDirectory = str(HTML_FILE.parent)
        shortcut.Description = '备忘录编辑器 - 双击编辑事件'
        shortcut.IconLocation = 'shell32.dll,44'
        shortcut.Save()
        print(f'桌面快捷方式已创建: {shortcut_path}')
    except Exception:
        pass  # 非关键，pywin32 可能未安装


def main():
    # Prevent multiple instances
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if s.connect_ex(('127.0.0.1', PORT)) == 0:
        s.close()
        print(f'备忘录壁纸引擎已在运行 (端口 {PORT} 已占用)，退出。')
        sys.exit(0)
    s.close()

    # Write PID file
    PID_FILE.write_text(str(os.getpid()))

    print(f'数据目录: {APP_DIR}')
    print(f'端口: {PORT}')

    store = EventStore()
    renderer = WallpaperRenderer(store)

    # Start clock refresh thread
    threading.Thread(target=clock_refresh_thread, args=(renderer,), daemon=True).start()

    # Force initial wallpaper
    print('正在生成壁纸...')
    ok = renderer.apply()
    if ok:
        print('壁纸已设置。若未生效，请右键桌面→个性化→背景→选择图片。')
    else:
        print('壁纸设置失败，请检查权限。')

    # Auto-open editor in browser
    print('正在打开编辑器...')
    threading.Thread(target=open_editor, daemon=True).start()

    # Create desktop shortcut for next time
    create_shortcut()

    # HTTP server
    RequestHandler.store = store
    RequestHandler.renderer = renderer

    server = HTTPServer(('127.0.0.1', PORT), RequestHandler)
    print(f'服务已启动 http://127.0.0.1:{PORT}')
    print('编辑器顶部显示 ●绿色 即表示壁纸联动正常。')
    print('按 Ctrl+C 退出。')

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n正在退出...')
        server.shutdown()
    finally:
        PID_FILE.unlink(missing_ok=True)


if __name__ == '__main__':
    import subprocess
    main()
