---
name: document-illustrator
description: >
  基于文档内容自动生成配图。AI 智能分析文档结构，归纳核心要点，
  为每个主题生成符合特定风格的配图，并可使用 Nebula 编辑已有配图。支持封面图生成和自定义图片比例。
  使用场景：当用户需要为文档、文章、笔记生成配图，或修改已有配图时。
  关键词：配图、插图、illustration、generate images、document images
allowed-tools:
  - Read
  - Write
  - Bash(python:*)
  - Glob
  - AskUserQuestion
---

# Document Illustrator Skill

基于 AI 智能分析的文档配图生成工具。无需依赖特定格式，自动理解内容并生成专业配图。

## 🎯 核心特点

- ✨ **AI 智能归纳**：自动理解文档内容，智能提取核心主题
- 🎨 **格式无关**：支持任何格式的文档（Markdown、纯文本、PDF 等）
- 📐 **灵活比例**：支持 16:9（横屏）和 3:4（竖屏）
- 🖼️ **封面图可选**：可生成概括全文的封面图
- 🎭 **16 种风格**：原有 3 种 + 从 codex-ppt 移植的 13 种

## 🚀 使用方法

### 直接告诉 Codex

```
帮我为这个文档生成配图：/path/to/document.md
```

或者：

```
我想为这篇文章生成一些配图
```

## 📝 完整工作流程

### 每次任务必须由用户选择风格

开始任何单图、批量或自定义 Python 生图调用前，必须获得用户在**本次任务**中明确选择的风格。
用户未指定时，可根据内容推荐 2–3 种候选及简短特点，同时告知可查看下方全部 16 种风格或使用自定义风格，询问并等待选择。只读取本次选中的风格文件，不必加载全部提示词。
不得根据文档类型自行决定风格，不得沿用上一任务的风格，也不得使用 `.env` 或脚本默认值替代用户选择。
用户在本次请求中已明确指定风格，可直接采用，不重复询问。同一任务的系列配图只需选择一次。
“确认生成”或对配图内容的确认，不等于选择助手自行推荐的风格；必须先明确询问风格并得到选择。
可以推荐风格，但推荐不能代替选择。等待期间可读取文档、归纳主题，不能发起生图 API 请求。
只在获得用户选择后传入 `--style`、`--style-file` 或底层 `style_prompt`，不要自行构造这些参数绕过询问。

### 第 1 步：Codex 读取和理解文档

当你请求生成配图时，Codex 会：
1. 使用 Read 工具读取完整文档
2. AI 分析理解文档内容和结构
3. 识别核心主题和要点

**无需担心文档格式**：
- ✅ 标准 Markdown（##、###）
- ✅ 分隔线格式（======、------）
- ✅ 纯文本段落
- ✅ 任何其他格式

### 第 2 步：配置选项（风格必选，其余按已知信息补充）

Codex 会询问你的偏好：

#### 必选：本次生图风格

用户本次未指定时，先询问并等待回答：

```
请选择本次配图风格（可查看全部 16 种）：
1. 手绘技术解释风：细线草图、淡彩标注，适合技术概念
2. 清蓝汇报风：蓝青双色、结论先行，适合管理汇报
3. 其他内置风格：查看下方完整目录
4. 自定义风格：提供风格说明或风格文件
```

以上为对话推荐示例，并非 CLI 菜单编号；候选应随本次内容调整。CLI 显示全部风格并动态编号，自定义文件入口在最后。

比例和分辨率可沿用 `.env`，已知的图片数量和封面要求无需重复询问；风格不得由助手默认指定。

#### 问题 1：图片比例
```
请选择图片比例：
1. 16:9 (横屏) - 适合演示文稿、幻灯片、横屏展示
2. 3:4 (竖屏) - 适合社交媒体、手机查看、海报

请选择 (1/2):
```

