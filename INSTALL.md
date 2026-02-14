# Larj 安装和故障排除指南

## 系统要求

### 最低要求
- **操作系统**: Windows 10 或 Windows 11
- **Python**: Python 3.8 或更高版本
- **内存**: 至少 100MB 可用内存
- **磁盘空间**: 至少 50MB 可用空间

### 推荐配置
- **操作系统**: Windows 10/11 (64位)
- **Python**: Python 3.10 或更高版本
- **内存**: 200MB 以上可用内存
- **鼠标**: 带侧键的鼠标（用于快捷触发）

## 详细安装步骤

### 步骤 1: 安装 Python

1. 访问 Python 官网: https://www.python.org/downloads/
2. 下载 Python 3.10 或更高版本
3. 运行安装程序
4. **重要**: 勾选 "Add Python to PATH"
5. 完成安装

**验证安装**:
```bash
python --version
```
应该显示 Python 3.8 或更高版本

### 步骤 2: 获取 Larj

#### 方式 A: 从 GitHub 克隆（推荐）
```bash
git clone https://github.com/LISANG3/Larj.git
cd Larj
```

#### 方式 B: 下载 ZIP
1. 访问 https://github.com/LISANG3/Larj
2. 点击 "Code" > "Download ZIP"
3. 解压到目标目录

### 步骤 3: 安装依赖

打开命令提示符或 PowerShell，进入 Larj 目录:

```bash
cd path\to\Larj
pip install -r requirements.txt
```

等待安装完成。

**如果遇到权限问题**:
```bash
pip install --user -r requirements.txt
```

### 步骤 4: 安装 Everything

Larj 使用 Everything 进行文件搜索。

1. 访问 Everything 官网: https://www.voidtools.com/downloads/
2. 下载 "Command-line Interface" (命令行工具)
   - 64位系统: es-1.1.0.24.x64.zip
   - 32位系统: es-1.1.0.24.x86.zip
3. 解压 `es.exe`
4. 将 `es.exe` 放入 `Larj/everything/` 目录

**验证**:
```bash
.\everything\es.exe --version
```

### 步骤 5: 首次运行

#### 使用启动脚本（推荐）
```bash
launch.bat
```

#### 或直接运行
```bash
python main.py
```

### 步骤 6: 配置热键

首次运行后，配置文件会自动创建在 `config/` 目录。

编辑 `config/settings.json`:
```json
{
  "hotkey": {
    "trigger_key": "XButton1",
    "fallback_keys": ["Ctrl+Space"]
  }
}
```

## 常见问题和解决方案

### 1. Python 未找到

**问题**: 运行 `python --version` 显示 "python 不是内部或外部命令"

**解决方案**:
- 重新安装 Python，确保勾选 "Add Python to PATH"
- 或手动添加 Python 到系统 PATH
- 尝试使用 `py` 命令代替 `python`

### 2. 依赖安装失败

**问题**: `pip install` 报错

**解决方案**:
```bash
# 升级 pip
python -m pip install --upgrade pip

# 使用国内镜像（如果下载慢）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 单独安装依赖
pip install PyQt5
pip install pynput
pip install psutil
```

### 3. PyQt5 安装失败（Windows）

**问题**: PyQt5 安装报错或崩溃

**解决方案**:
```bash
# 尝试安装特定版本
pip install PyQt5==5.15.9

# 或使用 wheel 文件
pip install PyQt5 --no-cache-dir
```

### 4. pynput 无法监听输入

**问题**: 热键不响应

**解决方案**:
- 以管理员权限运行 Larj
- 检查是否有其他程序占用了相同热键
- 尝试更改热键配置

### 5. Everything 搜索不工作

**问题**: 搜索框输入后无结果

**可能原因和解决方案**:

**A. es.exe 未安装**
- 确认 `everything/es.exe` 存在
- 重新下载并放置 es.exe

**B. es.exe 版本不兼容**
- 使用 Everything 1.1.0.24 或更高版本
- 确保下载的是命令行工具，不是完整安装包

**C. Everything 服务未运行**
- 安装完整版 Everything 并保持运行
- 或使用 Everything 便携版

### 6. 窗口不显示

**问题**: 按热键后窗口没有出现

**解决方案**:
- 检查 `logs/larj.log` 查看错误信息
- 确认 PyQt5 正确安装
- 尝试手动触发: 在代码中添加调试信息
- 检查窗口是否被其他程序遮挡

