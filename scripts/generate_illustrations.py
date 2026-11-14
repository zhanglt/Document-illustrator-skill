#!/usr/bin/env python3
"""
Document Illustrator - 为文档生成配图
基于文档内容和风格提示词，使用 Gemini 或 Nebula API 生成配图
"""

import os
import sys
import re
import argparse
from pathlib import Path
from style_selection import add_style_arguments, choose_style, resolve_style
from env_config import find_and_load_env, get_provider_config
from image_api import add_provider_argument, resolve_options



find_and_load_env()


def analyze_document_structure(doc_path):
    """
    分析文档的标题层级结构

    返回：{
        'h2': ['标题1', '标题2', ...],
        'h3': ['标题1', '标题2', ...],
        'h4': ['标题1', '标题2', ...],
        'sections': [
            {'level': 'h2', 'title': '...', 'content': '...'},
            {'level': 'h3', 'title': '...', 'content': '...'},
            ...
        ]
    }
    """
    if not Path(doc_path).exists():
        print(f"错误: 文件不存在: {doc_path}", file=sys.stderr)
        sys.exit(1)

    with open(doc_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 使用正则表达式识别标题
    # 匹配 ##、###、#### 等标题（不包括 # 一级标题）
    heading_pattern = re.compile(r'^(#{2,4})\s+(.+)$', re.MULTILINE)
    headings = heading_pattern.findall(content)

    if not headings:
        print("错误: 文档中没有找到标题（##、###、####）", file=sys.stderr)
        print("请确保文档使用 Markdown 格式并包含标题", file=sys.stderr)
        sys.exit(1)

    # 统计各级标题
    h2_titles = []
    h3_titles = []
    h4_titles = []

    for level, title in headings:
        if level == '##':
            h2_titles.append(title)
        elif level == '###':
            h3_titles.append(title)
        elif level == '####':
            h4_titles.append(title)

    # 提取每个小节的内容
    sections = []

    # 将文档按标题分割
    lines = content.split('\n')
    current_section = None

    for i, line in enumerate(lines):
        # 检查是否是标题行
        match = re.match(r'^(#{2,4})\s+(.+)$', line)

        if match:
            # 保存上一个小节
            if current_section:
                sections.append(current_section)

            # 开始新小节
            level_marks, title = match.groups()
            level = 'h' + str(len(level_marks))

            current_section = {
                'level': level,
                'title': title,
                'content': '',
                'line_start': i
            }
        elif current_section:
            # 累积当前小节的内容
            current_section['content'] += line + '\n'

    # 添加最后一个小节
    if current_section:
        sections.append(current_section)

    # 清理每个小节的内容（移除首尾空白）
    for section in sections:
        section['content'] = section['content'].strip()

    return {
        'h2': h2_titles,
        'h3': h3_titles,
        'h4': h4_titles,
        'sections': sections
    }


def merge_sections_by_level(sections, target_level):
    """
    根据目标层级智能合并章节，确保不丢失内容

    规则：
    - 如果选择 h2：将所有 h3、h4 内容合并到对应的 h2 父章节下
    - 如果选择 h3：将所有 h4 内容合并到对应的 h3 父章节下
    - 如果选择 h4：保持原样

    返回：合并后的章节列表
    """
    level_hierarchy = {'h2': 2, 'h3': 3, 'h4': 4}
    target_level_num = level_hierarchy[target_level]

    merged_sections = []
    current_parent = None

    for section in sections:
        section_level_num = level_hierarchy[section['level']]

        if section_level_num == target_level_num:
            # 找到目标层级的章节
            if current_parent:
                # 保存上一个父章节
                merged_sections.append(current_parent)

            # 创建新的父章节
            current_parent = {
                'level': section['level'],
                'title': section['title'],
                'content': section['content'],
                'merged_from': [section['title']]  # 记录合并来源
            }

        elif section_level_num > target_level_num:
            # 子章节，需要合并到当前父章节
            if current_parent:
                # 添加子章节的内容
                if current_parent['content']:
                    current_parent['content'] += '\n\n'

                # 添加子章节标题和内容
                current_parent['content'] += f"【{section['title']}】\n{section['content']}"
                current_parent['merged_from'].append(section['title'])
            else:
                # 没有父章节，说明文档结构有问题，作为独立章节处理
                merged_sections.append({
                    'level': section['level'],
                    'title': section['title'],
                    'content': section['content'],
                    'merged_from': [section['title']]
                })

        elif section_level_num < target_level_num:
            # 比目标层级更高的章节（比如选了 h3 但遇到 h2）
            # 保存当前父章节
            if current_parent:
                merged_sections.append(current_parent)

            # 这个高层级章节作为独立章节
            merged_sections.append({
                'level': section['level'],
                'title': section['title'],
                'content': section['content'],
                'merged_from': [section['title']]
            })
            current_parent = None

    # 保存最后一个父章节
    if current_parent:
        merged_sections.append(current_parent)

    return merged_sections


def verify_content_coverage(original_sections, merged_sections):
    """
    验证内容覆盖度，确保没有章节被遗漏

    返回：{
        'all_covered': True/False,
        'original_count': 原始章节数,
        'merged_count': 合并后章节数,
        'coverage_report': [
            {'title': '...', 'status': 'included/merged', 'merged_into': '...'},
            ...
        ]
    }
    """
    # 收集所有原始章节标题
    original_titles = {s['title'] for s in original_sections}

    # 收集合并后覆盖的所有标题
    covered_titles = set()
    coverage_report = []

    for merged in merged_sections:
        covered_titles.update(merged['merged_from'])

        if len(merged['merged_from']) == 1:
            # 未合并的章节
            coverage_report.append({
                'title': merged['title'],
                'status': 'independent',
                'merged_into': None
            })
        else:
            # 合并的章节
            main_title = merged['merged_from'][0]
            sub_titles = merged['merged_from'][1:]

            coverage_report.append({
                'title': main_title,
                'status': 'parent',
                'merged_into': None
            })

            for sub_title in sub_titles:
                coverage_report.append({
                    'title': sub_title,
                    'status': 'merged',
                    'merged_into': main_title
                })

    # 检查是否有遗漏
    missing_titles = original_titles - covered_titles

    for missing in missing_titles:
        coverage_report.append({
            'title': missing,
            'status': 'MISSING',
            'merged_into': None
        })

    return {
        'all_covered': len(missing_titles) == 0,
        'original_count': len(original_sections),
        'merged_count': len(merged_sections),
        'missing_count': len(missing_titles),
        'coverage_report': coverage_report
    }


def prompt_user_for_granularity(structure):
    """
    根据文档结构，让用户选择生成粒度

    返回：选中的标题级别（'h2', 'h3', 或 'h4'）
    """
    print(f"\n检测到文档结构：")
    print(f"- {len(structure['h2'])} 个二级标题 (##)")
    print(f"- {len(structure['h3'])} 个三级标题 (###)")
    print(f"- {len(structure['h4'])} 个四级标题 (####)")

    print(f"\n请选择生成粒度：")

    options = []
    if len(structure['h2']) > 0:
        print(f"1. 粗粒度 - 按二级标题生成 ({len(structure['h2'])} 张图片)")
        options.append(('1', 'h2'))

    if len(structure['h3']) > 0:
        print(f"2. 中等粒度 - 按三级标题生成 ({len(structure['h3'])} 张图片)")
        options.append(('2', 'h3'))

    if len(structure['h4']) > 0:
        print(f"3. 细粒度 - 按四级标题生成 ({len(structure['h4'])} 张图片)")
        options.append(('3', 'h4'))

    if not options:
        print("错误: 文档中没有找到任何标题", file=sys.stderr)
        sys.exit(1)

    while True:
        valid_choices = [opt[0] for opt in options]
        choice = input(f"\n请输入选择 ({'/'.join(valid_choices)}): ").strip()

        for opt_choice, opt_level in options:
            if choice == opt_choice:
                return opt_level

        print(f"无效选择，请输入 {' 或 '.join(valid_choices)}")


def prompt_user_for_style():
    return choose_style()


def extract_core_prompt(style_file_path):
    """
    从风格文件中智能提取核心提示词部分

    规则：
    1. 对于"渐变玻璃卡片风格"：提取"### 提示词"之后的内容
    2. 对于"票据风格"：提取整个文件内容（因为整个文件就是提示词模板）
    3. 对于"矢量插画风格"：提取"### 提示词"之后的内容

    通用策略：
    - 查找"提示词"、"prompt"等关键词
    - 排除"概述"、"适配模型"、"适用模型"等说明性章节
    - 保留核心的风格描述和要求
    """
    with open(style_file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 尝试匹配 "### 提示词" 或 "## 提示词"
    prompt_section_pattern = re.compile(r'###?\s+提示词(.+)', re.DOTALL)
    match = prompt_section_pattern.search(content)

    if match:
        # 提取提示词之后的内容
        extracted = match.group(1).strip()

        # 移除可能的尾部章节（如"需要生成 PPT 的内容："）
        # 查找"需要生成"、"文本信息"等标记
        end_markers = [
            '需要生成 PPT 的内容：',
            '需要生成 PPT 的内容:',
            '文本信息：',
            '文本信息:',
            '内容：',
            '内容:'
        ]

        for marker in end_markers:
            if marker in extracted:
                extracted = extracted.split(marker)[0].strip()
                break

        return extracted

    # 如果没有找到"提示词"章节，尝试更智能的提取
    # 查找"帮我"、"基于"等开头的段落
    if content.startswith('帮我') or content.startswith('基于'):
        # 票据风格的情况：整个文件就是提示词
        # 但要移除"文本信息："之后的部分
        for marker in ['文本信息：', '文本信息:']:
            if marker in content:
                content = content.split(marker)[0].strip()
                break
        return content

    # 如果以上都不匹配，排除说明性章节
    # 移除"## 概述"、"### 适配模型"等章节
    lines = content.split('\n')
    filtered_lines = []
    skip = False

    for line in lines:
        # 检查是否是需要跳过的章节
        if re.match(r'##?\s+(概述|适配模型|适用模型及软件)', line):
            skip = True
            continue
        elif re.match(r'##?\s+', line):
            # 遇到其他章节，停止跳过
            skip = False

        if not skip:
            filtered_lines.append(line)

    return '\n'.join(filtered_lines).strip()


def generate_illustration(section_title, section_content, style_prompt, output_dir, index,
                          resolution='2K', provider=None, aspect_ratio="16:9"):
    from generate_single_image import generate_image

    image_path = os.path.join(output_dir, f"illustration-{index:02d}.png")
    return generate_image(
        section_title, section_content, style_prompt, image_path,
        aspect_ratio=aspect_ratio, resolution=resolution, provider=provider,
    )


def main():
    """主流程"""
    parser = argparse.ArgumentParser(
        description='Document Illustrator - 为文档生成配图',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python generate_illustrations.py document.md
  python generate_illustrations.py document.md --resolution 4K
  python generate_illustrations.py document.md --output /custom/output

环境变量:
  GEMINI_API_KEY: Gemini 后端密钥
  GEMINI_MODEL: 原生 Gemini 模型，默认 gemini-3-pro-image-preview
  NEBULA_API_KEY: Nebula image2-4k 分组密钥
  NEBULA_MODEL / NEBULA_SIZE / NEBULA_QUALITY: image2-4k 请求参数
  NEBULA_NANOBANANA_API_KEY: Nebula nanobanana 分组密钥
  NEBULA_NANOBANANA_MODEL: 模型名称，默认 gemini-3.1-flash-image
  CIHEBI_IMAGE_API_KEY / CIHEBI_IMAGE_MODEL / CIHEBI_IMAGE_SIZE / CIHEBI_IMAGE_QUALITY: cihebi 分组配置
  ILLUSTRATOR_IMAGE_PROVIDER: 必填且锁定后端，gemini、image2-4k、nanobanana 或 cihebi
  ILLUSTRATOR_BATCH_RATIO: 批量默认比例，未配置时为 16:9
  ILLUSTRATOR_RESOLUTION: 默认请求分辨率，命令行参数优先
"""
    )

    parser.add_argument('document', help='文档路径')
    parser.add_argument(
        '--ratio', choices=['16:9', '3:4'], default=None,
        help='宽高比（cihebi 不适用；其他后端默认读取 ILLUSTRATOR_BATCH_RATIO）'
    )
    parser.add_argument(
        '--output',
        default=None,
        help='输出目录（默认：文档所在目录下的 images/ 文件夹）'
    )
    parser.add_argument(
        '--resolution',
        choices=['1K', '2K', '4K'],
        default=None,
        help='分辨率（cihebi 不适用；其他后端默认读取 ILLUSTRATOR_RESOLUTION）'
    )
    add_style_arguments(parser)
    parser.add_argument(
        '--level',
        choices=['h2', 'h3', 'h4'],
        help='标题层级（h2: 二级标题, h3: 三级标题, h4: 四级标题）'
    )

    add_provider_argument(parser)
    args = parser.parse_args()
    resolve_options(parser, args, batch=True)
    style_file = resolve_style(parser, args)

    print("=" * 60)
    print("Document Illustrator - 文档配图生成器")
    print("=" * 60)
    print()

    # 1. 分析文档结构
    print("📖 分析文档结构...")
    structure = analyze_document_structure(args.document)

    # 2. 用户选择生成粒度
    if args.level:
        # 非交互模式：使用命令行参数
        selected_level = args.level
        level_counts = {
            'h2': len(structure['h2']),
            'h3': len(structure['h3']),
            'h4': len(structure['h4'])
        }
        print(f"\n🎯 使用指定粒度: {selected_level} ({level_counts[selected_level]} 张图片)")
    else:
        # 交互模式：提示用户选择
        print("\n🎯 选择生成粒度...")
        selected_level = prompt_user_for_granularity(structure)

    # 3. 用户选择风格
    style_prompt = extract_core_prompt(style_file)

    # 显示提取的风格提示词预览（前 200 个字符）
    print(f"\n✓ 已加载风格提示词")
    print(f"  预览: {style_prompt[:200]}...")

    # 4. 创建输出目录（在文档所在目录下）
    doc_dir = os.path.dirname(os.path.abspath(args.document))

    if args.output:
        output_dir = os.path.join(args.output, "images")
    else:
        # 默认：文档所在目录下的 images/ 文件夹
        output_dir = os.path.join(doc_dir, "images")

    os.makedirs(output_dir, exist_ok=True)

    print(f"\n📁 输出目录: {output_dir}")

    # 4.5. 智能合并章节并验证内容覆盖
    print(f"\n📋 合并子章节内容...")
    merged_sections = merge_sections_by_level(structure['sections'], selected_level)

    print(f"\n✓ 已合并章节")
    print(f"  原始章节数: {len(structure['sections'])}")
    print(f"  合并后章节数: {len(merged_sections)}")

    # 验证内容覆盖度
    print(f"\n🔍 验证内容覆盖...")
    verification = verify_content_coverage(structure['sections'], merged_sections)

    if verification['all_covered']:
        print(f"✓ 所有内容已覆盖，无遗漏")
    else:
        print(f"⚠️  警告: 发现 {verification['missing_count']} 个章节可能遗漏")

    # 显示详细的覆盖报告
    print(f"\n📊 内容覆盖报告:")
    for item in verification['coverage_report']:
        if item['status'] == 'MISSING':
            print(f"  ⚠️  遗漏: {item['title']}")
        elif item['status'] == 'merged':
            print(f"  ✓ 已整合: {item['title']} → 合并到「{item['merged_into']}」")
        elif item['status'] == 'parent':
            # 统计该父章节合并了多少子章节
            merged_count = sum(1 for x in verification['coverage_report']
                             if x.get('merged_into') == item['title'])
            if merged_count > 0:
                print(f"  ✓ 父章节: {item['title']} (包含 {merged_count} 个子章节)")
            else:
                print(f"  ✓ 独立章节: {item['title']}")

    if not verification['all_covered']:
        print(f"\n❌ 错误: 有内容遗漏，请检查文档结构")
        print(f"建议: 尝试不同的粒度，或检查文档标题层级是否规范")
        sys.exit(1)

    # 5. 生成配图
    sections = merged_sections

    if not sections:
        print(f"错误: 没有找到级别为 {selected_level} 的小节", file=sys.stderr)
        sys.exit(1)

    print(f"\n🖼️  开始生成 {len(sections)} 张配图...")
    if args.provider == "cihebi":
        print(f"请求尺寸: {get_provider_config('cihebi').get('CIHEBI_IMAGE_SIZE') or '1254x1254'}")
    else:
        print(f"分辨率: {args.resolution}")
    print("=" * 60)
    print()

    successful = 0
    failed = 0

    for i, section in enumerate(sections, 1):
        print(f"正在生成第 {i}/{len(sections)} 张...")
        print(f"  标题: {section['title']}")

        # 限制内容长度（避免超过 API 限制）
        content = section['content']
        if len(content) > 1000:
            content = content[:1000] + "..."
            print(f"  提示: 内容较长，已截取前 1000 字符")

        image_path = generate_illustration(
            section['title'],
            content,
            style_prompt,
            output_dir,
            i,
            args.resolution,
            provider=args.provider,
            aspect_ratio=args.ratio
        )

        if image_path:
            print(f"  ✓ 已保存: {image_path}")
            successful += 1
        else:
            print(f"  ✗ 生成失败")
            failed += 1

        print()

    # 6. 完成
    print("=" * 60)
    print("✨ 生成完成！")
    print("=" * 60)
    print(f"成功: {successful} 张")
    if failed > 0:
        print(f"失败: {failed} 张")
    print(f"\n所有配图已保存到: {output_dir}")
    print()
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
