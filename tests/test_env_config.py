"""验证配置路径不受 Agent 安装目录或工作目录影响。"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
import env_config


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
