# 备忘录壁纸 — 部署与使用教程

---

## 零基础篇（完全没接触过编程）

### 第一步：安装 Python

1. 打开 https://www.python.org/downloads/
2. 点击黄色 **Download Python** 按钮下载安装包
3. 双击安装包，**务必勾选底部的 "Add Python to PATH"**，然后点 **Install Now**
4. 验证：按 `Win + R`，输入 `cmd` 回车，在黑色窗口输入 `python --version`，显示版本号即成功

### 第二步：下载项目

1. 打开 https://github.com/Raphaelutumn/Note-wallpaper
2. 点击绿色 **Code** 按钮 → **Download ZIP**
3. 将下载的 zip 解压到桌面（或任意位置）

### 第三步：安装依赖并启动

1. 按 `Win + R`，输入 `cmd` 回车
2. 进入项目目录（把 `你的用户名` 换成你电脑的用户名）：

```
cd C:\Users\你的用户名\Desktop\Note-wallpaper
```

3. 安装依赖：

```
pip install -r requirements.txt
```

4. 启动：

```
python wallpaper_engine.py
```

桌面壁纸自动变成四象限网格，浏览器弹出编辑器，即可使用。

### 第四步（可选）：开机自动启动

双击项目文件夹里的 `install_startup.bat`。以后每次开机自动运行。

### 日常使用

- 双击桌面的「备忘录编辑器」快捷方式，或浏览器打开 `http://127.0.0.1:8899`
- **添加**：点击「+ 添加新事件」→ 填缩写、紧迫度(1-20)、重要度(1-20) → 保存
- **修改**：点击网格上的圆点 → 右侧面板点「编辑」
- **删除**：点击网格上的圆点 → 右侧面板点「删除」
- **备份**：面板底部「导出 JSON」，下载备份文件到本地
- **恢复**：面板底部「导入 JSON」，选择之前导出的文件

### 关闭与重启

- 关闭：在命令行窗口按 `Ctrl + C`
- 重启：双击 `restart_wallpaper.bat`

---

## 有基础篇（熟悉 GitHub 和 Python）

### 部署

```bash
git clone https://github.com/Raphaelutumn/Note-wallpaper.git
cd Note-wallpaper
pip install -r requirements.txt
python wallpaper_engine.py
```

浏览器自动打开编辑器，桌面壁纸同步渲染。

### 开机自启

```bash
install_startup.bat
```

卸载自启：

```bash
uninstall_startup.bat
```

### 其他启动方式

| 方式 | 命令/文件 | 说明 |
|------|-----------|------|
| 完整模式 | `python wallpaper_engine.py` | HTTP 服务 + 壁纸渲染 + 编辑器 |
| 轻量模式 | `python launch_wallpaper.py` | 仅无边框桌面窗口，不渲染壁纸 |
| 静默启动 | 双击 `memo_wallpaper_launcher.vbs` | 后台启动引擎，无命令行窗口 |
| 仅编辑器 | 双击 `memo-wallpaper.html` | 浏览器打开，离线模式 |

---

## 使用指南

### 编辑器

- 访问地址：`http://127.0.0.1:8899`
- 顶部状态指示：●绿色 = 引擎已连接，○黄色 = 离线模式
- 点击「🖼 刷新壁纸」手动触发壁纸重绘

### 事件管理

- **添加**：点击「+ 添加新事件」，填写信息，保存
- **编辑**：点击网格圆点或列表中的「编辑」按钮
- **删除**：点击列表中的「删除」按钮，或右键圆点快捷操作
- **查看**：鼠标悬停圆点查看详情；重叠圆点会弹出选择列表
- **清空**：面板底部「清空全部」

### 四象限颜色规则

| 总分 | 颜色 | 含义 |
|------|------|------|
| ≥ 28 | 红色 | 高紧迫 + 高重要，立即处理 |
| 20-27 | 蓝色 | 中等优先级 |
| 12-19 | 绿色 | 较低优先级 |
| 2-11 | 白色 | 闲时处理 |

### 数据管理

- 数据存储在 `%APPDATA%/memo-wallpaper/events.json`
- 浏览器端同步缓存于 `localStorage`
- 导出/导入 JSON 可实现备份和迁移
- 数据完全本地，不联网

---

## 架构

```
memo-wallpaper.html    ← 前端编辑器（原生 JS，无框架）
wallpaper_engine.py    ← 后端引擎（HTTP Server + PIL 渲染 + 设壁纸）
launch_wallpaper.py    ← 无边框桌面窗口启动器
```

- 前端与后端通过 `127.0.0.1:8899` REST API 通信
- 引擎用 PIL 将事件渲染为 BMP，通过 Win32 API 设为桌面壁纸
- 每分钟自动刷新壁纸以更新时钟显示
- 引擎未运行时编辑器以离线模式运行（仅 localStorage）

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/ping` | 健康检查 |
| GET | `/api/events` | 获取全部事件 |
| POST | `/api/events` | 添加事件 |
| PUT | `/api/events/:id` | 更新事件 |
| DELETE | `/api/events/:id` | 删除事件 |
| POST | `/api/refresh` | 手动刷新壁纸 |
| POST | `/api/shutdown` | 关闭引擎 |

---

## 依赖

- Python 3.11+
- Pillow ≥ 9.0.0
- pywin32 ≥ 300
- Chrome / Edge / Brave（无边框窗口模式需要）

---

## 常见问题

**Q: 壁纸没变？**
右键桌面 → 个性化 → 背景 → 选择图片，确认壁纸来源。或点编辑器的「🖼 刷新壁纸」。

**Q: 编辑器显示"离线模式"？**
引擎未运行，执行 `python wallpaper_engine.py` 启动。

**Q: 端口被占用？**
已有实例在运行。检查任务栏是否有 Python 进程，或重启电脑。

**Q: 怎么迁移到另一台电脑？**
导出 JSON → 拷贝项目文件夹 + JSON 文件到新电脑 → 导入 JSON。