#### 问题 2：封面图
```
是否生成封面图？
封面图将概括文档的所有核心信息，作为系列配图的引导。

1. 是 - 生成封面图 + 内容配图
2. 否 - 仅生成内容配图

请选择 (1/2):
```

#### 问题 3：内容配图数量
```
期望生成多少张内容配图？
建议范围：3-10 张
根据文档内容，推荐生成 6 张

请输入数字：
```

### 第 3 步：Codex 归纳内容并展示

根据你指定的数量，Codex 会智能归纳文档，然后展示给你确认：

```
📋 内容归纳完成

📄 封面图内容：（如果选择生成）
"AI 编程工具概念演化：从 Rules 到 Skills"
- 核心概念：静态上下文 vs 动态上下文
- 演化路径：Rules → Commands → MCP → Modes → Skills
- 最佳实践：简化为两个核心工具

📚 内容配图（共 6 张）：

1. Rules 的诞生与演化
   包含：早期模型幻觉问题、rules 文件的作用、静态上下文概念

2. Commands 和工作流打包
   包含：固定工作流的出现、slash command、团队分享

3. MCP Servers 带来动态能力
   包含：第三方工具集成、OAuth 认证、上下文膨胀问题

4. Modes 和 Subagents 的登场
   包含：人设提示词、系统提示词修改、可靠性设计、Hooks 确定性

5. Skills 统一动态上下文
   包含：Skills 概念、动态加载、编程工具优化

6. 最佳实践与未来展望
   包含：Rules 使用建议、Skills 探索、核心理念总结

✓ 所有内容已覆盖，无遗漏

确认开始生成配图吗？(Y/N)
```

**关键保证**：
- ✅ 内容完整：所有重要信息都会被归入某张图片
- ✅ 逻辑清晰：按照内容的自然逻辑分段
- ✅ 用户可控：展示归纳结果，等待用户确认

### 第 4 步：生成配图

确认后，Codex 调用 Python 脚本生成图片：

```
🖼️  开始生成配图...

正在生成封面图...
  ✓ 已保存: /path/to/document/images/cover.png

正在生成第 1/6 张...
  标题: Rules 的诞生与演化
  ✓ 已保存: /path/to/document/images/illustration-01.png

正在生成第 2/6 张...
  标题: Commands 和工作流打包
  ✓ 已保存: /path/to/document/images/illustration-02.png

...

✨ 完成！共生成 7 张配图（1 张封面 + 6 张内容）
```

### 第 5 步：输出结果

**输出位置**：文档所在目录下的 `images/` 文件夹

```
/path/to/your/document/
└── images/
    ├── cover.png              # 封面图（如果选择生成）
    ├── illustration-01.png    # 第 1 张内容配图
    ├── illustration-02.png    # 第 2 张内容配图
    ├── illustration-03.png
    ├── illustration-04.png
    ├── illustration-05.png
    └── illustration-06.png
```

## 🎨 16 种风格说明

目前共 16 种内置风格：原有 3 种，以及从 codex-ppt 移植的 12 种内置风格和自定义「清蓝汇报风」。移植风格已适配文档封面与正文配图，画幅服从调用参数，支持 `16:9`、`3:4`；运行时不依赖 codex-ppt。原有三种风格保留原提示词。

