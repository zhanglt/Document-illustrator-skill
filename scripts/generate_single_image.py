#!/usr/bin/env python3
"""
Document Illustrator - 单图片生成工具
由助手负责文档分析和内容归纳，此脚本调用 Gemini 或 Nebula API 生成图片
"""

import os
import sys
import argparse
from pathlib import Path
from env_config import find_and_load_env, get_provider_config
from image_api import add_provider_argument, generate_nebula, generate_nanobanana, get_provider, resolve_options, validate_options



find_and_load_env()


def get_image_dimensions(aspect_ratio, resolution):
    """
    根据比例和分辨率返回图片尺寸

    参数：
    - aspect_ratio: "16:9" 或 "3:4"
    - resolution: "2K" 或 "4K"

    返回：(width, height)
    """
    dimensions = {
        "16:9": {
            "2K": (2560, 1440),
            "4K": (3840, 2160)
        },
        "3:4": {
            "2K": (1920, 2560),
            "4K": (2880, 3840)
        }
    }

    if aspect_ratio not in dimensions:
        raise ValueError(f"不支持的比例: {aspect_ratio}，请使用 '16:9' 或 '3:4'")

    if resolution not in dimensions[aspect_ratio]:
        raise ValueError(f"不支持的分辨率: {resolution}，请使用 '2K' 或 '4K'")

    return dimensions[aspect_ratio][resolution]


