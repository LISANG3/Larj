# Larj

Larj 是一个轻量级的 Windows 桌面效率工具，提供快速文件搜索、应用启动和插件扩展功能。

## 功能特性

- **全局热键触发**: 鼠标侧键 (XButton1) 或键盘快捷键 (Ctrl+Space)
- **快速文件搜索**: 集成 Everything 实现即时文件搜索
- **应用快捷启动**: 一键启动常用应用，自动按使用频率排序
- **插件系统**: 可扩展的插件架构，支持自定义功能
- **轻量高效**: 内存占用 < 50MB，搜索响应 < 200ms

## 目录

- [安装](#安装)
- [使用方法](#使用方法)
- [项目结构](#项目结构)
- [技术架构](#技术架构)
- [插件开发](#插件开发)
- [配置说明](#配置说明)
- [常见问题](#常见问题)
- [贡献指南](#贡献指南)

## 安装

### 系统要求

- Windows 10/11
- Python 3.8+

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/LISANG3/Larj.git
cd Larj
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **下载 Everything**
   - 访问 https://www.voidtools.com/downloads/
   - 下载 Command-line Interface (es.exe)
   - 将 `es.exe` 和 `Everything.exe` 放入 `everything/` 目录

4. **运行程序**
```bash
python main.py
# 或使用启动脚本
launch.bat
```

## 使用方法

### 触发面板

- **鼠标**: 按下鼠标侧键 (XButton1)
- **键盘**: 按 Ctrl+Space

### 搜索文件

1. 触发面板后，在搜索框输入关键词
2. 搜索结果即时显示
3. 双击结果打开文件

### 管理应用

1. 点击应用图标启动应用
2. 点击 "+ 添加应用" 添加新应用
3. 应用自动按使用频率排序

## 项目结构

```
Larj/
├── config/                 # 配置文件目录
│   ├── settings.json       # 主配置
│   ├── apps.json          # 应用数据
│   └── plugins.json       # 插件配置
│
├── everything/            # Everything 搜索引擎
│   ├── es.exe            # 命令行工具 (需下载)
│   └── Everything.exe    # 主程序 (需下载)
│
├── plugins/              # 插件目录
│   ├── calculator.py     # 计算器插件
│   ├── notepad.py        # 记事本插件
│   └── mtran_server/     # MTranServer 插件（目录化插件）
│       └── __init__.py
│
├── src/                  # 源代码
│   ├── core/             # 核心模块
│   │   ├── main_controller.py      # 主控制器
│   │   ├── config_manager.py       # 配置管理
│   │   ├── hotkey_listener.py      # 热键监听
│   │   ├── window_manager.py       # 窗口管理
│   │   ├── search_engine.py        # 搜索引擎
│   │   ├── application_manager.py  # 应用管理
│   │   └── plugin_system.py        # 插件系统
│   │
│   └── ui/               # UI 组件
│       └── main_panel.py # 主面板
│
├── main.py               # 程序入口
├── launch.bat            # Windows 启动脚本
└── requirements.txt      # Python 依赖
```

## 技术架构

### 架构模式

采用**事件驱动架构**，模块间通过信号-槽机制通信，实现松耦合。

```
┌──────────────────────────────────────────────────────────┐
│                     主控制器                               │
│            (协调器 + 事件分发中心)                         │
├──────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │热键监听器│  │窗口管理器│  │搜索引擎  │  │插件系统│  │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘  │
│       │             │             │             │        │
└───────┼─────────────┼─────────────┼─────────────┼────────┘
        │             │             │             │
        ▼             ▼             ▼             ▼
  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐
  │配置管理器│  │应用管理器│  │配置管理器│  │配置存储│
  └──────────┘  └──────────┘  └──────────┘  └────────┘
```

### 核心模块

| 模块 | 职责 |
|-----|------|
| MainController | 事件总线、模块协调、生命周期管理 |
| ConfigManager | 配置读写、验证、热重载 |
| HotkeyListener | 全局热键监听、防抖处理 |
| WindowManager | 窗口显示/隐藏、位置计算、动画 |
| SearchEngine | Everything 集成、异步搜索、结果缓存 |
| ApplicationManager | 应用管理、启动、使用统计 |
| PluginSystem | 插件发现、加载、生命周期管理 |

### 数据流

**热键触发流程:**
```
用户按热键 → HotkeyListener 捕获 → MainController 处理 
→ WindowManager 显示窗口 → MainPanel 获得焦点
```

**搜索流程:**
```
用户输入 → 防抖(300ms) → SearchEngine 异步搜索 
→ 调用 es.exe → 解析 CSV 结果 → 更新界面
```

## 插件开发

### 创建插件

1. 在 `plugins/` 目录创建 `.py` 文件或插件目录（目录内需包含 `__init__.py`）
2. 继承 `PluginBase` 类
3. 实现必需方法

### 插件接口

```python
from src.core.plugin_system import PluginBase

class MyPlugin(PluginBase):
    def get_name(self) -> str:
        return "My Plugin"
    
    def get_icon(self) -> str:
        return "icon_name"
    
    def get_info(self) -> dict:
        return {
            "name": "My Plugin",
            "version": "1.0.0",
            "author": "Your Name",
            "description": "插件描述"
        }
    
    def handle_click(self):
        # 点击时执行的逻辑
        pass
    
    def on_load(self):
        # 可选：加载时调用
        pass
    
    def on_unload(self):
        # 可选：卸载时调用
        pass
```

### 启用插件

在 `config/settings.json` 中配置：
```json
{
  "plugin": {
    "enabled_plugins": ["my_plugin"]
  }
}
```

### 开发建议

- `handle_click()` 中避免长时间阻塞操作
- 捕获异常并记录，避免影响主程序
- 仅使用可信输入，避免安全风险

## 配置说明

配置文件位于 `config/` 目录：

### settings.json

```json
{
  "hotkey": {
    "trigger_key": "XButton1",
    "fallback_keys": ["Ctrl+Space"],
    "enabled": true
  },
  "window": {
    "width": 600,
    "height": 400,
    "opacity": 95,
    "follow_mouse": true
  },
  "search": {
    "max_results": 50,
    "debounce_ms": 300,
    "cache_timeout": 60
  },
  "application": {
    "auto_sort": true,
    "sort_by": "usage"
  },
  "plugin": {
    "enabled_plugins": []
  }
}
```

### apps.json

```json
{
  "apps": [
    {
      "id": "uuid",
      "name": "应用名称",
      "path": "C:\\path\\to\\app.exe",
      "usage_count": 0
    }
  ]
}
```

## 常见问题

### 热键不响应
- 检查是否有其他程序占用相同热键
- 尝试以管理员权限运行
- 更改热键配置

### 搜索不工作
- 确保 `everything/es.exe` 存在
- 确保 Everything 正在运行
- 检查日志文件 `logs/larj.log`

### 窗口不显示
- 检查 PyQt5 是否正确安装
- 查看日志了解错误详情

### 插件加载失败
- 检查插件是否正确实现所有必需方法
- 查看日志了解加载错误

### 依赖安装失败
```bash
# 升级 pip
python -m pip install --upgrade pip

# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 贡献指南

### 报告 Bug

1. 在 [Issues](https://github.com/LISANG3/Larj/issues) 搜索是否已有类似问题
2. 创建新 Issue，包含：
   - 复现步骤
   - 期望行为 vs 实际行为
   - 系统信息
   - 相关日志

### 提交代码

1. Fork 项目并克隆
2. 创建分支: `git checkout -b feature/your-feature`
3. 遵循 PEP 8 代码规范
4. 提交: `git commit -m "feat: 描述"`
5. 推送并创建 Pull Request

### 提交信息格式

- `feat:` 新功能
- `fix:` Bug 修复
- `docs:` 文档更新
- `refactor:` 代码重构
- `test:` 测试相关

## 许可证

MIT License

## 致谢

- [Everything](https://www.voidtools.com/) - 文件搜索引擎
- [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) - GUI 框架
- [pynput](https://github.com/moses-palmer/pynput) - 输入监听