| 风格 | CLI 标识 | 特点与适用场景 | 提示词 |
|---|---|---|---|
| 渐变玻璃卡片 | `gradient-glass` | 玻璃质感、极光渐变，适合科技与产品介绍 | [风格文件](styles/gradient-glass.md) |
| 票据风格 | `ticket` | 黑白对比、票券分区，适合简报与数据报告 | [风格文件](styles/ticket.md) |
| 矢量插画 | `vector-illustration` | 扁平插画、柔和配色，适合场景与概念解释 | [风格文件](styles/vector-illustration.md) |
| 党政红风格 | `government-red` | 庄重红金、正式排版，适合政策与公共服务 | [风格文件](styles/government-red.md) |
| 创意杂志风 | `creative-editorial` | 非对称版式、醒目标题，适合品牌与创意主题 | [风格文件](styles/creative-editorial.md) |
| 复古扁平插画风 | `retro-flat` | 复古配色、等粗描边，适合文化与故事 | [风格文件](styles/retro-flat.md) |
| 手绘技术解释风 | `handdrawn-tech` | 细线草图、淡彩标注，适合技术概念 | [风格文件](styles/handdrawn-tech.md) |
| 手绘白板风 | `whiteboard` | 白板笔迹、圈画箭头，适合教学与讨论 | [风格文件](styles/whiteboard.md) |
| 教学课件风 | `teaching-courseware` | 学术蓝、知识层级，适合课程与案例讲解 | [风格文件](styles/teaching-courseware.md) |
| 数据仪表盘风 | `data-dashboard` | 明亮数据卡、清晰图表，适合指标与趋势 | [风格文件](styles/data-dashboard.md) |
| 清爽专业风 | `clean-professional` | 浅底蓝青、结构清晰，适合方案与工作说明 | [风格文件](styles/clean-professional.md) |
| 温暖手工风 | `warm-handmade` | 纸张拼贴、柔和色彩，适合生活与人文故事 | [风格文件](styles/warm-handmade.md) |
| 电子墨水杂志风 | `eink-editorial` | 墨色纸感、杂志字体，适合观点与专题 | [风格文件](styles/eink-editorial.md) |
| 科研答辩风 | `research-defense` | 学术蓝红、证据导向，适合研究与技术路线 | [风格文件](styles/research-defense.md) |
| 麦肯锡风格 | `consulting` | 理性蓝灰、结构化隐喻，适合商业分析 | [风格文件](styles/consulting.md) |
| 清蓝汇报风 | `clear-blue-report` | 蓝青双色、结论先行，适合管理与行业汇报 | [风格文件](styles/clear-blue-report.md) |

例如，在本次任务已选择手绘技术解释风后：

```powershell
python -X utf8 scripts/generate_single_image.py --provider nanobanana --style handdrawn-tech --title "技术原理" --content "本次确认的配图内容" --ratio 3:4 --resolution 2K --output output/technical.png
python -X utf8 scripts/generate_illustrations.py article.md --provider nanobanana --style clear-blue-report --level h2 --ratio 16:9 --resolution 2K --output output
```

两条命令分别演示两种风格，执行前应确认本次任务选择。Nebula image2-4k 的比例与分辨率限制仍以该后端要求为准。

### 原有三种风格详解


### 1. 渐变玻璃卡片风格 (gradient-glass)

**特点**：
- Apple Keynote 风格的极简主义
- 玻璃拟态（Glassmorphism）设计
- 深邃虚空黑或纯净陶瓷白基底
- 流动的极光渐变色
- 3D 玻璃物体和发光效果

**适用场景**：
- 科技产品介绍
- 数据分析报告
- 未来趋势展望
- 产品功能演示

### 2. 票据风格 (ticket)

**特点**：
- 数字极简票券设计
- 高度对比的黑白配色
- 类似登机牌、门票的结构
- 精确的几何分区
- 中英混排，多向文字布局

**适用场景**：
- 信息图表
- 统计数据展示
- 时间线和流程图
- 要点总结

### 3. 矢量插画风格 (vector-illustration)

**特点**：
- 扁平化矢量插画
- 统一粗细的黑色轮廓线
- 复古柔和的配色
- 几何化处理
- 横向全景式构图

**适用场景**：
- 故事叙述
- 概念解释
- 教育内容
- 品牌宣传

## 💡 使用示例

### 示例 1：完整流程

