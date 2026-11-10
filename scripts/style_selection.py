"""单图与批量入口共用的风格选择；不设置默认风格。"""

from pathlib import Path


STYLES = {
    "gradient-glass": "渐变玻璃卡片：玻璃质感、极光渐变，适合科技与产品介绍",
    "ticket": "票据风格：黑白对比、票券分区，适合简报与数据报告",
    "vector-illustration": "矢量插画：扁平插画、柔和配色，适合场景与概念解释",
    "government-red": "党政红风格：庄重红金、正式排版，适合政策与公共服务",
    "creative-editorial": "创意杂志风：非对称版式、醒目标题，适合品牌与创意主题",
    "retro-flat": "复古扁平插画风：复古配色、等粗描边，适合文化与故事",
    "handdrawn-tech": "手绘技术解释风：细线草图、淡彩标注，适合技术概念",
    "whiteboard": "手绘白板风：白板笔迹、圈画箭头，适合教学与讨论",
    "teaching-courseware": "教学课件风：学术蓝、知识层级，适合课程与案例讲解",
    "data-dashboard": "数据仪表盘风：明亮数据卡、清晰图表，适合指标与趋势",
    "clean-professional": "清爽专业风：浅底蓝青、结构清晰，适合方案与工作说明",
    "warm-handmade": "温暖手工风：纸张拼贴、柔和色彩，适合生活与人文故事",
    "eink-editorial": "电子墨水杂志风：墨色纸感、杂志字体，适合观点与专题",
    "research-defense": "科研答辩风：学术蓝红、证据导向，适合研究与技术路线",
    "consulting": "麦肯锡风格：理性蓝灰、结构化隐喻，适合商业分析",
    "clear-blue-report": "清蓝汇报风：蓝青双色、结论先行，适合管理与行业汇报",
}


def add_style_arguments(parser):
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--style", choices=list(STYLES), help="本次任务明确选择的内置风格；未指定时询问")
    group.add_argument("--style-file", help="本次任务明确选择的自定义风格文件，与 --style 互斥")


def choose_style(style=None, style_file=None):
    """显式参数视为本次选择；无参数时必须询问，空输入不采用默认值。"""
    if not style and not style_file:
        print("\n请选择本次生图风格（无默认项）：")
        names = list(STYLES)
        for index, name in enumerate(names, 1):
            print(f"{index}. {STYLES[name]}")
        custom_choice = str(len(names) + 1)
        print(f"{custom_choice}. 自定义风格文件")
        while True:
            try:
                choice = input(f"请输入选择 (1-{custom_choice})：").strip()
                if choice == custom_choice:
                    style_file = input("请输入风格文件路径：").strip()
                    if style_file:
                        break
                elif choice in {str(index) for index in range(1, len(names) + 1)}:
                    style = names[int(choice) - 1]
                    break
            except (EOFError, KeyboardInterrupt):
                raise ValueError("尚未选择生图风格，已停止；请先让用户选择，再传入 --style 或 --style-file") from None
            print("请选择有效选项，不会自动采用默认风格。")
    if style_file:
        path = Path(style_file)
    elif style in STYLES:
        path = Path(__file__).resolve().parents[1] / "styles" / f"{style}.md"
    else:
        raise ValueError("无效的生图风格")
    if not path.is_file():
        raise ValueError(f"风格文件不存在或不是文件：{path}")
    print(f"本次选择的风格文件：{path.name}")
    return str(path)


def resolve_style(parser, args):
    try:
        return choose_style(args.style, args.style_file)
    except ValueError as exc:
        parser.error(str(exc))
