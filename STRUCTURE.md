# Larj 项目结构文档

## 目录结构

```
Larj/
├── config/                 # 配置文件目录
│   ├── settings.json       # 主配置文件
│   ├── apps.json          # 应用快捷方式数据
│   ├── plugins.json       # 插件配置
│   ├── *.example.json     # 配置文件示例
│   └── README.md          # 配置说明
│
├── everything/            # Everything 搜索引擎目录
│   ├── es.exe            # Everything 命令行工具（需自行下载）
│   └── README.md         # 下载和安装说明
│
├── plugins/              # 插件目录
│   ├── calculator.py     # 计算器插件示例
│   ├── notepad.py        # 记事本插件示例
│   └── __init__.py
│
├── src/                  # 源代码目录
│   ├── core/             # 核心模块
│   │   ├── main_controller.py      # 主控制器（事件总线）
│   │   ├── config_manager.py       # 配置管理器
│   │   ├── hotkey_listener.py      # 热键监听器
│   │   ├── window_manager.py       # 窗口管理器
│   │   ├── search_engine.py        # 搜索引擎
│   │   ├── application_manager.py  # 应用管理器
│   │   ├── plugin_system.py        # 插件系统
│   │   └── __init__.py
│   │
│   ├── ui/               # UI 组件
│   │   ├── main_panel.py # 主面板窗口
│   │   └── __init__.py
│   │
│   ├── plugins/          # 插件基础模块
│   │   └── __init__.py
│   │
│   └── utils/            # 工具模块
│       └── __init__.py
│
├── logs/                 # 日志目录（自动创建）
│   └── larj.log         # 应用日志
│
├── main.py               # 程序入口
├── launch.bat            # Windows 启动脚本
├── launch.sh             # Linux/Mac 启动脚本
├── requirements.txt      # Python 依赖
├── test_structure.py     # 结构测试脚本
├── README.md             # 项目说明
├── Larj_技术架构文档_v1.md  # 技术架构文档
└── .gitignore            # Git 忽略文件
```

## 核心模块说明

### 1. main_controller.py - 主控制器
- **职责**: 系统协调器和事件总线
- **功能**:
  - 管理所有模块的生命周期
  - 事件路由和分发
  - 模块间通信协调
  - 异常处理和恢复

### 2. config_manager.py - 配置管理器
- **职责**: 配置数据的统一存储和访问
- **功能**:
  - 读写 JSON 配置文件
  - 配置验证和默认值处理
  - 配置热重载
  - 应用数据管理

### 3. hotkey_listener.py - 热键监听器
- **职责**: 全局热键监听
- **功能**:
  - 监听鼠标侧键（XButton1/2）
  - 监听键盘快捷键
  - 热键防抖处理
  - 热键冲突检测

### 4. window_manager.py - 窗口管理器
- **职责**: 管理浮动面板窗口
- **功能**:
  - 窗口显示/隐藏控制
  - 窗口位置计算（跟随鼠标）
  - 窗口动画效果
  - 窗口属性管理

### 5. search_engine.py - 搜索引擎
- **职责**: 文件搜索功能
- **功能**:
  - 调用 Everything es.exe 执行搜索
  - 异步搜索处理
  - 搜索结果缓存
  - 实时搜索（防抖）

### 6. application_manager.py - 应用管理器
- **职责**: 应用快捷方式管理
- **功能**:
  - 应用增删改查
  - 应用启动和错误处理
  - 使用统计记录
  - 应用排序和分组

### 7. plugin_system.py - 插件系统
- **职责**: 插件管理和扩展
- **功能**:
  - 插件发现和加载
  - 插件生命周期管理
  - 插件隔离和异常处理
  - 插件权限控制

### 8. main_panel.py - 主面板 UI
- **职责**: 用户界面
- **功能**:
  - 搜索框和结果展示
  - 应用网格布局
  - 用户交互处理
  - 视图切换（应用/搜索结果）

## 数据流说明

### 热键触发流程
```
用户按下热键
    ↓
HotkeyListener 捕获事件
    ↓
MainController 处理事件
    ↓
WindowManager 显示窗口
    ↓
MainPanel 获得焦点
```

### 搜索流程
```
用户输入关键词
    ↓
MainPanel 触发搜索（防抖 300ms）
    ↓
SearchEngine 执行异步搜索
    ↓
调用 Everything es.exe
    ↓
解析 JSON 结果
    ↓
MainPanel 更新结果列表
```

### 应用启动流程
```
用户点击应用图标
    ↓
MainPanel 发送启动事件
    ↓
ApplicationManager 验证路径
    ↓
调用系统 API 启动应用
    ↓
更新使用统计
    ↓
WindowManager 隐藏窗口
```

## 配置文件格式

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
    "debounce_ms": 300
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
      "icon_path": "",
      "args": "",
      "usage_count": 0,
      "created_at": "2026-02-14T00:00:00",
      "last_used": null
    }
  ]
}
```

## 插件开发指南

### 创建插件

1. 在 `plugins/` 目录创建 `.py` 文件
2. 继承 `PluginBase` 类
3. 实现必需方法:
   - `get_name()`: 返回插件名称
   - `get_icon()`: 返回图标
   - `get_info()`: 返回插件信息
   - `handle_click()`: 处理点击事件

### 示例插件

```python
from src.core.plugin_system import PluginBase

class MyPlugin(PluginBase):
    def get_name(self) -> str:
        return "My Plugin"
    
    def get_icon(self) -> str:
        return "icon"
    
    def get_info(self) -> dict:
        return {
            "name": "My Plugin",
            "version": "1.0.0",
            "author": "Your Name",
            "description": "Plugin description"
        }
    
    def handle_click(self):
        # Your plugin logic
        pass
    
    def on_load(self):
        # Optional: called when plugin loads
        pass
    
    def on_unload(self):
        # Optional: called when plugin unloads
        pass
```

### 启用插件

在 `config/settings.json` 中添加:
```json
{
  "plugin": {
    "enabled_plugins": ["my_plugin"]
  }
}
```

## 开发和调试

### 运行测试
```bash
python test_structure.py
```

### 查看日志
日志文件位于 `logs/larj.log`

### 开发模式
直接运行 `python main.py` 启动应用

### 调试建议
- 使用 Python 调试器（pdb 或 IDE）
- 查看日志文件了解错误详情
- 测试时使用示例配置文件

## 打包发布

### 使用 PyInstaller
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon=icon.ico main.py
```

### 发布清单
- 可执行文件
- config/ 目录（示例配置）
- plugins/ 目录（示例插件）
- everything/ 目录（README）
- README.md
- LICENSE

## 常见问题

### Q: 热键不响应？
A: 检查是否有其他程序占用了相同的热键

### Q: 搜索不工作？
A: 确保 `everything/es.exe` 存在并可执行

### Q: 窗口不显示？
A: 检查日志文件，可能是 PyQt5 问题

### Q: 插件加载失败？
A: 检查插件代码是否正确实现了所有必需方法

## 贡献指南

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 许可证

MIT License