```
用户: 帮我为 ~/blog/ai-tools.md 生成配图，用票据风格

Codex: 好的，让我先读取这个文档...
        [读取文档，分析内容]

        检测到文档长度约 3000 字，内容涉及 AI 工具演化。

        请选择图片比例：
        1. 16:9 (横屏)
        2. 3:4 (竖屏)

用户: 1

Codex: 是否生成封面图？
        1. 是
        2. 否

用户: 是

Codex: 期望生成多少张内容配图？
        建议范围：3-10 张
        根据文档内容，推荐生成 5 张

用户: 5

Codex: [展示归纳的 5 个主题]
        确认开始生成配图吗？

用户: Y

Codex: [调用 Python 脚本生成 6 张图片]
        ✨ 完成！配图已保存到 ~/blog/images/
```

### 示例 2：纯文本文档

```
用户: 为这个纯文本笔记生成配图

Codex: [读取笔记，即使没有任何标题也能理解内容]
        [智能识别 3 个核心主题]
        [询问配置、展示归纳、生成配图]
```

### 示例 3：自定义数量

```
用户: 我想要 8 张图，竖屏的，不要封面

Codex: 好的，16:9 竖屏，不生成封面，8 张内容配图。
        [将文档归纳为 8 个主题]
        [展示归纳结果，用户确认后生成]
```

## 🔧 技术细节

### 图片规格

以下比例和分辨率适用于 Gemini；Nebula image2-4k 仅支持 16:9、3840x2160。
用户选择 Nebula 时，直接使用 4K；如用户要求 2K 或竖图，先说明限制并确定受支持方案。

| 比例 | 分辨率 | 适用场景 |
|------|--------|----------|
| 16:9 | 2560x1440 (2K) | 演示文稿、横屏展示 |
| 3:4 | 1920x2560 | 社交媒体、竖屏查看 |

可选 4K 分辨率：
- 16:9 → 3840x2160
- 3:4 → 2880x3840

### API 调用

各后端读取统一 `.env` 对应分组的 URL：`[nanobanana]` 使用
`NEBULA_NANOBANANA_BASE_URL=https://img-api.apinebula.ai/v1beta/models`，脚本仅追加
`/{model}:generateContent`，API 版本升级时修改此配置；`[image2-4k]` 使用完整接口地址
`NEBULA_ENDPOINT=https://img-api.apinebula.ai/v1/images/generations`；
`[gemini]` 使用 `GEMINI_BASE_URL=https://generativelanguage.googleapis.com`，
由 SDK 追加 API 版本和模型路径。未配置或留空时沿用这些默认地址。
三个后端共用的代理在第一个分组之前配置，例如 `PROXY=http://127.0.0.1:81`；
Nebula 与 nanobanana 在 HTTP 403 或明确未建立连接时使用它重试，Gemini SDK 直接通过它发送请求。
不配置或留空时不使用此代理；付费 POST 超时后不自动重发。

- **Gemini 模型**：`gemini-3-pro-image-preview`（脚本当前默认值）
- **Nebula 模型**：`gpt-image-2-4k`，使用 image2-4k 分组令牌
- **成本**：每张图片 = 1 次 API 调用
- **速度**：取决于后端负载；Nebula 4K 请求超时为 1800 秒

### 后端选择与 Nebula 调用

#### 原生 Gemini 分组

用户指定 Google 原生 Gemini 时，传入 `--provider gemini`，或设置顶部
`ILLUSTRATOR_IMAGE_PROVIDER=gemini`。统一 `.env` 的 `[gemini]` 分组配置
`GEMINI_API_KEY`（Google 官方密钥）、`GEMINI_MODEL`（默认 `gemini-3-pro-image-preview`），
以及该后端独立的 `ILLUSTRATOR_SINGLE_RATIO`、`ILLUSTRATOR_BATCH_RATIO`、
`ILLUSTRATOR_RESOLUTION`。缺省比例 16:9、分辨率 2K；支持现有 16:9 / 3:4、2K / 4K。
通过 `google-genai` SDK 调用 Google 官方服务，不使用 Nebula 密钥或接口。
两个脚本均支持该分组，命令行参数仍优先于分组图片参数；不要复用其他分组的配置。

#### nanobanana 分组

