"""单图与批量入口共用的风格选择；不设置默认风格。"""

from pathlib import Path


STYLES = {
    "gradient-glass": "渐变玻璃卡片：玻璃质感、极光渐变，适合科技与产品介绍",
    "ticket": "票据风格：黑白对比、票券分区，适合简报与数据报告",
    "vector-illustration": "矢量插画：扁平插画、柔和配色，适合场景与概念解释",
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
        print("4. 自定义风格文件")
        while True:
            try:
                choice = input("请输入选择 (1/2/3/4)：").strip()
                if choice == "4":
                    style_file = input("请输入风格文件路径：").strip()
                    if style_file:
                        break
                elif choice in ("1", "2", "3"):
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