def generate_image(title, content, style_prompt, output_path, aspect_ratio="16:9", resolution="2K", is_cover=False, provider=None):
    """
    调用所选 API 生成单张配图

    参数：
    - title: 图片标题
    - content: 图片内容文本
    - style_prompt: 风格提示词
    - output_path: 输出文件路径（包含文件名）
    - aspect_ratio: 宽高比 "16:9" 或 "3:4"
    - resolution: 分辨率 "2K" 或 "4K"
    - is_cover: 是否为封面图

    返回：成功返回图片路径，失败返回 None
    """
    # 组合提示词
    if is_cover:
        # 封面图的提示词，强调概括性和引导性
        full_prompt = f"""{style_prompt}

这是一张封面图，需要概括整个文档的核心信息。

标题：{title}

核心内容（需要在一张图中体现）：
{content}

要求：
- 封面图需要突出主题，具有引导性
- 信息要精炼但完整，能代表整个系列
- 视觉冲击力强，吸引读者注意
"""
    else:
        # 普通内容配图
        full_prompt = f"""{style_prompt}

根据以下内容生成配图：

标题：{title}

内容：
{content}
"""

    try:
        provider = get_provider(provider)
        validate_options(provider, aspect_ratio, resolution)
        if provider == "nebula":
            return generate_nebula(full_prompt, output_path)
        if provider == "nanobanana":
            return generate_nanobanana(full_prompt, output_path, aspect_ratio, resolution)

        from google import genai
        from google.genai import types

        api_key = get_provider_config("gemini").get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("请设置 GEMINI_API_KEY")

        # 调用 Gemini API
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model="gemini-3-pro-image-preview",  # Nano Banana Pro
            contents=full_prompt,
            config=types.GenerateContentConfig(
                response_modalities=['IMAGE'],
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                    image_size=resolution
                )
            )
        )

        # 检查响应是否有效
        if response is None:
            print(f"错误: API 返回空响应", file=sys.stderr)
            return None

        if not hasattr(response, 'parts') or response.parts is None:
            print(f"错误: API 响应中没有 parts 属性", file=sys.stderr)
            print(f"响应内容: {response}", file=sys.stderr)
            return None

        # 保存图片
        for part in response.parts:
            if part.inline_data is not None:
                image = part.as_image()

                # 确保输出目录存在
                output_dir = os.path.dirname(output_path)
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)

                image.save(output_path)
                return output_path

        print(f"警告: 图片生成失败 - 未收到图片数据", file=sys.stderr)
        return None

    except Exception as e:
        import traceback
        print(f"错误: 图片生成失败 - {e}", file=sys.stderr)
        print(f"详细错误信息:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return None


def main():
    """主流程"""
    parser = argparse.ArgumentParser(
        description='Document Illustrator - 单图片生成工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 生成普通内容配图
  python generate_single_image.py \\
    --title "AI 工具演化" \\
    --content "从 Rules 到 Skills 的演化历程..." \\
    --style-file ../styles/ticket.md \\
    --output /path/to/output/image-01.png \\
    --ratio 16:9 \\
    --resolution 2K

  # 生成封面图
  python generate_single_image.py \\
    --title "AI 编程工具完全指南" \\
    --content "本文介绍..." \\
    --style-file ../styles/gradient-glass.md \\
    --output /path/to/output/cover.png \\
    --ratio 3:4 \\
    --resolution 2K \\
    --cover

环境变量:
  GEMINI_API_KEY: Gemini 后端密钥
  NEBULA_API_KEY: Nebula image2-4k 分组密钥
  NEBULA_MODEL / NEBULA_SIZE / NEBULA_QUALITY: image2-4k 请求参数
  NEBULA_NANOBANANA_API_KEY: Nebula nanobanana 分组密钥
  NEBULA_NANOBANANA_MODEL: 模型名称，默认 gemini-3.1-flash-image
  ILLUSTRATOR_IMAGE_PROVIDER: 默认后端 gemini、nebula 或 nanobanana
  ILLUSTRATOR_SINGLE_RATIO: 单图默认比例，未配置时为 16:9
  ILLUSTRATOR_RESOLUTION: 默认请求分辨率，命令行参数优先
"""
    )

    parser.add_argument('--title', required=True, help='图片标题')
    parser.add_argument('--content', required=True, help='图片内容文本')
    parser.add_argument('--style-file', required=True, help='风格提示词文件路径')
    parser.add_argument('--output', required=True, help='输出文件路径（包含文件名）')
    parser.add_argument(
        '--ratio',
        choices=['16:9', '3:4'],
        default=None,
        help='宽高比（默认读取 ILLUSTRATOR_SINGLE_RATIO，未配置时为 16:9）'
    )
    parser.add_argument(
        '--resolution',
        choices=['1K', '2K', '4K'],
        default=None,
        help='分辨率（默认读取 ILLUSTRATOR_RESOLUTION；未配置时 Gemini/nanobanana 为 2K，Nebula 为 4K）'
    )
    parser.add_argument(
        '--cover',
        action='store_true',
        help='标记为封面图（会使用不同的提示词策略）'
    )

    add_provider_argument(parser)
    args = parser.parse_args()
    resolve_options(parser, args)

    # 读取风格提示词
    style_file_path = Path(args.style_file)
    if not style_file_path.exists():
        print(f"错误: 风格文件不存在: {args.style_file}", file=sys.stderr)
        sys.exit(1)

    with open(style_file_path, 'r', encoding='utf-8') as f:
        style_prompt = f.read()

    # 显示生成信息
    image_type = "封面图" if args.cover else "内容配图"
    print(f"正在生成{image_type}...")
    print(f"  标题: {args.title}")
    print(f"  比例: {args.ratio}")
    print(f"  分辨率: {args.resolution}")

    if args.provider == "nebula":
        print(f"  请求尺寸: {get_provider_config('nebula').get('NEBULA_SIZE', '3840x2160')}")
    elif args.provider == "nanobanana":
        print("  尺寸: 由所选模型决定，以实际输出图片为准")
    else:
        width, height = get_image_dimensions(args.ratio, args.resolution)
        print(f"  尺寸: {width}x{height}")

    # 生成图片
    result_path = generate_image(
        title=args.title,
        content=args.content,
        style_prompt=style_prompt,
        output_path=args.output,
        aspect_ratio=args.ratio,
        resolution=args.resolution,
        is_cover=args.cover,
        provider=args.provider
    )

    if result_path:
        print(f"✓ 已保存: {result_path}")
        sys.exit(0)
    else:
        print(f"✗ 生成失败", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