用户指定 nanobanana 时，两个脚本均传入 `--provider nanobanana`。
统一 `.env` 中使用专用 `NEBULA_NANOBANANA_API_KEY`（nanobanana 分组令牌），
不复用 image2-4k 的密钥。`NEBULA_NANOBANANA_MODEL` 默认为 `gemini-3.1-flash-image`，
可指定令牌支持的其他模型；`ILLUSTRATOR_IMAGE_PROVIDER=nanobanana` 可设为默认。
单图、批量均支持 16:9、3:4；可请求 1K、2K、4K，默认 2K，
具体支持值及实际像素由所选模型决定，不套用 image2-4k 的 4K 横图限制。

统一 `.env` 使用 `ILLUSTRATOR_SINGLE_RATIO` 设置单图默认比例，
`ILLUSTRATOR_BATCH_RATIO` 设置批量默认比例，`ILLUSTRATOR_RESOLUTION` 设置默认请求分辨率。
两个入口均支持 `--ratio`、`--resolution` 覆盖配置。不配置或值为空时，比例为 16:9，
分辨率使用后端默认值（Gemini/nanobanana 为 2K，image2-4k 为 4K）。
这些设置适用于所有后端；与后端限制冲突时，请求前报错，须调整配置或显式覆盖。

统一 `.env` 兼容平铺格式和 `[image2-4k]`、`[nanobanana]`、`[gemini]` 分组。
默认 `ILLUSTRATOR_IMAGE_PROVIDER` 必须放在第一个分组之前，分组内的同名项会被忽略。
`nebula` 使用 `[image2-4k]`，其余后端使用同名分组；密钥、模型和图片参数按所选分组读取。
参数优先级：命令行 > 对应分组 > 全局配置 > 进程环境 > 内置默认值。
推荐仅在 `[nanobanana]` 配置 `ILLUSTRATOR_SINGLE_RATIO`、`ILLUSTRATOR_BATCH_RATIO`、
`ILLUSTRATOR_RESOLUTION`；`[image2-4k]` 配置 `NEBULA_API_KEY`、`NEBULA_MODEL`、
`NEBULA_SIZE`、`NEBULA_QUALITY`，不必重复比例和分辨率。其缺省值为 16:9、4K，
不会继承 `[nanobanana]` 的 2K。
不要将各分组参数合并成同一组全局环境变量；完整示例见 README 的配置比例与分辨率章节。

```powershell
python -X utf8 scripts/generate_single_image.py --provider nanobanana --title "主题" --content "配图内容" --style-file styles/ticket.md --ratio 3:4 --resolution 2K --output output/banana.png
python -X utf8 scripts/generate_illustrations.py article.md --provider nanobanana --style ticket --level h2 --resolution 2K
```