### 7. 热键冲突

**问题**: 其他程序也使用相同热键

**解决方案**:
编辑 `config/settings.json`:
```json
{
  "hotkey": {
    "trigger_key": "XButton2",  // 改用另一个鼠标侧键
    "fallback_keys": ["Ctrl+Alt+Space"]  // 改用其他组合键
  }
}
```

### 8. 应用启动失败

**问题**: 点击应用图标无反应或报错

**解决方案**:
- 检查应用路径是否正确
- 确认应用文件存在
- 查看 `logs/larj.log` 了解具体错误
- 更新 `config/apps.json` 中的路径

### 9. 插件加载失败

**问题**: 插件不工作

**解决方案**:
- 确认插件文件在 `plugins/` 目录
- 检查插件是否在 `config/settings.json` 中启用
- 验证插件代码语法正确
- 查看日志了解加载错误

### 10. 性能问题

**问题**: 程序运行缓慢或占用资源高

**解决方案**:
- 减少搜索结果数量（修改 `max_results`）
- 增加防抖时间（修改 `debounce_ms`）
- 关闭不需要的插件
- 清理搜索缓存

## 高级配置

### 自定义窗口样式

编辑 `config/settings.json`:
```json
{
  "window": {
    "width": 800,           // 窗口宽度
    "height": 500,          // 窗口高度
    "opacity": 95,          // 透明度 (0-100)
    "corner_radius": 10,    // 圆角半径
    "follow_mouse": true,   // 跟随鼠标
    "animation_duration": 200  // 动画时长(毫秒)
  }
}
```

### 搜索优化

```json
{
  "search": {
    "max_results": 50,        // 最大结果数
    "debounce_ms": 300,       // 防抖时间
    "cache_timeout": 60,      // 缓存超时(秒)
    "search_paths": [         // 搜索路径限制
      "C:\\Users\\YourName\\Documents"
    ],
    "exclude_paths": [        // 排除路径
      "C:\\Windows",
      "C:\\Program Files"
    ]
  }
}
```

### 应用排序

```json
{
  "application": {
    "auto_sort": true,        // 自动排序
    "sort_by": "usage",       // 排序方式: usage, name, date
    "groups": []              // 分组配置
  }
}
```

## 开发者模式

### 启用调试日志

修改 `main.py` 中的日志级别:
```python
logging.basicConfig(
    level=logging.DEBUG,  # 改为 DEBUG
    ...
)
```

### 测试项目结构

```bash
python test_structure.py
```

### 手动测试模块

```python
# 测试配置管理器
from src.core.config_manager import ConfigManager
config = ConfigManager()
print(config.get("hotkey.trigger_key"))
```

## 卸载

1. 停止 Larj 程序
2. 删除 Larj 目录
3. （可选）删除 Python 虚拟环境
4. （可选）卸载 Everything

## 获取帮助

### 日志位置
- 主日志: `logs/larj.log`
- 包含所有错误和警告信息

### 报告问题
1. 查看日志文件
2. 记录复现步骤
3. 在 GitHub 创建 Issue
4. 附上日志和系统信息

### 联系方式
- GitHub Issues: https://github.com/LISANG3/Larj/issues
- 邮件: （如果有）

## 更新

### 更新 Larj
```bash
cd Larj
git pull
pip install -r requirements.txt --upgrade
```

### 备份配置
更新前建议备份 `config/` 目录:
```bash
xcopy config config_backup /E /I
```

## 性能基准

### 正常指标
- 启动时间: < 2秒
- 搜索响应: < 200ms
- 内存占用: < 50MB
- CPU占用: < 5% (空闲时)

### 优化建议
- 定期清理日志文件
- 关闭不需要的插件
- 限制搜索范围
- 使用 SSD 存储

## 安全建议

1. **只从官方源下载** Larj 和 Everything
2. **检查插件来源** 谨慎安装第三方插件
3. **定期更新** 保持软件最新版本
4. **备份配置** 防止数据丢失
5. **权限最小化** 不要以不必要的高权限运行

## 许可证

Larj 使用 MIT 许可证。
Everything 有单独的许可证，请查阅其官网。

## 致谢

- Everything: https://www.voidtools.com/
- PyQt5: https://www.riverbankcomputing.com/software/pyqt/
- pynput: https://github.com/moses-palmer/pynput
