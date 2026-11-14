"""验证每次任务的风格选择，以及未选择时不调用生图接口。"""

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import style_selection
import env_config
import generate_single_image
import generate_illustrations


class StyleSelectionTests(unittest.TestCase):
    def setUp(self):
        selected = patch.object(env_config, "_configured_provider", "nanobanana")
        selected.start()
        self.addCleanup(selected.stop)

    def test_menu_rejects_blank_and_invalid_choices(self):
        output = io.StringIO()
        with patch("builtins.input", side_effect=["", "invalid", "2"]) as ask, contextlib.redirect_stdout(output):
            path = style_selection.choose_style()
        self.assertEqual(Path(path).name, "ticket.md")
        self.assertEqual(ask.call_count, 3)
        self.assertIn("渐变玻璃卡片", output.getvalue())
        self.assertIn("矢量插画", output.getvalue())

    def test_explicit_style_and_custom_file_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            custom = Path(directory) / "custom.md"
            custom.write_text("自定义风格", encoding="utf-8")
            with patch("builtins.input") as ask, contextlib.redirect_stdout(io.StringIO()):
                for style in style_selection.STYLES:
                    self.assertEqual(Path(style_selection.choose_style(style=style)).stem, style)
                self.assertEqual(style_selection.choose_style(style_file=str(custom)), str(custom))
            ask.assert_not_called()

    def test_custom_menu_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            custom = Path(directory) / "custom.md"
            custom.write_text("自定义风格", encoding="utf-8")
            with patch("builtins.input", side_effect=[str(len(style_selection.STYLES) + 1), str(custom)]), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(style_selection.choose_style(), str(custom))

    def test_new_menu_choices_and_prompt_extraction(self):
        names = list(style_selection.STYLES)
        self.assertEqual(len(names), 16)
        for index in (4, len(names)):
            with self.subTest(index=index), patch("builtins.input", return_value=str(index)), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(Path(style_selection.choose_style()).stem, names[index - 1])
        root = Path(style_selection.__file__).resolve().parents[1]
        for name in names[3:]:
            with self.subTest(style=name):
                path = root / "styles" / f"{name}.md"
                content = path.read_text(encoding="utf-8")
                prompt = generate_illustrations.extract_core_prompt(path)
                self.assertEqual(prompt, content.split("### 提示词", 1)[1].strip())
                self.assertNotIn("来源：", prompt)

    def test_interrupted_selection_stops(self):
        with patch("builtins.input", side_effect=KeyboardInterrupt), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(ValueError, "尚未选择"):
                style_selection.choose_style()

    def test_imported_styles_reach_generation_in_both_clis(self):
        with tempfile.TemporaryDirectory() as directory:
            document = Path(directory) / "article.md"
            document.write_text("## 技术原理\n监测、分析与预警。\n", encoding="utf-8")
            for name in list(style_selection.STYLES)[3:]:
                for module in (generate_single_image, generate_illustrations):
                    for ratio in ("16:9", "3:4"):
                        arguments = ["--style", name, "--provider", "nanobanana", "--ratio", ratio,
                                     "--resolution", "2K", "--output", str(Path(directory) / "output")]
                        if module is generate_single_image:
                            arguments += ["--title", "技术原理", "--content", "监测、分析与预警。"]
                        else:
                            arguments += [str(document), "--level", "h2"]
                        with self.subTest(style=name, module=module.__name__, ratio=ratio), \
                             patch.object(sys, "argv", [module.__name__] + arguments), \
                             patch("builtins.input") as ask, \
                             patch.object(generate_single_image, "generate_image", return_value="result.png") as generate, \
                             contextlib.redirect_stdout(io.StringIO()):
                            if module is generate_single_image:
                                with self.assertRaises(SystemExit) as caught:
                                    module.main()
                                self.assertEqual(caught.exception.code, 0)
                            else:
                                module.main()
                            ask.assert_not_called()
                            generate.assert_called_once()
                            call = generate.call_args
                            self.assertEqual(call.kwargs["provider"], "nanobanana")
                            self.assertEqual(call.kwargs["aspect_ratio"], ratio)
                            self.assertEqual(call.kwargs["resolution"], "2K")
                            prompt = call.kwargs.get("style_prompt") if module is generate_single_image else call.args[2]
                            self.assertIn("画幅比例遵循本次调用参数", prompt)

    def test_no_selection_is_reused_between_tasks(self):
        with patch("builtins.input", side_effect=["1", "3"]) as ask, contextlib.redirect_stdout(io.StringIO()):
            first = style_selection.choose_style()
            second = style_selection.choose_style()
        self.assertNotEqual(first, second)
        self.assertEqual(ask.call_count, 2)

    def test_both_clis_stop_without_selection_before_any_generation(self):
        cases = [
            (generate_single_image, ["--title", "主题", "--content", "内容", "--output", "unused.png"]),
            (generate_illustrations, ["missing.md", "--level", "h2"]),
        ]
        for module, arguments in cases:
            with self.subTest(module=module.__name__), patch.object(sys, "argv", [module.__name__] + arguments), \
                 patch("builtins.input", side_effect=EOFError), \
                 patch.object(generate_single_image, "generate_image") as single, \
                 patch.object(generate_illustrations, "generate_illustration") as batch, \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as error:
                with self.assertRaises(SystemExit) as caught:
                    module.main()
                self.assertEqual(caught.exception.code, 2)
                self.assertIn("尚未选择生图风格", error.getvalue())
                single.assert_not_called()
                batch.assert_not_called()

    def test_single_cli_uses_interactive_choice(self):
        with patch.object(sys, "argv", ["single", "--title", "主题", "--content", "内容", "--output", "unused.png"]), \
             patch("builtins.input", return_value="3") as ask, \
             patch.object(generate_single_image, "generate_image", return_value="unused.png") as generate, \
             contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                generate_single_image.main()
        self.assertEqual(caught.exception.code, 0)
        ask.assert_called_once()
        expected = (Path(style_selection.__file__).resolve().parents[1] / "styles/vector-illustration.md").read_text(encoding="utf-8")
        self.assertEqual(generate.call_args.kwargs["style_prompt"], expected)

    def test_conflicting_style_arguments_do_not_generate(self):
        with patch.object(sys, "argv", ["single", "--title", "主题", "--content", "内容", "--output", "unused.png",
                                        "--style", "ticket", "--style-file", "custom.md"]), \
             patch.object(generate_single_image, "generate_image") as generate, \
             contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                generate_single_image.main()
        self.assertEqual(caught.exception.code, 2)
        generate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
