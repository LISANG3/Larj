# 贡献指南

感谢您对 Larj 项目的关注！我们欢迎各种形式的贡献。

## 如何贡献

### 报告 Bug

1. 在 [Issues](https://github.com/LISANG3/Larj/issues) 页面搜索是否已有类似问题
2. 如果没有，创建新的 Issue
3. 清楚描述问题：
   - 详细的复现步骤
   - 期望行为
   - 实际行为
   - 系统信息（Windows 版本、Python 版本）
   - 相关日志（`logs/larj.log`）

### 提出功能请求

1. 在 Issues 中描述新功能
2. 说明为什么需要这个功能
3. 提供使用场景示例
4. 如果可能，建议实现方案

### 提交代码

#### 1. Fork 和克隆

```bash
# Fork 项目到你的账号
# 然后克隆
git clone https://github.com/YOUR_USERNAME/Larj.git
cd Larj
```

#### 2. 创建分支

```bash
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/your-bug-fix
```

#### 3. 开发

- 遵循项目代码规范
- 添加必要的注释
- 编写/更新文档
- 编写测试（如适用）

#### 4. 测试

```bash
# 运行结构测试
python test_structure.py

# 手动测试你的改动
python main.py
```

#### 5. 提交

```bash
git add .
git commit -m "描述你的改动"
```

提交信息格式：
- `feat: 添加新功能`
- `fix: 修复 bug`
- `docs: 更新文档`
- `style: 代码格式调整`
- `refactor: 代码重构`
- `test: 添加测试`
- `chore: 构建/工具相关`

#### 6. 推送和 Pull Request

```bash
git push origin feature/your-feature-name
```

然后在 GitHub 上创建 Pull Request。

## 代码规范

### Python 代码风格

- 遵循 PEP 8 规范
- 使用 4 空格缩进
- 类名使用 PascalCase
- 函数名使用 snake_case
- 常量使用 UPPER_CASE
- 私有方法/属性以 `_` 开头

### 文档字符串

```python
def function_name(param1: str, param2: int) -> bool:
    """
    简短描述函数功能
    
    Args:
        param1: 参数1说明
        param2: 参数2说明
    
    Returns:
        返回值说明
    
    Raises:
        可能抛出的异常
    """
    pass
```

### 注释

- 在复杂逻辑处添加注释
- 注释应解释"为什么"，而不仅是"是什么"
- 保持注释更新

## 项目结构规范

### 新增模块

放置在合适的目录：
- 核心功能: `src/core/`
- UI 组件: `src/ui/`
- 工具函数: `src/utils/`
- 插件: `plugins/`

### 依赖管理

如果添加新依赖：
1. 更新 `requirements.txt`
2. 在 PR 中说明为什么需要这个依赖
3. 选择轻量级的库

## 插件开发

### 插件规范

1. 继承 `PluginBase` 类
2. 实现所有必需方法
3. 添加清晰的文档字符串
4. 处理可能的异常
5. 避免阻塞操作

### 示例插件

参考 `plugins/calculator.py` 和 `plugins/notepad.py`

### 插件测试

```python
# 测试插件加载
from src.core.plugin_system import PluginSystem
from src.core.config_manager import ConfigManager

config = ConfigManager()
plugin_system = PluginSystem(config)
plugin_system.load_plugin("your_plugin")
```

## 文档

### 更新文档

如果你的改动影响以下内容，请更新相应文档：
- 功能变化 → README.md
- 配置变化 → STRUCTURE.md
- 安装流程 → INSTALL.md
- 架构变化 → Larj_技术架构文档_v1.md

### 文档风格

- 使用清晰简洁的语言
- 提供代码示例
- 添加必要的截图
- 保持格式一致

## 测试

### 手动测试清单

提交前请测试：
- [ ] 程序能正常启动
- [ ] 热键触发工作正常
- [ ] 搜索功能正常
- [ ] 应用启动正常
- [ ] 窗口显示/隐藏正常
- [ ] 配置加载正常
- [ ] 插件系统正常（如果涉及）

### 自动化测试

运行测试脚本：
```bash
python test_structure.py
```

## 版本控制

### 分支策略

- `main`: 稳定版本
- `develop`: 开发版本
- `feature/*`: 功能开发
- `fix/*`: Bug 修复
- `hotfix/*`: 紧急修复

### 提交频率

- 经常提交小的改动
- 每个提交应该是一个逻辑单元
- 避免一次提交过多改动

## Pull Request 流程

1. **创建 PR**
   - 填写清晰的标题和描述
   - 关联相关 Issue
   - 添加适当的标签

2. **代码审查**
   - 等待维护者审查
   - 根据反馈进行修改
   - 保持讨论友好和建设性

3. **合并**
   - 审查通过后由维护者合并
   - 合并后可删除特性分支

## 行为准则

- 尊重所有贡献者
- 接受建设性批评
- 关注对项目最有利的事情
- 展示同理心和友善

## 社区

### 交流渠道

- GitHub Issues: 问题讨论和功能请求
- Pull Requests: 代码审查和讨论

### 获取帮助

如果遇到问题：
1. 查看文档（README, INSTALL, STRUCTURE）
2. 搜索已有 Issues
3. 创建新 Issue 提问

## 认可

所有贡献者将在 README 中被列出（如果适用）。

感谢贡献！🎉
