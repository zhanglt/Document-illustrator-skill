"""验证配置路径不受 Agent 安装目录或工作目录影响。"""

import os
import subprocess
import sys
import tempfile
import unittest
import argparse
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
import env_config
import image_api


class EnvConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.config = self.home / ".agents/skills/document-illustrator/.env"
        self.legacy = self.home / ".claude/skills/document-illustrator/.env"
        self.workdir = self.home / "work"
        self.workdir.mkdir()
        self.legacy.parent.mkdir(parents=True)
        self.legacy.write_text("ILLUSTRATOR_TEST_CONFIG=legacy\n", encoding="utf-8")
        (self.workdir / ".env").write_text("ILLUSTRATOR_TEST_CONFIG=cwd\n", encoding="utf-8")

    def test_only_shared_path_is_loaded(self):
        self.config.parent.mkdir(parents=True)
        self.config.write_text("ILLUSTRATOR_TEST_CONFIG=shared\n", encoding="utf-8")
        with patch.object(Path, "home", return_value=self.home), patch.dict(os.environ):
            os.environ["ILLUSTRATOR_TEST_CONFIG"] = "process"
            self.assertTrue(env_config.find_and_load_env())
            self.assertEqual(os.environ["ILLUSTRATOR_TEST_CONFIG"], "shared")

    def test_image_options_from_shared_env_and_cli_override(self):
        self.config.parent.mkdir(parents=True)
        self.config.write_text(
            "ILLUSTRATOR_IMAGE_PROVIDER=nanobanana\n"
            "ILLUSTRATOR_SINGLE_RATIO=3:4\n"
            "ILLUSTRATOR_BATCH_RATIO=16:9\n"
            "ILLUSTRATOR_RESOLUTION=1K\n", encoding="utf-8",
        )
        with patch.object(Path, "home", return_value=self.home), patch.dict(os.environ, {}, clear=True):
            env_config.find_and_load_env()
            for batch, ratio in ((False, "3:4"), (True, "16:9")):
                args = SimpleNamespace(provider=None, ratio=None, resolution=None)
                image_api.resolve_options(argparse.ArgumentParser(), args, batch=batch)
                self.assertEqual((args.provider, args.ratio, args.resolution), ("nanobanana", ratio, "1K"))
            args = SimpleNamespace(provider="nebula", ratio="16:9", resolution="4K")
            image_api.resolve_options(argparse.ArgumentParser(), args, batch=True)
            self.assertEqual((args.provider, args.ratio, args.resolution), ("nebula", "16:9", "4K"))

    def test_invalid_env_options_fail_before_request(self):
        cases = [
            {"ILLUSTRATOR_SINGLE_RATIO": "invalid"},
            {"ILLUSTRATOR_BATCH_RATIO": "invalid"},
            {"ILLUSTRATOR_RESOLUTION": "8K"},
            {"ILLUSTRATOR_IMAGE_PROVIDER": "nebula", "ILLUSTRATOR_BATCH_RATIO": "3:4"},
            {"ILLUSTRATOR_IMAGE_PROVIDER": "nebula", "ILLUSTRATOR_RESOLUTION": "2K"},
        ]
        parser = unittest.mock.Mock()
        parser.error.side_effect = ValueError("配置错误")
        for env in cases:
            with self.subTest(env=env), patch.dict(os.environ, env, clear=True), patch.object(image_api, "read_request") as read:
                args = SimpleNamespace(provider=None, ratio=None, resolution=None)
                with self.assertRaisesRegex(ValueError, "配置错误"):
                    image_api.resolve_options(parser, args, batch="ILLUSTRATOR_SINGLE_RATIO" not in env)
                read.assert_not_called()

    def test_unconfigured_defaults(self):
        with patch.dict(os.environ, {}, clear=True):
            for provider, resolution in (("nanobanana", "2K"), ("gemini", "2K"), ("nebula", "4K")):
                args = SimpleNamespace(provider=provider, ratio=None, resolution=None)
                image_api.resolve_options(argparse.ArgumentParser(), args, batch=True)
                self.assertEqual((args.ratio, args.resolution), ("16:9", resolution))

    def test_missing_shared_file_preserves_environment(self):
        with patch.object(Path, "home", return_value=self.home), patch.dict(
            os.environ, {"ILLUSTRATOR_TEST_CONFIG": "process"}
        ), patch.object(env_config, "load_dotenv") as load:
            self.assertFalse(env_config.find_and_load_env())
            self.assertEqual(os.environ["ILLUSTRATOR_TEST_CONFIG"], "process")
            load.assert_not_called()

    def test_both_entrypoints_from_another_working_directory(self):
        self.config.parent.mkdir(parents=True)
        self.config.write_text("ILLUSTRATOR_TEST_CONFIG=shared\n", encoding="utf-8")
        for filename in ("generate_single_image.py", "generate_illustrations.py"):
            with self.subTest(script=filename):
                self.assert_entrypoint_config(filename, "shared")

    def test_entrypoints_do_not_search_legacy_or_working_directory(self):
        for filename in ("generate_single_image.py", "generate_illustrations.py"):
            with self.subTest(script=filename):
                self.assert_entrypoint_config(filename, "process")

    def assert_entrypoint_config(self, filename, expected):
        script = SCRIPT_DIR / filename
        code = (
            "import runpy, sys, os; "
            f"sys.path.insert(0, {str(SCRIPT_DIR)!r}); "
            f"runpy.run_path({str(script)!r}, run_name='config_test'); "
            "print(os.environ.get('ILLUSTRATOR_TEST_CONFIG'))"
        )
        environment = dict(os.environ)
        environment.update({
            "USERPROFILE": str(self.home), "HOME": str(self.home),
            "ILLUSTRATOR_TEST_CONFIG": "process",
        })
        result = subprocess.run(
            [sys.executable, "-X", "utf8", "-c", code], cwd=self.workdir,
            env=environment, capture_output=True, encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), expected)


if __name__ == "__main__":
    unittest.main()
