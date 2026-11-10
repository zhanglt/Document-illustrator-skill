"""nanobanana 接口契约与失败处理的离线验证。"""

import argparse
import base64
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import image_api
import env_config
import generate_single_image
import generate_illustrations


class NanobananaTests(unittest.TestCase):
    def setUp(self):
        sections = patch.object(env_config, "_sections", {})
        sections.start()
        self.addCleanup(sections.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "images/result.png"
        buffer = io.BytesIO()
        Image.new("RGB", (1376, 768), "white").save(buffer, format="JPEG")
        self.inline = {"mimeType": "image/jpeg", "data": base64.b64encode(buffer.getvalue()).decode()}
        env = patch.dict(os.environ, {
            "NEBULA_NANOBANANA_API_KEY": "banana-test-key",
            "NEBULA_NANOBANANA_MODEL": "gemini-3.1-flash-image",
            "ILLUSTRATOR_SINGLE_RATIO": "", "ILLUSTRATOR_BATCH_RATIO": "",
            "ILLUSTRATOR_RESOLUTION": "",
        })
        env.start()
        self.addCleanup(env.stop)

    def response(self, parts):
        return json.dumps({"candidates": [{"content": {"parts": parts}}]}).encode()

    def test_contract_and_actual_image_save(self):
        response = self.response([{"text": "说明"}, {"inlineData": self.inline}])
        with patch.object(image_api, "read_request", return_value=response) as read:
            result = image_api.generate_nanobanana("中文提示词", self.output, "3:4", "4K")
        self.assertEqual(result, str(self.output))
        request = read.call_args.args[0]
        self.assertEqual(request.full_url, "https://img-api.apinebula.ai/v1beta/models/gemini-3.1-flash-image:generateContent")
        self.assertEqual(request.get_header("Authorization"), "Bearer banana-test-key")
        self.assertEqual(json.loads(request.data), {
            "contents": [{"role": "user", "parts": [{"text": "中文提示词"}]}],
            "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "3:4", "imageSize": "4K"}},
        })
        self.assertEqual(read.call_count, 1)
        self.assertEqual(read.call_args.kwargs["timeout"], 1800)
        with Image.open(self.output) as image:
            self.assertEqual(image.format, "PNG")
            self.assertEqual(image.size, (1376, 768))
        self.assertFalse(self.output.with_suffix(".png.response.json").exists())

    def test_group_base_url(self):
        section = {"nanobanana": {
            "NEBULA_NANOBANANA_BASE_URL": "https://banana.example/",
        }}
        with patch.object(env_config, "_sections", section), patch.object(
            image_api, "read_request", return_value=self.response([{"inlineData": self.inline}])
        ) as read:
            image_api.generate_nanobanana("test", self.output)
        self.assertEqual(
            read.call_args.args[0].full_url,
            "https://banana.example/v1beta/models/gemini-3.1-flash-image:generateContent",
        )

    def test_model_and_1k(self):
        with patch.dict(os.environ, {"NEBULA_NANOBANANA_MODEL": "gemini-3-pro-image-preview"}), patch.object(
            image_api, "read_request", return_value=self.response([{"inlineData": self.inline}])
        ) as read:
            image_api.generate_nanobanana("test", self.output, resolution="1K")
        self.assertIn("gemini-3-pro-image-preview:generateContent", read.call_args.args[0].full_url)
        self.assertEqual(json.loads(read.call_args.args[0].data)["generationConfig"]["imageConfig"]["imageSize"], "1K")

    def test_invalid_response_or_image_does_not_save(self):
        cases = [b'[]', b'{}', b'{"candidates": []}', b'{"candidates": [null]}',
                 self.response([]), self.response([{"text": "拒绝"}]),
                 self.response([{"inlineData": {"mimeType": "image/png", "data": "!"}}]),
                 self.response([{"inlineData": {"mimeType": "image/png", "data": "bm90LWltYWdl"}}]),
                 self.response([{"thought": True, "inlineData": self.inline}])]
        for response in cases:
            with self.subTest(response=response[:80]), patch.object(image_api, "read_request", return_value=response) as read:
                with self.assertRaises((ValueError, OSError)):
                    image_api.generate_nanobanana("test", self.output)
                self.assertEqual(read.call_count, 1)
                self.assertFalse(self.output.exists())

    def test_missing_key_and_invalid_model_do_not_request(self):
        for env in ({"NEBULA_API_KEY": "other-group"}, {"NEBULA_NANOBANANA_API_KEY": "test", "NEBULA_NANOBANANA_MODEL": "../bad?key=test"}):
            with patch.dict(os.environ, env, clear=True), patch.object(image_api, "read_request") as read:
                with self.assertRaises(ValueError):
                    image_api.generate_nanobanana("test", self.output)
                read.assert_not_called()

    def test_default_and_dispatch_for_both_entries(self):
        with patch.dict(os.environ, {"ILLUSTRATOR_IMAGE_PROVIDER": "nanobanana"}):
            args = SimpleNamespace(provider=None, resolution=None)
            image_api.resolve_options(argparse.ArgumentParser(), args)
            self.assertEqual((args.provider, args.resolution), ("nanobanana", "2K"))
            self.assertEqual(image_api.get_provider("nebula"), "nebula")
        with patch.object(generate_single_image, "generate_nanobanana", return_value="done") as generate:
            self.assertEqual(generate_single_image.generate_image(
                "title", "body", "style", str(self.output), "3:4", "1K", True, "nanobanana"
            ), "done")
            self.assertIn("封面", generate.call_args.args[0])
            self.assertEqual(generate.call_args.args[2:], ("3:4", "1K"))
            self.assertEqual(generate_illustrations.generate_illustration(
                "title", "body", "style", self.temp.name, 1, "4K", "nanobanana"
            ), "done")
            self.assertEqual(generate.call_args.args[2:], ("16:9", "4K"))
            generate_illustrations.generate_illustration(
                "title", "body", "style", self.temp.name, 2, "2K", "nanobanana", aspect_ratio="3:4"
            )
            self.assertEqual(generate.call_args.args[2:], ("3:4", "2K"))


if __name__ == "__main__":
    unittest.main()
