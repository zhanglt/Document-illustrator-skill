# Repository Guidelines

## 项目结构与职责

本项目是文档配图技能包，由 AI 助手分析内容，Python 脚本调用 Gemini 生成图片。

- `SKILL.md`：助手使用流程；调整交互步骤时同步更新。
- `README.md`：安装、配置与用户使用说明。
- `scripts/generate_single_image.py`：根据标题、正文和风格提示词生成单图。
- `scripts/generate_illustrations.py`：解析 Markdown 的 `##`、`###`、`####` 标题并生成配图。
- `styles/`：风格提示词，文件名使用 `gradient-glass.md` 等小写连字符形式。
- `examples/`：示例说明与展示素材；目前仅有说明文件。

## 安装与开发命令

在项目根目录执行：

```powershell
python -m pip install google-genai pillow python-dotenv
python -X utf8 scripts/generate_single_image.py --help
python -X utf8 scripts/generate_illustrations.py --help
python -m py_compile scripts/generate_single_image.py scripts/generate_illustrations.py
```

以上依次安装依赖、检查两个 CLI 入口及检查 Python 语法。项目无需构建，也未配置统一的格式化或 lint 命令。

批量生成示例：

```powershell
python -X utf8 scripts/generate_illustrations.py article.md --style ticket --level h2 --resolution 2K --output ./output
```

此命令需要真实 API 配置，会产生接口调用；图片写入 `output/images/`，流程可能要求交互确认。

## 编码与命名规范

Python 使用四空格缩进，函数和变量采用 `snake_case`；沿用现有 CLI 参数风格。修改参数、依赖或模型时，同步维护文档和帮助文本。

说明性内容以中文为主，保留准确的 API 名称、配置项和路径。所有 `.md`、`.json`、`.yaml` 文件按 UTF-8 无 BOM 读写。PowerShell 写入使用 `Set-Content -Encoding utf8`，并确认所用版本不会产生 BOM；禁止使用 `>`、`>>` 或默认编码的 `Out-File` 写文件。

## 测试与验收

当前没有测试目录、自动化测试框架或覆盖率门槛。提交前至少执行上述语法检查和两个 `--help` 命令。修改文档解析时，用包含不同标题层级的短 Markdown 验证章节提取；修改图片生成时，优先模拟 API 响应，再按需执行真实调用。

真实调用后确认图片可打开、输出路径正确、内容和风格符合要求。批量输出采用 `illustration-01.png` 命名。记录验证命令与结果，明确区分静态检查和真实接口验证。

## 提交与 Pull Request

当前目录不含 Git 元数据，无法核实历史提交惯例。建议使用简洁的动词开头提交说明，例如 `fix: 修复图片输出路径`，每次提交聚焦一个问题。

PR 应说明修改目的、涉及文件、验证结果和配置变化；有关联问题时附链接，视觉效果变更附生成样例，并移除敏感内容。

## 配置与网络

通过 `.env` 或环境变量设置 `GEMINI_API_KEY`，禁止提交或输出真实密钥。两个脚本目前使用 `google-genai`，模型写为 `gemini-3-pro-image-preview`；更换提供方时需适配请求和响应格式。

网络请求失败时，使用 `http://127.0.0.1:81` 作为代理重试。生成图片尚未被 `.gitignore` 默认忽略，提交前检查是否意外包含生成物。
