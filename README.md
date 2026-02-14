# Larj

Larj is a lightweight Windows desktop efficiency tool designed for quick file searching, application launching, and plugin extensions.

## Features

- **Global Hotkey Trigger**: Trigger the panel with a mouse side button (XButton1) or keyboard shortcut
- **Fast File Search**: Integrated with Everything for instant file searching
- **Quick App Launch**: One-click access to your favorite applications
- **Plugin System**: Extensible plugin architecture for custom functionality
- **Lightweight**: Minimal resource usage, always ready when you need it

## Installation

### Requirements

- Windows 10/11
- Python 3.8 or higher
- Everything (recommended: install Everything and copy `es.exe`/`Everything.exe` into `everything/`)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/LISANG3/Larj.git
cd Larj
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Download Everything from [Everything](https://www.voidtools.com/downloads/), and place `es.exe` and `Everything.exe` in the `everything/` directory.

4. Run the application:
```bash
python main.py
```

## Usage

### Triggering the Panel

- **Mouse**: Press the side button (XButton1) on your mouse
- **Keyboard**: Press Ctrl+Space (configurable)

### Searching Files

1. Trigger the panel
2. Type your search query in the search box
3. Results appear instantly from Everything
4. Double-click a result to open the file

### Managing Applications

1. Trigger the panel
2. Click on any app icon to launch it
3. Click "+ 添加应用" to add new applications
4. Apps are automatically sorted by usage frequency

### Using Plugins

Plugins extend Larj's functionality. Sample plugins included:
- **Calculator**: Quick access to Windows Calculator
- **Notepad**: Quick access to Windows Notepad

To enable a plugin, add its name to `config/settings.json` under `plugin.enabled_plugins`.
For plugin authoring details, see [PLUGIN_DEVELOPMENT.md](PLUGIN_DEVELOPMENT.md).

## Configuration

Configuration files are stored in the `config/` directory:

- `settings.json`: Main application settings
- `apps.json`: Application shortcuts
- `plugins.json`: Plugin configurations

### Example settings.json

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
  }
}
```

## Developing Plugins

Create a new plugin by extending the `PluginBase` class:

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
            "description": "Plugin description"
        }
    
    def handle_click(self):
        # Your plugin logic here
        pass
```

Place your plugin file in the `plugins/` directory and enable it in the configuration.

## Architecture

Larj follows a modular, event-driven architecture:

- **Main Controller**: Coordinates all modules and manages event flow
- **Hotkey Listener**: Monitors global input for trigger events
- **Window Manager**: Controls the floating panel window
- **Search Engine**: Integrates with Everything for file search
- **Application Manager**: Manages application shortcuts
- **Plugin System**: Loads and manages plugins
- **Configuration Manager**: Handles settings persistence

For detailed architecture information, see [Larj_技术架构文档_v1.md](Larj_技术架构文档_v1.md).

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues.

## Support

For questions or issues, please open an issue on GitHub.
