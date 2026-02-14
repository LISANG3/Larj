# 插件开发文档

Larj 插件通过继承 `PluginBase` 实现，放在 `plugins/` 目录后即可由系统自动发现。

## 1. 插件接口

所有插件都需要实现以下方法（位于 `src/core/plugin_system.py`）：

- `get_name() -> str`：返回插件显示名
- `get_icon() -> str`：返回图标标识（可为空字符串）
- `get_info() -> dict`：返回插件信息（名称、版本、作者、描述）
- `handle_click()`：用户点击插件时执行的逻辑

## 2. 最小示例

```python
from src.core.plugin_system import PluginBase


class HelloPlugin(PluginBase):
    def get_name(self) -> str:
        return "Hello"

    def get_icon(self) -> str:
        return "hello"

    def get_info(self) -> dict:
        return {
            "name": "Hello",
            "version": "1.0.0",
            "author": "Your Name",
            "description": "示例插件"
        }

    def handle_click(self):
        print("Hello from plugin")
```

将文件保存为 `plugins/hello_plugin.py`。

## 3. 启用插件

在 `config/settings.json` 中配置：

```json
{
  "plugin": {
    "enabled_plugins": ["hello_plugin"]
  }
}
```

> `enabled_plugins` 中填写的是插件文件名（不含 `.py`）。

## 4. 开发建议

- `handle_click()` 中尽量避免长时间阻塞操作
- 仅使用可信输入，避免拼接命令字符串导致安全风险
- 对异常进行捕获并记录，避免影响主程序运行
