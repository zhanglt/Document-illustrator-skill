"""使用 Nebula image2-4k 编辑已有图片。"""

import argparse

from env_config import find_and_load_env
from image_api import edit_nebula


def main():
    parser = argparse.ArgumentParser(description="Nebula 参考图编辑；原图保持不变")
    parser.add_argument("--image", action="append", required=True, help="参考图路径；可重复传入")
    parser.add_argument("--prompt", required=True, help="说明要保留和修改的内容")
    parser.add_argument("--output", required=True, help="新的输出图片路径")
    args = parser.parse_args()
    find_and_load_env()
    try:
        result = edit_nebula(args.prompt, args.image, args.output)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"图编辑失败：{exc}\n")
    print(f"已保存：{result}")


if __name__ == "__main__":
    main()
