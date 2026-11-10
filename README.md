# Document Illustrator
# 源代码来自：https://github.com/op7418/Document-illustrator-skill

![Document Illustrator Cover](https://github.com/user-attachments/assets/d8b4c25c-2c9d-4e6c-aafe-d2abae764e81)

> 基于 AI 智能分析的文档配图生成工具

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

**Document Illustrator** 是一个可供 Codex / Claude Code 使用的文档配图技能包，它能理解文档内容、归纳核心要点，并为每个主题生成配图。本仓库增加了 Nebula image2-4k 生图接口，同时保留 Gemini 后端。

## ✨ 核心特性

- **🤖 AI 智能归纳**：自动理解文档内容，智能提取核心主题，无需依赖标题格式
- **📝 格式无关**：支持任何格式的文档（Markdown、纯文本、PDF 等）
- **🎨 三种风格**：渐变玻璃卡片、票据风格、矢量插画，满足不同场景需求
- **📐 图片规格**：Gemini 支持 16:9 和 3:4；Nebula image2-4k 支持 16:9、3840x2160
- **生图后端可选**：通过 `--provider gemini|nebula|nanobanana` 切换，支持配置默认后端
- **🖼️ 封面图可选**：可生成概括全文的封面图作为系列配图的引导
- **✅ 内容完整**：展示归纳结果供你确认，确保所有重要信息都被包含

## 🚀 快速开始

### 使用 npx 安装（推荐）

```bash
npx skills add https://github.com/zhanglt/Document-illustrator-skill
```

### 手动安装

1. 克隆或下载本仓库到 Claude Skills 目录：

```bash
cd ~/.claude/skills/
git clone https://github.com/zhanglt/Document-illustrator-skill.git document-illustrator
```

2. 配置 API 密钥（见下方"配置说明"部分）

3. 安装 Python 依赖（见下方"环境要求"部分）

### 基本使用

在 Claude Code 中直接告诉 Claude：

```
帮我为这个文档生成配图：/path/to/document.md
```

或者：

```
我想为这篇文章生成一些配图
```

Claude 会引导你完成整个配图生成流程。

## 🎨 三种风格说明

### 1. 渐变玻璃卡片风格 (gradient-glass)

**视觉特点**：
- Apple Keynote 风格的极简主义设计
- 玻璃拟态（Glassmorphism）效果
- 深邃虚空黑或纯净陶瓷白基底
- 流动的极光渐变色
- 3D 玻璃物体和发光效果

**适用场景**：
- 科技产品介绍
- 数据分析报告
- 未来趋势展望
- 产品功能演示

### 2. 票据风格 (ticket)

**视觉特点**：
- 数字极简票券设计
- 高度对比的黑白配色
- 类似登机牌、门票的结构化布局
- 精确的几何分区
- 中英混排，多向文字布局

**适用场景**：
- 信息图表
- 统计数据展示
- 时间线和流程图
- 要点总结

### 3. 矢量插画风格 (vector-illustration)

**视觉特点**：
- 扁平化矢量插画
- 统一粗细的黑色轮廓线
- 复古柔和的配色方案
- 几何化处理
- 横向全景式构图

**适用场景**：
- 故事叙述
- 概念解释
- 教育内容
- 品牌宣传

## 📦 安装和配置

### 使用 Nebula nanobanana 分组生图

单图和批量脚本均新增 `--provider nanobanana`，使用 Gemini 原生接口，
与 `--provider nebula` 的 image2-4k 分组分别选择、分别配置密钥。
在统一配置文件 `~/.agents/skills/document-illustrator/.env` 中添加：

```dotenv
NEBULA_NANOBANANA_BASE_URL=https://img-api.apinebula.ai/v1beta/models
NEBULA_NANOBANANA_API_KEY=your-nanobanana-group-api-key
NEBULA_NANOBANANA_MODEL=gemini-3.1-flash-image
# 可选：设为默认生图后端
ILLUSTRATOR_IMAGE_PROVIDER=nanobanana
```

令牌必须属于 **nanobanana 分组**；模型可用列表建议留空，或包含所选模型。
此模式只读取 `NEBULA_NANOBANANA_API_KEY`，不复用 image2-4k 的 `NEBULA_API_KEY`。
模型默认 `gemini-3.1-flash-image`，可配置为当前令牌支持的其他模型，例如
`gemini-3-pro-image-preview`。模型可能调整，可通过 `GET https://img-api.apinebula.ai/v1/models`
确认可用模型；脚本不会为此额外发起查询或自动切换模型。

```powershell
# 单图：支持现有 16:9、3:4 比例，可请求 1K、2K、4K，默认 2K
python -X utf8 scripts/generate_single_image.py --provider nanobanana --title "智慧水利" --content "监测感知、预警调度" --style-file styles/ticket.md --ratio 3:4 --resolution 2K --output output/banana.png

# 按 Markdown 二级标题批量生成，比例读取 ILLUSTRATOR_BATCH_RATIO
python -X utf8 scripts/generate_illustrations.py article.md --provider nanobanana --style ticket --level h2 --resolution 2K --output output
```

请求为 `POST https://img-api.apinebula.ai/v1beta/models/{model}:generateContent`，
使用 Bearer 认证，发送 `contents` 和 `generationConfig.imageConfig`，从
`candidates[0].content.parts[].inlineData` 解码图片。保存前用 Pillow 验证图片，
按输出扩展名编码；不记录完整 Base64 响应，也不强制套用 image2-4k 的固定像素限制。
分辨率参数的实际支持情况、图片尺寸及比例以所选模型输出为准。
此接入提供文本生图，暂不提供参考图编辑；无需 Google SDK 或新增依赖。
请求超时为 1800 秒，复用现有代理与防重复提交逻辑：403 或明确未建立连接时尝试
`http://127.0.0.1:81`；POST 超时或中断后不自动重发，须先核实任务状态。

接口依据：[nanobanana 官方文档](https://docs.apinebula.ai/docs/advanced/image/nanobanana)。
离线验证：`python -X utf8 -m unittest discover -s tests -v`。

### 配置单图比例、批量比例与请求分辨率

统一 `.env` 同时支持原有平铺格式和以下分组格式（示例密钥均为占位符）：

```dotenv
# 值为 nanobanana、nebula 或 gemini；默认后端必须放在第一个分组之前
ILLUSTRATOR_IMAGE_PROVIDER=nanobanana

[nanobanana]
NEBULA_NANOBANANA_BASE_URL=https://img-api.apinebula.ai/v1beta/models
NEBULA_NANOBANANA_API_KEY=your-nanobanana-api-key
NEBULA_NANOBANANA_MODEL=gemini-3.1-flash-image
ILLUSTRATOR_SINGLE_RATIO=16:9
ILLUSTRATOR_BATCH_RATIO=16:9
ILLUSTRATOR_RESOLUTION=2K

[image2-4k]
NEBULA_ENDPOINT=https://img-api.apinebula.ai/v1/images/generations
NEBULA_API_KEY=your-image2-4k-api-key
NEBULA_MODEL=gpt-image-2-4k
NEBULA_SIZE=3840x2160
NEBULA_QUALITY=high

[gemini]
GEMINI_BASE_URL=https://generativelanguage.googleapis.com
GEMINI_API_KEY=your-google-gemini-api-key
GEMINI_MODEL=gemini-3-pro-image-preview
ILLUSTRATOR_SINGLE_RATIO=16:9
ILLUSTRATOR_BATCH_RATIO=16:9
ILLUSTRATOR_RESOLUTION=2K
```

各后端的访问地址独立配置，未配置或值为空时使用示例中的默认地址：

| 分组 | URL 配置项 | 地址格式 |
|------|------------|----------|
| `[nanobanana]` | `NEBULA_NANOBANANA_BASE_URL` | 包含 API 版本和 `/models` 的基础地址，脚本仅追加 `/{model}:generateContent`；升级版本时修改此配置 |
| `[image2-4k]` | `NEBULA_ENDPOINT` | 完整生图接口地址，包含 `/v1/images/generations` |
| `[gemini]` | `GEMINI_BASE_URL` | 基础地址，由 `google-genai` SDK 追加 API 版本和模型路径 |

已有 `.env` 只需将 URL 配置项补入对应分组，不要重复创建分组。
本地 `.env` 含真实密钥，已由 Git 忽略；共享配置示例使用本节占位符。

`[nanobanana]` 的 `ILLUSTRATOR_*` 图片参数仅对 nanobanana 生效。
`[image2-4k]` 无需重复配置比例与分辨率；会使用其内置的 16:9、4K 默认值，
实际请求像素由 `NEBULA_SIZE` 决定。切换顶部默认后端即可选择对应分组。

`--provider nebula` 对应 `[image2-4k]`；`--provider nanobanana` 对应 `[nanobanana]`；
Google 官方后端使用 `[gemini]`，通过 `google-genai` 调用原生 Google Gemini API，
不会调用 Nebula。`GEMINI_API_KEY` 使用 Google 官方密钥，`GEMINI_MODEL` 默认
`gemini-3-pro-image-preview`；可按官方模型权限更换。该分组独立配置比例和分辨率，
支持现有 `16:9`、`3:4` 以及 `2K`、`4K`，实际模型支持情况以官方接口为准。
先安装 `google-genai`，再设置顶部 `ILLUSTRATOR_IMAGE_PROVIDER=gemini`，
或用命令行 `--provider gemini` 选择原生后端。
分组只对其对应后端生效，不会写入进程环境或覆盖其他分组。
分组内的 `ILLUSTRATOR_IMAGE_PROVIDER` 会被忽略；选择默认后端只使用第一个分组之前的全局值，
或在未配置全局值时使用进程环境变量。推荐删除分组内重复的后端选择项。
分组支持注释、引号和多行值，沿用 dotenv 的 `${变量}` 插值；不支持的分组会报错。
文件一旦进入分组，后续配置均属于该分组，直到遇到下一个分组标题。

在统一 `.env` 中配置以下三项，适用于所有后端：

```dotenv
ILLUSTRATOR_SINGLE_RATIO=16:9
ILLUSTRATOR_BATCH_RATIO=16:9
ILLUSTRATOR_RESOLUTION=2K
```

两个比例均支持 `16:9`、`3:4`，分别控制单图、批量入口；请求分辨率支持
`1K`、`2K`、`4K`，仍须满足所选后端限制。image2-4k 必须使用 `16:9`、`4K`，
Gemini 官方模式仅支持原有 `2K`、`4K`，nanobanana 具体支持值以所选模型为准。
配置与后端不兼容时，在请求前报错，不自动修改配置或切换服务。

优先级：命令行 `--ratio` / `--resolution` > 所选后端分组中的配置 > `.env` 全局配置 >
进程环境变量 > 内置默认值。未配置或值为空时，比例默认 `16:9`；
分辨率按后端默认：Gemini/nanobanana 为 `2K`，image2-4k 为 `4K`。
`.env` 中的值沿用现有规则，覆盖同名进程环境变量。

```powershell
# 临时覆盖批量配置，生成竖版图片
python -X utf8 scripts/generate_illustrations.py article.md --provider nanobanana --style ticket --level h2 --ratio 3:4 --resolution 4K --output output
```

### 使用 Nebula image2-4k 生图

两个脚本均支持 `--provider gemini` 和 `--provider nebula`。未指定时读取
`ILLUSTRATOR_IMAGE_PROVIDER`，未配置则使用原有 Gemini 后端。

所有 Agent 统一在 `~/.agents/skills/document-illustrator/.env` 中配置（不要提交真实密钥）：

```dotenv
NEBULA_API_KEY=your-image2-4k-api-key
ILLUSTRATOR_IMAGE_PROVIDER=nebula
```

必须在 Nebula 创建属于 **image2-4k 分组**的令牌，并复制完整 API Key。
两个脚本只读取 `~/.agents/skills/document-illustrator/.env`，与 Codex、Claude 等 Agent
及其安装位置、当前工作目录无关。Windows 对应 `%USERPROFILE%\.agents\skills\document-illustrator\.env`。
文件中的值覆盖同名环境变量；文件不存在时仅使用现有环境变量，不搜索其他 `.env`。
命令行 `--provider` 优先于默认后端配置。

```powershell
# 单图；--cover 可用于生成封面
python -X utf8 scripts/generate_single_image.py --provider nebula --title "智慧水利" --content "监测感知、数字孪生、预警调度" --style-file styles/gradient-glass.md --output output/cover.png --cover

# 按 Markdown 二级标题批量生成
python -X utf8 scripts/generate_illustrations.py article.md --provider nebula --style ticket --level h2 --output output
```

接口依据：[Nebula image2-4k 官方文档](https://docs.apinebula.ai/docs/advanced/image/image2-4k)。
请求为 `POST https://img-api.apinebula.ai/v1/images/generations`，默认使用
`model=gpt-image-2-4k`、`size=3840x2160`、`quality=high`、`response_format=url`，
超时为 1800 秒。该分组仅支持 **16:9、4K**，选择 Nebula 时默认使用 4K；
显式传入 `--resolution 2K` 或单图 `--ratio 3:4` 会在请求前报错。
Gemini 保留原有比例，默认 2K。

`[image2-4k]` 中可通过 `NEBULA_MODEL`、`NEBULA_SIZE`、`NEBULA_QUALITY`
设置请求体的 `model`、`size`、`quality`，未配置时分别为 `gpt-image-2-4k`、
`3840x2160`、`high`。`NEBULA_SIZE` 使用像素 `宽x高` 格式，输出图片的实际像素
必须与该配置一致；此后端请求的实际尺寸由 `NEBULA_SIZE` 决定，
`ILLUSTRATOR_RESOLUTION` / `--resolution` 不会改写它。CLI 仍保留原有 16:9、4K 限制。
本地接受 `auto`、`low`、`medium`、`high` 的 quality 值；服务端是否接受具体模型、
尺寸和质量取决于令牌分组与接口能力。当前 image2-4k 文档对应的组合仍为
`gpt-image-2-4k`、`3840x2160`、`high`，不代表其他组合已获服务端支持或验证。

优先下载 `data[0].url`，无 URL 时读取 `data[0].b64_json`；下载请求不携带 API 密钥。
保存前验证实际像素为 `3840x2160`，服务端 JPEG 会按本地文件扩展名重新编码。
接口成功响应另存为 `<图片文件名>.response.json`，用于下载失败后的排查和恢复，可能含图片数据或临时链接，请妥善保存。
下载失败时先从缓存响应中的 URL 恢复下载；不要直接重新生图，以免重复计费。
此接入提供文本生图，暂未实现文档中的参考图编辑接口。

网络请求遭遇 HTTP 403 或连接未建立时，使用 `http://127.0.0.1:81` 代理重试。
生图 POST 超时或连接中断后不自动重发，应先检查服务端任务状态。
Nebula 后端使用 Python 标准库、`Pillow` 和 `python-dotenv`；无需额外安装 OpenAI SDK。

离线回归测试（不请求真实 API）：

```powershell
python -X utf8 -m unittest discover -s tests -v
```

### 步骤 1: 安装 Skill

**使用 npx（推荐）**：

```bash
npx skills add https://github.com/zhanglt/Document-illustrator-skill
```

**手动安装**：

```bash
cd ~/.claude/skills/
git clone https://github.com/zhanglt/Document-illustrator-skill.git document-illustrator
cd document-illustrator
```

### 步骤 2: 配置 API 密钥

以下步骤配置 Gemini 后端。使用 Nebula 时，按本节前面的“使用 Nebula image2-4k 生图”配置 `NEBULA_API_KEY` 即可，无需 Gemini 密钥。

1. 获取 Gemini API 密钥：[Google AI Studio](https://makersuite.google.com/app/apikey)

2. 在 `~/.agents/skills/document-illustrator/.env` 创建配置文件：

如父目录不存在，先创建；用文本编辑器创建该文件，采用 UTF-8 无 BOM 编码：

```env
GEMINI_API_KEY=your-api-key-here
```

> **安全提示**：`.env` 文件包含敏感信息，请勿提交到版本控制系统

### 步骤 3: 安装 Python 依赖

```bash
cd ~/.claude/skills/document-illustrator
pip install google-genai pillow python-dotenv
```

或使用 pip3：

```bash
pip3 install google-genai pillow python-dotenv
```

### 步骤 4: 验证安装

运行测试命令：

```bash
python3 scripts/generate_single_image.py --help
```

预期输出应显示脚本的帮助信息，表示安装成功。

## 📖 使用方法

### 每次任务先选择生图风格

每次新任务都需要用户明确选择风格。助手会展示渐变玻璃卡片、票据风格、矢量插画及自定义风格选项；
用户在本次请求中已经指定的风格可直接采用。同一任务的系列图片只需选择一次。
助手可以提出建议，但不能自动决定风格、沿用上一次任务的选择，或把内容确认视为风格选择。

单图与批量 CLI 共用风格选择入口：未传 `--style` 或 `--style-file` 时显示菜单并等待输入，
空输入不会采用默认值；输入结束仍未选择时停止，不发起生图请求。
显式参数代表本次选择，供直接 CLI 使用或助手在获得用户选择后传入；这两个参数互斥。
自定义风格通过 `--style-file` 指定。助手直接调用 Python 函数时也须先向用户确认风格，
脚本无法判断参数是否来自真实的对话选择，因此该要求同时写入 `SKILL.md`。

### 方式 1: 通过 Claude Code 使用（推荐）

这是主要的使用方式，让 Claude 智能处理整个流程。

**基本命令**：

```
帮我为这个文档生成配图：~/blog/my-article.md
```

**交互式流程**：

1. **选择图片比例**
   - 16:9（横屏）- 适合演示文稿、网站横幅
   - 3:4（竖屏）- 适合社交媒体、手机查看

2. **是否生成封面图**
   - 是 - 生成封面图 + 内容配图
   - 否 - 仅生成内容配图

3. **指定配图数量**
   - 根据文档长度，Claude 会推荐合适的数量
   - 你可以自定义需要的图片数量（建议 3-10 张）

4. **确认内容归纳**
   - Claude 会展示归纳的主题列表
   - 确认所有重要内容都被包含
   - 可以要求调整归纳结果

5. **生成配图**
   - 确认后，调用所选 Gemini 或 Nebula API 生成图片
   - 图片保存到文档所在目录的 `images/` 文件夹

**完整示例**：

```
用户: 帮我为 ~/documents/ai-evolution.md 生成配图，用渐变玻璃风格

Claude: 好的，让我先读取这个文档...
        [读取并分析文档内容]

        检测到文档长度约 3000 字。

        请选择图片比例：
        1. 16:9 (横屏)
        2. 3:4 (竖屏)

用户: 1

Claude: 是否生成封面图？
        1. 是
        2. 否

用户: 是

Claude: 期望生成多少张内容配图？
        建议范围：3-10 张
        根据文档内容，推荐生成 5 张

用户: 5

Claude: 📋 内容归纳完成

        📄 封面图内容：
        "AI 技术演化：从规则到智能"
        - 核心概念、演化路径、最佳实践

        📚 内容配图（共 5 张）：
        1. AI 技术的起源
        2. 机器学习的突破
        3. 深度学习革命
        4. 大语言模型时代
        5. 未来发展趋势

        ✓ 所有内容已覆盖，无遗漏

        确认开始生成配图吗？(Y/N)

用户: Y

Claude: 🖼️  开始生成配图...

        正在生成封面图...
        ✓ 已保存: ~/documents/images/cover.png

        正在生成第 1/5 张...
        ✓ 已保存: ~/documents/images/illustration-01.png

        ...

        ✨ 完成！共生成 6 张配图
```

### 方式 2: 直接使用 Python 脚本（高级用户）

如果你想要更多控制或进行批量处理，可以直接调用 Python 脚本。

**单图生成**：

```bash
python3 scripts/generate_single_image.py \
  --title "人工智能的未来" \
  --content "AI 技术正在快速发展..." \
  --style gradient-glass \
  --aspect-ratio 16:9 \
  --resolution 2K \
  --output ~/output/image.png
```

**参数说明**：

- `--title`: 图片标题
- `--content`: 图片内容描述
- `--style`: 风格（gradient-glass / ticket / vector-illustration）
- `--aspect-ratio`: 比例（16:9 / 3:4）
- `--resolution`: 分辨率（2K / 4K）
- `--output`: 输出文件路径

## 🔍 示例展示

### 示例 1: 技术文章配图

![技术文章示例](./examples/tech-article.png.png)

使用渐变玻璃卡片风格，16:9 比例，适合科技博客和演示文稿。

### 示例 2: 数据报告配图

![数据报告示例](./examples/data-report.png)

使用票据风格，3:4 比例，适合信息图表和社交媒体分享。

### 示例 3: 教程配图

![教程示例](./examples/tutorial.png)

使用矢量插画风格，16:9 比例，适合教育内容和故事叙述。

> **注意**：以上为示例占位符。实际生成的图片效果取决于文档内容和选择的风格。

## ⚙️ 工作原理

### 整体架构

```
📄 文档输入
    ↓
🤖 Claude 读取和理解
    ↓
💡 AI 智能归纳核心主题
    ↓
✅ 用户确认内容分配
    ↓
🎨 调用所选生图 API 生成图片
    ↓
💾 保存到本地目录
```

### 与传统方式的对比

**传统方式**：
```
代码解析标题 → 机械切分章节 → 生成配图
    ↓
❌ 依赖特定格式（## ###）
❌ 容易遗漏非标准内容
❌ 无法理解语义
```

**Document Illustrator**：
```
AI 理解内容 → 智能归纳主题 → 用户确认 → 生成配图
    ↓
✅ 格式无关，任何文档都能处理
✅ 保证内容完整性
✅ 用户可控，结果透明
```

**核心优势**：
- AI 理解文档语义，而非简单的格式解析
- 智能归纳保证内容完整，不会遗漏重要信息
- 用户确认机制，生成前可以调整归纳结果

## 👨‍💻 开发者指南

### 目录结构

```
document-illustrator/
├── README.md                 # 项目说明文档（本文件）
├── LICENSE                   # MIT 许可证
├── SKILL.md                  # Skill 定义文件（供 Claude Code 使用）
├── .env                      # 仅当此目录为 ~/.agents/skills/document-illustrator 时在此配置
├── .gitignore                # Git 忽略规则
├── scripts/                  # Python 脚本目录
│   ├── generate_illustrations.py    # 批量生成脚本（已废弃）
│   └── generate_single_image.py     # 单图生成脚本
├── styles/                   # 风格提示词目录
│   ├── gradient-glass.md            # 渐变玻璃卡片风格
│   ├── ticket.md                     # 票据风格
│   └── vector-illustration.md        # 矢量插画风格
└── examples/                 # 示例图片目录（可选）
    └── README.md                     # 示例说明
```

### 自定义风格

你可以创建自己的图片风格：

1. 在 `styles/` 目录创建新的 `.md` 文件，例如 `my-style.md`

2. 编写 Gemini 提示词：

```markdown
### 提示词

帮我生成一张[描述你的风格]的图片...

[详细的风格要求]
- 配色方案
- 构图规则
- 设计元素
- 视觉效果
```

3. 修改 `scripts/generate_single_image.py` 以支持新风格（在 `--style` 参数中添加新选项）

### 贡献指南

我们欢迎贡献！如果你想为本项目做出贡献：

1. **Fork 本仓库**

2. **创建功能分支**：
   ```bash
   git checkout -b feature/my-new-feature
   ```

3. **提交你的更改**：
   ```bash
   git commit -m "Add: 新功能描述"
   ```

4. **推送到分支**：
   ```bash
   git push origin feature/my-new-feature
   ```

5. **创建 Pull Request**

**贡献类型**：
- 新的图片风格
- 功能改进
- Bug 修复
- 文档完善
- 测试用例

**代码规范**：
- 遵循 PEP 8 Python 代码风格
- 添加必要的注释和文档字符串
- 确保代码可读性和可维护性

## ❓ 常见问题

### Q: API 密钥无效怎么办？

**A**: 请检查以下几点：
1. 确认所选后端的密钥变量正确：Gemini 使用 `GEMINI_API_KEY`，Nebula 使用 `NEBULA_API_KEY`
2. 确保 API 密钥有效且未过期
3. 检查 API 密钥是否有足够的配额
4. Gemini 可在 [Google AI Studio](https://makersuite.google.com/app/apikey) 获取密钥；Nebula 须在平台创建 image2-4k 分组令牌

### Q: 生成的图片不符合预期怎么办？

**A**: 可以尝试：
1. 在归纳展示阶段，告诉 Claude 你的期望，它会重新归纳
2. 尝试不同的风格
3. 调整配图数量（增加或减少）
4. 提供更详细的文档内容

### Q: 如何调整图片质量？

**A**: Gemini 使用 `--resolution` 参数：
- `2K`（默认）：16:9 为 2560x1440，3:4 为 1920x2560
- `4K`：16:9 为 3840x2160，3:4 为 2880x3840

Nebula image2-4k 仅支持 16:9、4K，选择该后端时默认使用 4K；不支持竖图或 2K。
4K 图片生成时间可能更长，费用以对应平台实际计费为准。

### Q: 支持批量处理多个文档吗？

**A**: 目前推荐通过 Claude Code 逐个处理文档。如果需要批量处理，可以编写自定义脚本循环调用 `generate_single_image.py`。

### Q: 成本估算？

**A**: 每张图片需要调用一次所选后端的生图 API：
- 无封面 + 3 张：3 次调用
- 有封面 + 5 张：6 次调用
- 有封面 + 10 张：11 次调用

Gemini 费用查看 [Gemini API 定价](https://ai.google.dev/pricing)；Nebula 费用以平台 image2-4k 分组的实际计费为准。

### Q: 为什么有时图片生成失败？

**A**: 可能的原因：
1. 网络连接问题 - 检查网络连接
2. API 配额用尽 - 检查 API 使用量
3. 内容过长 - 脚本会自动截取前 1000 字符
4. API 服务临时不可用 - 稍后重试

## 📊 技术规格

| 项目 | 说明 |
|------|------|
| **AI 模型** | Gemini：gemini-3-pro-image-preview；Nebula：gpt-image-2-4k |
| **图片格式** | PNG |
| **16:9 分辨率** | Gemini：2K / 4K；Nebula：仅 3840x2160 |
| **3:4 分辨率** | 仅 Gemini：2K (1920x2560) / 4K (2880x3840) |
| **支持文档格式** | Markdown, 纯文本, PDF 等（任何 Claude 可读的格式） |
| **生成时间** | 依后端负载而定；Nebula 4K 使用 1800 秒请求超时 |
| **Python 版本** | 3.8+ |
| **主要依赖** | google-genai, pillow, python-dotenv |

## 💡 最佳实践

### 1. 合理选择图片数量

**太少（1-2 张）**：
- 每张图片信息量过大
- 不容易理解和记忆
- 视觉负担重

**太多（15+ 张）**：
- 内容分散，缺乏重点
- 增加生成时间和成本
- 可能过于碎片化

**推荐**：
- 短文档（<1000 字）：3-5 张
- 中等文档（1000-3000 字）：5-7 张
- 长文档（>3000 字）：8-10 张
- 每张图片涵盖 1-2 个核心观点

### 2. 根据用途选择比例

**16:9 适合**：
- PPT 演示和幻灯片
- 网站横幅和博客配图
- 视频封面和缩略图
- 桌面端展示

**3:4 适合**：
- 社交媒体（Instagram、小红书、微信朋友圈）
- 移动端文章和 H5 页面
- 海报设计
- 竖屏视频和 Story

### 3. 封面图的使用场景

**建议生成封面图**：
- 系列文章（作为统一的视觉引导）
- 社交分享（作为预览图吸引点击）
- 文档首页（概括全文主旨）
- 演示文稿开场

**可以不生成封面图**：
- 仅内部使用的文档
- 图片数量已经足够
- 希望降低 API 调用成本
- 不需要总览性的图片

### 4. 风格选择建议

| 内容类型 | 推荐风格 | 理由 |
|---------|---------|------|
| 技术文档 | 渐变玻璃卡片 | 现代、科技感强 |
| 数据报告 | 票据风格 | 简洁、信息密度高 |
| 教程故事 | 矢量插画 | 温馨、易于理解 |
| 产品介绍 | 渐变玻璃卡片 | 高端、未来感 |
| 学术论文 | 票据风格 | 专业、严谨 |
| 儿童内容 | 矢量插画 | 可爱、友好 |

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE)。

你可以自由地：
- ✅ 使用本软件用于商业或非商业目的
- ✅ 修改本软件
- ✅ 分发本软件
- ✅ 将本软件用于私人用途

前提是：
- 📝 在所有副本中包含原始许可证和版权声明

## 🙏 致谢

本项目由以下技术驱动：

- **Claude Sonnet 4.5** - AI 智能内容分析和归纳
- **Gemini 3 Pro Image Preview** - 高质量图片生成
- **Claude Code** - Skill 执行环境

特别感谢所有为本项目做出贡献的开发者和用户。

## 📞 联系方式

- **Issues**: [GitHub Issues](https://github.com/op7418/Document-illustrator-skill/issues)
- **Discussions**: [GitHub Discussions](https://github.com/op7418/Document-illustrator-skill/discussions)

如有问题或建议，欢迎通过以上方式联系！

---

**让 AI 帮你理解和归纳内容，生成专业配图！** ✨