调用 Gemini 原生 `POST /v1beta/models/{model}:generateContent`，从 `inlineData`
解码并验证图片，不持久化完整 Base64 响应。不需要 Google SDK。
当前接入仅支持文本生图；超时后不自动重发收费任务。
详见 [README.md](README.md#使用-nebula-nanobanana-分组生图) 和
[官方接口说明](https://docs.apinebula.ai/docs/advanced/image/nanobanana)。

#### 原有 image2-4k 分组

两个脚本支持 `--provider gemini|nebula`。不指定时读取 `ILLUSTRATOR_IMAGE_PROVIDER`，
未配置时使用 Gemini。用户明确指定 Nebula 时，传入 `--provider nebula`；不要改用其他服务。
在统一路径 `~/.agents/skills/document-illustrator/.env` 配置 `NEBULA_API_KEY`，或使用同名环境变量；令牌须属于 image2-4k 分组。
Nebula 无需 Gemini 密钥或 Google SDK，仍需要 `Pillow` 和 `python-dotenv`。

```powershell
python -X utf8 scripts/generate_single_image.py --provider nebula --title "主题" --content "已确认的配图内容" --style-file styles/ticket.md --output output/image-01.png --resolution 4K
python -X utf8 scripts/generate_illustrations.py article.md --provider nebula --style ticket --level h2 --resolution 4K
```

脚本调用 `POST https://img-api.apinebula.ai/v1/images/generations`，默认使用
`gpt-image-2-4k`、`3840x2160`、`quality=high`、`response_format=url`。
`[image2-4k]` 可配置 `NEBULA_MODEL`、`NEBULA_SIZE`、`NEBULA_QUALITY`，分别设置
请求的 `model`、`size`、`quality`；缺失时沿用上述默认值。保存前按 `NEBULA_SIZE`
验证实际像素，`--resolution` 不会覆盖该像素配置。当前分组官方支持组合仍以上述默认值为准，
更改配置并不代表服务端支持其他模型、尺寸或质量。
优先读取 URL，兼容 Base64；保存前验证真实像素，将服务端 JPEG 转为本地扩展名对应的格式。
接口响应保存为 `<图片文件名>.response.json`，下载失败时先复用其中的临时链接恢复下载。
POST 超时后任务状态可能未知，不自动重发；先确认服务端状态，避免重复计费。
HTTP 403 或连接尚未建立时会尝试共享 `.env` 顶层 `PROXY` 指定的代理。
参考图编辑使用独立入口 `scripts/edit_image.py`，不自动加入批量生图流程。
当用户要求保留已有图片的主体、风格或布局，只修改指定部分时，先确认要保留和修改的内容；
用户未指定编辑风格时沿用原图风格，不把生图任务的风格选择规则强加到局部编辑。
传入一张或多张本地参考图，输出到新路径，保留原图；不要覆盖已有输出或响应缓存。

```powershell
python -X utf8 scripts/edit_image.py --image input.png --prompt "保留主体与布局，只把背景改为浅蓝色" --output output/edited.png
```

编辑调用 `POST https://img-api.apinebula.ai/v1/images/edits`，上传 multipart `image`，
沿用 `[image2-4k]` 的 `NEBULA_API_KEY`、`NEBULA_MODEL`、`NEBULA_SIZE`、`NEBULA_QUALITY`；
独立的 `NEBULA_EDITS_ENDPOINT` 可覆盖编辑接口地址。保存与尺寸验证沿用生图逻辑。
请求超时后任务状态可能未知，不自动重发；下载失败时先使用响应缓存恢复，避免重复计费。

完整配置说明与离线测试命令见 [README.md](README.md#使用-nebula-image2-4k-生图)，
接口参数以 [官方文档](https://docs.apinebula.ai/docs/advanced/image/image2-4k) 为依据。

### 环境要求

**必需**：
```bash
pip install google-genai pillow python-dotenv
```

**API 密钥**：
- Codex、Claude 等所有 Agent 统一读取 `~/.agents/skills/document-illustrator/.env`
- Windows 对应 `%USERPROFILE%\.agents\skills\document-illustrator\.env`
- 仅加载该文件，其值覆盖同名环境变量；文件不存在时仅使用现有环境变量，不搜索其他位置
- Gemini 使用 `GEMINI_API_KEY`，Nebula 使用 `NEBULA_API_KEY`
- nanobanana 分组使用 `NEBULA_NANOBANANA_API_KEY`；模型配置见上方分组说明

## 📊 内容归纳原则

Claude 归纳内容时遵循以下原则：

### 1. 完整性优先

- ✅ 所有重要信息都会被包含
- ✅ 不会遗漏关键概念
- ✅ 保留原文的核心观点

### 2. 逻辑清晰

- 按照内容的自然逻辑分段
- 相关内容归为一组
- 保持叙事的连贯性

### 3. 平衡分配

- 每张图片包含相似的信息量
- 避免某张过于拥挤或空洞
- 根据内容重要性调整

### 4. 用户可控

- 展示归纳结果给用户确认
- 用户可以要求调整
- 确认后才开始生成

## 🐛 故障排除

### 问题 1：API 密钥错误

**错误信息**：
```
Error: Invalid API key
```

**解决方案**：
1. 检查 `.env` 中对应后端的 `GEMINI_API_KEY` 或 `NEBULA_API_KEY`；Nebula 同时检查令牌分组
2. 确保 API 密钥有效且未过期
3. 获取新密钥：https://makersuite.google.com/app/apikey

### 问题 2：内容归纳不理想

**问题**：归纳的主题不符合预期

**解决方案**：
1. 在归纳展示阶段，告诉 codex 你的期望
2. codex 会重新归纳并调整
3. 确认满意后再开始生成

### 问题 3：图片生成失败

**可能原因**：
- 网络连接问题
- API 配额用尽
- 内容过长超过限制

**解决方案**：
1. 检查网络连接
2. 检查 API 配额
3. 尝试增加图片数量（分散内容）

## 💰 成本估算

| 图片数量 | API 调用次数 | 预估成本 |
|---------|-------------|---------|
| 无封面 + 3 张 | 3 次 | 低 |
| 有封面 + 5 张 | 6 次 | 中 |
| 有封面 + 10 张 | 11 次 | 较高 |

**建议**：
- 短文档（<1000字）：3-5 张
- 中等文档（1000-3000字）：5-7 张
- 长文档（>3000字）：8-10 张

## 📚 最佳实践

### 1. 合理选择图片数量

**太少**：
- 每张图片信息量过大
- 不容易理解和记忆

**太多**：
- 内容分散
- 增加成本和生成时间

**推荐**：
- 根据文档长度选择
- 每张图片涵盖 1-2 个核心观点

### 2. 根据用途选择比例

**16:9 适合**：
- PPT 演示
- 网站横幅
- 视频封面
- 博客配图（桌面端）

**3:4 适合**：
- 社交媒体（Instagram、小红书）
- 移动端文章
- 海报设计
- 竖屏视频

### 3. 封面图的使用

**建议生成封面图的场景**：
- 系列文章（作为统一引导）
- 社交分享（作为预览图）
- 文档首页（概括全文）

**可以不生成的场景**：
- 仅内部使用
- 图片数量已足够
- 希望降低成本

### 4. 风格选择建议

**技术文档** → 渐变玻璃卡片风格
**数据报告** → 票据风格
**教程故事** → 矢量插画风格
**产品介绍** → 渐变玻璃卡片风格

## 🔄 工作原理

### 传统方式（已废弃）

```
[代码] 读取文档 → 识别 ## ### 标题 → 机械切分
       ↓
    依赖特定格式
    容易遗漏内容
    不够智能
```

### 新方式（当前实现）

```
[Claude] 读取文档 → AI 理解内容 → 智能归纳主题
         ↓
      格式无关
      内容完整
      用户可控
```

**核心区别**：
- ❌ 旧方式：依赖代码解析，只能处理标准格式
- ✅ 新方式：AI 理解内容，任何格式都能处理

## 🎯 与其他工具的对比

| 功能 | Document Illustrator | 传统 PPT 工具 | AI 图片生成器 |
|------|---------------------|--------------|--------------|
| 理解文档内容 | ✅ AI 智能理解 | ❌ 需要手动 | ❌ 需要手动输入 |
| 格式依赖 | ✅ 格式无关 | ❌ 依赖特定格式 | ✅ 无依赖 |
| 内容完整性 | ✅ 自动验证 | ⚠️ 手动确保 | ❌ 无法保证 |
| 批量生成 | ✅ 一次生成多张 | ❌ 逐张制作 | ⚠️ 需要多次输入 |
| 风格一致性 | ✅ 自动保持 | ⚠️ 手动调整 | ⚠️ 需要重复提示词 |

## 📞 获取帮助

如有问题或建议：
1. 直接在 codex 中询问
2. 检查 Skill 目录：`~/.agents/skills/document-illustrator

---

**让 AI 帮你理解和归纳内容，生成专业配图！** ✨
