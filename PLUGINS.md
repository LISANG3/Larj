# Larj 插件开发指南

本文档详细介绍 Larj 插件系统的架构、开发流程和最佳实践。

## 目录

- [插件系统概述](#插件系统概述)
- [插件架构](#插件架构)
- [快速开始](#快速开始)
- [插件接口详解](#插件接口详解)
- [配置管理](#配置管理)
- [内置插件](#内置插件)
- [开发最佳实践](#开发最佳实践)
- [调试与日志](#调试与日志)
- [常见问题](#常见问题)

## 插件系统概述

Larj 插件系统采用**自动发现机制**，插件开发者只需将插件目录放入 `plugins/` 目录，系统会自动识别并加载。

### 核心特性

- **自动发现**: 扫描 `plugins/` 目录，自动识别插件模块
- **热配置**: 通过配置文件启用/禁用插件，无需修改代码
- **独立配置**: 每个插件拥有独立的配置文件
- **生命周期管理**: 提供 `on_load`、`on_unload` 等钩子函数
- **配置表单自动生成**: 基于 `config_schema` 自动生成设置界面

### 插件目录结构（一个插件一个文件夹）

```
plugins/
├── another_plugin/           # 目录插件
│   ├── __init__.py          # 必需：插件入口（PluginBase 子类）
│   ├── utils.py             # 可选：辅助模块
│   └── resources/           # 可选：资源文件
└── ...
```

## 插件架构

### 类继承关系

```
PluginBase (基类)
    │
    ├── get_metadata()      # 返回插件元数据
    ├── handle_click()      # 点击事件处理 (必需)
    ├── on_load()          # 加载时调用
    ├── on_unload()        # 卸载时调用
    └── apply_settings()   # 应用配置
```

### 生命周期

```
1. 发现阶段 (Discovery)
   └── 扫描 plugins/ 目录
   └── 读取插件元数据 (get_metadata)
   └── 注册到 discovered_plugins

2. 加载阶段 (Loading)
   └── 检查是否在 enabled_plugins 列表
   └── 实例化插件类
   └── 调用 on_load()
   └── 加载独立配置文件

3. 运行阶段 (Running)
   └── 用户点击 → handle_click()
   └── 配置变更 → apply_settings()

4. 卸载阶段 (Unloading)
   └── 调用 on_unload()
   └── 清理资源
```

### 配置存储

插件配置采用**主配置 + 独立文件**机制：

```
config/
├── settings.json           # 主配置（plugin.enabled_plugins / plugin.plugin_directory）
├── plugins/                # 插件独立配置目录（每个插件一个 JSON）
│   ├── mtran_server.json   # 翻译插件配置
│   ├── ocr.json            # OCR 插件配置
│   └── my_plugin.json      # 自定义插件配置
└── plugins.json            # legacy：仅用于旧版迁移来源，不作为当前主路径
```

其中：

- 插件启用列表读取自 `config/settings.json` 的 `plugin.enabled_plugins`
- 插件运行时配置读取/写入 `config/plugins/{plugin_id}.json`

## 快速开始

### 创建第一个插件

1. **创建插件目录**

在 `plugins/` 目录创建 `hello_world/__init__.py`：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hello World Plugin - A simple example plugin
"""

from PyQt5.QtWidgets import QMessageBox
from src.core.plugin_system import PluginBase


class HelloWorldPlugin(PluginBase):
    """Hello World 示例插件"""

    def get_metadata(self) -> dict:
        return {
            "plugin_id": "hello_world",
            "name": "Hello World",
            "icon": "info",
            "version": "1.0.0",
            "author": "Your Name",
            "description": "一个简单的示例插件",
            "config_schema": {}
        }

    def handle_click(self):
        QMessageBox.information(None, "Hello", "Hello, World!")
```

2. **启用插件**

编辑 `config/settings.json`：

```json
{
  "plugin": {
    "enabled_plugins": ["hello_world"]
  }
}
```

3. **运行测试**

重启 Larj，点击插件图标即可看到效果。

## 插件接口详解

### get_metadata()

返回插件元数据，系统通过此方法获取插件信息。

**返回字段：**

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| plugin_id | str | 是 | 唯一标识符，建议使用小写+下划线 |
| name | str | 是 | 显示名称 |
| icon | str | 否 | 图标标识（目前支持：info, translate, ocr） |
| version | str | 是 | 版本号，遵循语义化版本 |
| author | str | 否 | 作者名称 |
| description | str | 是 | 插件描述 |
| config_schema | dict | 否 | 配置项定义 |

**示例：**

```python
def get_metadata(self) -> dict:
    return {
        "plugin_id": "my_tool",
        "name": "我的工具",
        "icon": "info",
        "version": "1.0.0",
        "author": "Developer",
        "description": "一个实用的工具插件",
        "config_schema": {
            "api_key": {
                "type": "str",
                "required": True,
                "default": "",
                "desc": "API 密钥"
            },
            "timeout": {
                "type": "int",
                "required": False,
                "default": 30,
                "desc": "超时时间（秒）"
            },
            "enabled": {
                "type": "bool",
                "required": False,
                "default": True,
                "desc": "启用功能"
            }
        }
    }
```

### handle_click()

用户点击插件图标时调用，是插件的核心入口。

**注意事项：**
- 此方法在主线程执行，避免长时间阻塞
- 耗时操作应使用 QThread 或异步处理
- 必须捕获异常，避免影响主程序

**示例：**

```python
def handle_click(self):
    try:
        dialog = MyPluginDialog()
        dialog.exec_()
    except Exception as e:
        self.logger.error(f"Plugin error: {e}")
```

### on_load()

插件加载时调用，用于初始化资源。

**示例：**

```python
def on_load(self):
    self.logger.info("Plugin loaded")
    self._load_config()
    self._init_resources()
```

### on_unload()

插件卸载时调用，用于清理资源。

**示例：**

```python
def on_unload(self):
    self.logger.info("Plugin unloaded")
    self._cleanup()
```

### apply_settings(settings: dict)

应用配置变更时调用。

**示例：**

```python
def apply_settings(self, settings: dict):
    self._api_key = settings.get("api_key", "")
    self._timeout = settings.get("timeout", 30)
    self.logger.info(f"Settings applied: timeout={self._timeout}")
```

## 配置管理

### 配置文件格式

每个插件的配置存储在 `config/plugins/{plugin_id}.json`：

```json
{
  "api_key": "your_api_key_here",
  "timeout": 30,
  "enabled": true
}
```

### 读取配置

```python
from pathlib import Path
import json

class MyPlugin(PluginBase):
    def on_load(self):
        config_file = Path("config/plugins") / "my_plugin.json"
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
        else:
            self._config = self._get_default_config()
```

### 配置表单自动生成

系统根据 `config_schema` 自动在设置界面生成配置表单：

```python
"config_schema": {
    "api_key": {
        "type": "str",        # 字符串类型
        "required": True,     # 必填项
        "default": "",        # 默认值
        "desc": "API 密钥"    # 显示标签
    },
    "timeout": {
        "type": "int",        # 整数类型
        "required": False,
        "default": 30,
        "desc": "超时时间"
    },
    "region": {
        "type": "enum",       # 枚举类型
        "required": False,
        "default": "ap-beijing",
        "desc": "服务区域",
        "options": ["ap-beijing", "ap-shanghai", "ap-guangzhou"]
    }
}
```

**支持的字段类型：**

| 类型 | 说明 | 表单控件 |
|------|------|----------|
| str | 字符串 | QLineEdit |
| int | 整数 | QSpinBox |
| bool | 布尔值 | QCheckBox |
| enum | 枚举 | QComboBox |

## 内置插件

### 腾讯翻译插件 (mtran_server)

基于腾讯云机器翻译 API 的多语言翻译插件。

**功能特性：**
- 支持 15 种语言互译
- 自动检测源语言
- 语言交换功能
- 字符计数器

**配置项：**

| 配置项 | 类型 | 必需 | 说明 |
|--------|------|------|------|
| secret_id | str | 是 | 腾讯云 API 密钥 ID |
| secret_key | str | 是 | 腾讯云 API 密钥 Key |
| region | str | 否 | API 地域，默认 ap-beijing |

**使用方法：**
1. 在 [腾讯云控制台](https://console.cloud.tencent.com/cam/capi) 获取 API 密钥
2. 在设置 → 插件管理中配置密钥
3. 点击翻译图标打开翻译对话框

**技术实现：**
- 使用腾讯云 TMT API v3
- 采用 TC3-HMAC-SHA256 签名算法
- 异步请求，不阻塞主线程

### OCR 识别插件 (TencentOcr)

基于腾讯云 OCR API 的屏幕文字识别插件。

**功能特性：**
- 区域截图识别
- 高精度识别（99% 准确率）
- 支持 20+ 种语言
- 一键复制结果

**配置项：**

| 配置项 | 类型 | 必需 | 说明 |
|--------|------|------|------|
| secret_id | str | 是 | 腾讯云 API 密钥 ID |
| secret_key | str | 是 | 腾讯云 API 密钥 Key |
| region | str | 否 | API 地域，默认 ap-beijing |

**使用方法：**
1. 在 [腾讯云控制台](https://console.cloud.tencent.com/cam/capi) 获取 API 密钥
2. 在设置 → 插件管理中配置密钥
3. 点击 OCR 图标进入截图模式
4. 拖拽选择识别区域
5. 查看识别结果

**技术实现：**
- 使用腾讯云 GeneralAccurateOCR 接口
- 全屏透明窗口实现区域选择
- Base64 编码传输图像数据

## 开发最佳实践

### 1. 异步处理耗时操作

```python
from PyQt5.QtCore import QThread, pyqtSignal

class Worker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, data):
        super().__init__()
        self.data = data
    
    def run(self):
        try:
            result = self._process(self.data)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

class MyPlugin(PluginBase):
    def handle_click(self):
        self.worker = Worker(self._get_data())
        self.worker.finished.connect(self._on_success)
        self.worker.error.connect(self._on_error)
        self.worker.start()
```

### 2. 资源清理

```python
class MyPlugin(PluginBase):
    def __init__(self):
        self._temp_files = []
        self._worker = None
    
    def on_unload(self):
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait()
        
        for temp_file in self._temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)
```

### 3. 错误处理

```python
import logging

class MyPlugin(PluginBase):
    def __init__(self):
        self.logger = logging.getLogger(f"Plugin.{self.__class__.__name__}")
    
    def handle_click(self):
        try:
            self._do_work()
        except requests.Timeout:
            self._show_error("请求超时，请检查网络连接")
        except requests.ConnectionError:
            self._show_error("网络连接失败")
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}", exc_info=True)
            self._show_error(f"发生错误: {e}")
```

### 4. 配置验证

```python
def apply_settings(self, settings: dict):
    api_key = settings.get("api_key", "").strip()
    if not api_key:
        raise ValueError("API 密钥不能为空")
    
    timeout = settings.get("timeout", 30)
    if timeout < 1 or timeout > 300:
        raise ValueError("超时时间必须在 1-300 秒之间")
    
    self._api_key = api_key
    self._timeout = timeout
```

### 5. 日志记录

```python
import logging

class MyPlugin(PluginBase):
    def __init__(self):
        self.logger = logging.getLogger(f"Plugin.{self.__class__.__name__}")
    
    def handle_click(self):
        self.logger.info("Plugin clicked")
        self.logger.debug(f"Current config: {self._config}")
```

## 调试与日志

### 查看日志

日志文件位置：`logs/larj.log`

```bash
# 实时查看日志
tail -f logs/larj.log

# 查看插件相关日志
grep "Plugin" logs/larj.log
```

### 调试模式

在插件中启用详细日志：

```python
import logging

class MyPlugin(PluginBase):
    def __init__(self):
        self.logger = logging.getLogger(f"Plugin.{self.__class__.__name__}")
        self.logger.setLevel(logging.DEBUG)
```

### 常见调试技巧

1. **检查插件是否被发现**

```python
# 在 get_metadata 中添加日志
def get_metadata(self) -> dict:
    print(f"[DEBUG] Plugin discovered: {self.__class__.__name__}")
    return {...}
```

2. **检查配置加载**

```python
def on_load(self):
    config_file = Path("config/plugins") / "my_plugin.json"
    print(f"[DEBUG] Config file exists: {config_file.exists()}")
    print(f"[DEBUG] Config path: {config_file}")
```

## 常见问题

### Q: 插件没有出现在列表中？

**排查步骤：**
1. 检查文件是否在 `plugins/` 目录
2. 检查是否采用目录结构：`plugins/<plugin_id>/__init__.py`
3. 检查 `get_metadata()` 返回的 `plugin_id` 是否正确
4. 查看日志文件是否有加载错误
5. 检查 `plugin_id` 是否与目录名一致

### Q: 插件点击无反应？

**排查步骤：**
1. 检查 `handle_click()` 是否抛出异常
2. 查看日志文件中的错误信息
3. 确保没有阻塞主线程的操作

### Q: 配置保存后没有生效？

**排查步骤：**
1. 检查配置文件 `config/plugins/{plugin_id}.json` 是否存在
2. 确认 `apply_settings()` 方法是否正确实现
3. 检查 `config_schema` 中的字段名是否与配置文件一致

### Q: 如何调试插件？

1. 在代码中添加 `print()` 或 `self.logger.debug()`
2. 查看 `logs/larj.log` 日志文件
3. 使用 Python 调试器：`import pdb; pdb.set_trace()`

### Q: 如何处理网络请求超时？

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_session():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('https://', adapter)
    return session
```

## 完整示例

以下是一个功能完整的目录插件示例（`plugins/weather/__init__.py`）：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Weather Plugin - Display weather information
"""

import logging
import requests
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import QThread, pyqtSignal

from src.core.plugin_system import PluginBase


class WeatherWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, city, api_key):
        super().__init__()
        self.city = city
        self.api_key = api_key
    
    def run(self):
        try:
            url = f"https://api.weather.com/v1?city={self.city}&key={self.api_key}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            self.finished.emit(response.json())
        except Exception as e:
            self.error.emit(str(e))


class WeatherDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("天气预报")
        self.setFixedSize(300, 200)
        
        layout = QVBoxLayout(self)
        
        self.label = QLabel("正在获取天气信息...")
        layout.addWidget(self.label)
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)
        layout.addWidget(self.close_btn)
    
    def update_weather(self, data):
        temp = data.get("temperature", "N/A")
        desc = data.get("description", "N/A")
        self.label.setText(f"温度: {temp}°C\n天气: {desc}")


class WeatherPlugin(PluginBase):
    """天气查询插件"""
    
    def __init__(self):
        self.logger = logging.getLogger("Plugin.Weather")
        self._api_key = ""
        self._city = "Beijing"
        self._worker = None
    
    def get_metadata(self) -> dict:
        return {
            "plugin_id": "weather",
            "name": "天气预报",
            "icon": "info",
            "version": "1.0.0",
            "author": "Developer",
            "description": "查询城市天气信息",
            "config_schema": {
                "api_key": {
                    "type": "str",
                    "required": True,
                    "default": "",
                    "desc": "天气 API 密钥"
                },
                "city": {
                    "type": "str",
                    "required": False,
                    "default": "Beijing",
                    "desc": "默认城市"
                }
            }
        }
    
    def on_load(self):
        self.logger.info("Weather plugin loaded")
    
    def apply_settings(self, settings: dict):
        self._api_key = settings.get("api_key", "")
        self._city = settings.get("city", "Beijing")
        self.logger.info(f"Settings applied: city={self._city}")
    
    def handle_click(self):
        if not self._api_key:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(None, "提示", "请先配置 API 密钥")
            return
        
        self.dialog = WeatherDialog()
        
        self._worker = WeatherWorker(self._city, self._api_key)
        self._worker.finished.connect(self.dialog.update_weather)
        self._worker.error.connect(lambda e: self.dialog.label.setText(f"错误: {e}"))
        self._worker.start()
        
        self.dialog.exec_()
    
    def on_unload(self):
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait()
        self.logger.info("Weather plugin unloaded")


```

## 更多资源

- [Larj 主项目](../README.md)
- [腾讯云 API 文档](https://cloud.tencent.com/document/api)
- [PyQt5 文档](https://www.riverbankcomputing.com/static/Docs/PyQt5/)

---

如有问题或建议，欢迎在 [Issues](https://github.com/LISANG3/Larj/issues) 中反馈。
