# Get It — 每日提醒应用 (PyQt6)

精致的桌面日程提醒工具。指定时间弹出提醒窗口，支持延后、自定义铃声、角色装扮。

## 快速开始

```bash
pip install PyQt6 pygame numpy Pillow
python Get_It.pyw              # 正常启动
python Get_It.pyw --minimized  # 启动后最小化到托盘
```

**单文件即用** — `Get_It.pyw` 包含全部功能，双击运行。`daily_reminder_data.json` 首次运行自动创建，与旧版 tkinter 数据兼容。

## 功能

| 功能 | 说明 |
|---|---|
| 日程管理 | 添加/编辑/删除每日提醒，精确到分钟 |
| 提醒弹窗 | 右下角浅色主题弹窗，淡入淡出动画，角色头像 + 名称 |
| 延后 (Snooze) | 延后 N 分钟再次提醒，**不改变原始日程时间** |
| 内置铃声 | 7 种程序化合成铃声（叮咚声/风铃声/蜂鸣声/警报声/通知音/钢琴音/合成器） |
| 自定义铃声 | mp3 / wav / ogg |
| 角色装扮 | 名称、颜色、字体、圆形头像（内置裁剪工具） |
| 系统托盘 | 关闭最小化到托盘，双击恢复 |
| 单实例 | 重复启动静默唤醒已有窗口，不弹提示 |
| 休眠补提醒 | 休眠/关闭期间错过的日程，恢复后自动补提醒（可开关） |

## 项目结构

```
├── Get_It.pyw                # ★ 单文件版，直接运行
├── main.py                   # 模块化入口
├── app.py                    # 主窗口 + 提醒线程 + 系统托盘
├── ringtone.py               # 铃声生成器（numpy + pygame）
├── models.py                 # Schedule / AppSettings 数据模型
├── data_manager.py           # JSON 持久化
├── icon.ico                  # 应用图标
├── widgets/
│   ├── schedule_editor.py    # 日程编辑表单
│   ├── schedule_list.py      # 日程列表
│   └── avatar_cropper.py     # 圆形头像裁剪
├── dialogs/
│   ├── notification.py       # 提醒弹窗（淡入淡出）
│   └── settings.py           # 设置对话框
├── tests/
│   ├── test_models.py
│   ├── test_data_manager.py
│   └── test_snooze.py        # 延后 Bug 修复验证
└── requirements.txt
```

## 测试

```bash
pytest tests/ -v    # 15 个测试
```

## Bug 修复：延后不改时间

| | 旧行为 (tkinter) | 新行为 (PyQt6) |
|---|---|---|
| 点击"延后" | `schedule.hour/minute` 被 `now + N` 永久覆盖 | 仅设 `snoozed_until`，原始时间不变 |
| 到期后 | 日程时间已变，无法恢复 | `snoozed_until` 到期自动恢复原始时间触发 |

## 技术栈

| 组件 | 原版 (tkinter) | PyQt6 版 |
|---|---|---|
| GUI | tkinter | PyQt6 |
| 音频 | pygame | pygame |
| 铃声合成 | numpy | numpy |
| 图像 | Pillow | Pillow |
| 托盘 | pystray | QSystemTrayIcon |
| 后台线程 | threading.Thread | QThread + pyqtSignal |
| 动画 | after() 循环 | QPropertyAnimation |
| 单实例 | — | QSharedMemory + QLocalServer |
