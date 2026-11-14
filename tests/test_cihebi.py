"""cihebi Image API 的离线请求、响应和路由验证。"""

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
import env_config
import image_api
import generate_single_image


class CihebiTests(unittest.TestCase):
    def setUp(self):
        sections = patch.object(env_config, "_sections", {})
        sections.start()
        self.addCleanup(sections.stop)
        selected = patch.object(env_config, "_configured_provider", "cihebi")
        selected.start()
        self.addCleanup(selected.stop)
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.output = Path(temp.name) / "images" / "result.png"
        buffer = io.BytesIO()
        Image.new("RGB", (32, 24), "white").save(buffer, format="PNG")
        self.encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        variables = patch.dict(os.environ, {
            "CIHEBI_IMAGE_API_KEY": "cihebi-test-key", "CIHEBI_IMAGE_MODEL": "", "CIHEBI_IMAGE_SIZE": "",
            "CIHEBI_IMAGE_QUALITY": "", "CIHEBI_IMAGE_API_BASE_URL": "",
        })
        variables.start()
        self.addCleanup(variables.stop)

    def test_documented_request_and_png_save(self):
        response = json.dumps({"data": [{"b64_json": self.encoded, "extra": "ok"}]}).encode()
        with patch.object(image_api, "read_request", return_value=response) as read:
            result = image_api.generate_cihebi("中文提示词", self.output)
        self.assertEqual(result, str(self.output))
        request = read.call_args.args[0]
        self.assertEqual(request.full_url, "https://cpa.cihebi.vip/image-api/v1/images/generations")
        self.assertEqual(request.get_header("Authorization"), "Bearer cihebi-test-key")
        self.assertEqual(json.loads(request.data), {
            "model": "gpt-image-2.5-sunburst", "prompt": "中文提示词", "n": 1,
            "size": "1254x1254", "quality": "low", "output_format": "png",
            "response_format": "b64_json", "stream": False,
        })
        self.assertEqual(read.call_args.kwargs["timeout"], 600)
        with Image.open(self.output) as image:
            self.assertEqual((image.format, image.size), ("PNG", (32, 24)))
        self.assertFalse(self.output.with_suffix(".png.response.json").exists())

    def test_group_overrides_and_dispatch(self):
        section = {"cihebi": {
            "CIHEBI_IMAGE_API_KEY": "group-key", "CIHEBI_IMAGE_MODEL": "gpt-image-2.5-flare",
            "CIHEBI_IMAGE_SIZE": "1536x1024", "CIHEBI_IMAGE_QUALITY": "medium",
            "CIHEBI_IMAGE_API_BASE_URL": "https://cpa.cihebi.vip/image-api/v1/",
        }}
        response = json.dumps({"data": [{"b64_json": self.encoded}]}).encode()
        with patch.object(env_config, "_sections", section), patch.object(
            image_api, "read_request", return_value=response
        ) as read:
            image_api.generate_cihebi("test", self.output)
        request = read.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer group-key")
        self.assertEqual(json.loads(request.data)["model"], "gpt-image-2.5-flare")
        self.assertEqual(json.loads(request.data)["size"], "1536x1024")
        self.assertEqual(json.loads(request.data)["quality"], "medium")
        with patch.object(generate_single_image, "generate_cihebi", return_value="done") as generate:
            result = generate_single_image.generate_image("title", "body", "style", self.output, provider="cihebi")
        self.assertEqual(result, "done")
        self.assertIn("style", generate.call_args.args[0])
        self.assertIn("body", generate.call_args.args[0])

    def test_invalid_settings_and_response_do_not_save(self):
        bad_settings = [
            {"CIHEBI_IMAGE_API_KEY": ""}, {"CIHEBI_IMAGE_MODEL": "../bad"},
            {"CIHEBI_IMAGE_SIZE": "bad"}, {"CIHEBI_IMAGE_QUALITY": "ultra"},
            {"CIHEBI_IMAGE_API_BASE_URL": "http://cpa.cihebi.vip/image-api/v1"},
        ]
        for setting in bad_settings:
            with self.subTest(setting=setting), patch.dict(os.environ, setting), patch.object(
                image_api, "read_request"
            ) as read:
                with self.assertRaises(ValueError):
                    image_api.generate_cihebi("test", self.output)
                read.assert_not_called()
        for response in (b"[]", b"{}", b'{"data": []}', b'{"data": [{}]}',
                         b'{"data": [{"b64_json": "!"}]}',
                         b'{"data": [{"b64_json": "bm90LWltYWdl"}]}'):
            with self.subTest(response=response), patch.object(image_api, "read_request", return_value=response):
                with self.assertRaises((ValueError, OSError)):
                    image_api.generate_cihebi("test", self.output)
                self.assertFalse(self.output.exists())

    def test_unprefixed_legacy_key_is_not_used(self):
        with patch.dict(os.environ, {"IMAGE_API_KEY": "old-key"}, clear=True), patch.object(
            image_api, "read_request"
        ) as read:
            with self.assertRaisesRegex(ValueError, "CIHEBI_IMAGE_API_KEY"):
                image_api.generate_cihebi("test", self.output)
            read.assert_not_called()

    def test_cli_does_not_accept_unused_ratio_resolution(self):
        parser = argparse.ArgumentParser()
        with patch.dict(os.environ, {"ILLUSTRATOR_IMAGE_PROVIDER": "cihebi"}):
            args = SimpleNamespace(provider=None, ratio=None, resolution=None)
            image_api.resolve_options(parser, args)
            self.assertEqual((args.provider, args.ratio, args.resolution), ("cihebi", None, None))
            for ratio, resolution in (("16:9", None), (None, "2K")):
                with self.subTest(ratio=ratio, resolution=resolution), self.assertRaises(SystemExit):
                    image_api.resolve_options(parser, SimpleNamespace(
                        provider=None, ratio=ratio, resolution=resolution,
                    ))

    def test_locked_provider_blocks_other_direct_api_calls(self):
        with patch.dict(os.environ, {"ILLUSTRATOR_IMAGE_PROVIDER": "image2-4k"}), patch.object(
            image_api, "read_request"
        ) as read:
            self.assertEqual(image_api.get_provider(), "cihebi")
            with self.assertRaisesRegex(ValueError, "锁定"):
                image_api.generate_nebula("test", self.output)
            with self.assertRaisesRegex(ValueError, "锁定"):
                image_api.generate_nanobanana("test", self.output)
            with self.assertRaisesRegex(ValueError, "锁定"):
                image_api.edit_nebula("test", [self.output], self.output)
            read.assert_not_called()
        with patch.object(generate_single_image, "generate_cihebi") as current, patch.object(
            generate_single_image, "generate_nebula"
        ) as other:
            self.assertIsNone(generate_single_image.generate_image(
                "title", "body", "style", self.output, provider="image2-4k",
            ))
            current.assert_not_called()
            other.assert_not_called()


if __name__ == "__main__":
    unittest.main()
