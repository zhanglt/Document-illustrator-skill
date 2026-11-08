"""离线验证接口契约、响应处理和 CLI 后端选择；不会请求真实 API。"""

import argparse
import base64
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.request import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import image_api
import env_config
import generate_single_image
import generate_illustrations
from PIL import Image


class NebulaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        buffer = io.BytesIO()
        Image.new("RGB", (3840, 2160), "white").save(buffer, format="JPEG")
        cls.jpeg = buffer.getvalue()

    def setUp(self):
        sections = patch.object(env_config, "_sections", {})
        sections.start()
        self.addCleanup(sections.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "images" / "result.png"
        env = patch.dict(os.environ, {
            "NEBULA_API_KEY": "test-key", "ILLUSTRATOR_IMAGE_PROVIDER": "gemini",
            "ILLUSTRATOR_SINGLE_RATIO": "", "ILLUSTRATOR_BATCH_RATIO": "",
            "ILLUSTRATOR_RESOLUTION": "",
            "NEBULA_MODEL": "gpt-image-2-4k", "NEBULA_SIZE": "3840x2160", "NEBULA_QUALITY": "high",
            "GEMINI_MODEL": "gemini-3-pro-image-preview",
        })
        env.start()
        self.addCleanup(env.stop)

    def response(self, item):
        return json.dumps({"data": [item]}).encode()

    def test_url_request_contract_and_png_conversion(self):
        response = self.response({"url": "https://cdn.example/image.jpg"})
        with patch.object(image_api, "read_request", side_effect=[response, self.jpeg]) as read:
            image_api.generate_nebula("中文提示词", self.output)
        request = read.call_args_list[0].args[0]
        self.assertEqual(request.full_url, image_api.NEBULA_ENDPOINT)
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
        self.assertEqual(json.loads(request.data), {
            "model": "gpt-image-2-4k", "prompt": "中文提示词",
            "size": "3840x2160", "quality": "high", "response_format": "url",
        })
        self.assertEqual(read.call_args_list[0].kwargs["timeout"], 1800)
        self.assertIsNone(read.call_args_list[1].args[0].get_header("Authorization"))
        with Image.open(self.output) as image:
            self.assertEqual(image.format, "PNG")
            self.assertEqual(image.size, (3840, 2160))

    def test_base64_fallback(self):
        with patch.object(image_api, "read_request", return_value=self.response({
            "b64_json": base64.b64encode(self.jpeg).decode(),
        })) as read:
            image_api.generate_nebula("test", self.output)
        self.assertEqual(read.call_count, 1)
        self.assertTrue(self.output.exists())

    def test_group_request_parameters_and_dimension_validation(self):
        buffer = io.BytesIO()
        Image.new("RGB", (160, 90)).save(buffer, format="PNG")
        section = {"image2-4k": {
            "NEBULA_MODEL": "test-image-model", "NEBULA_SIZE": "160x90", "NEBULA_QUALITY": "medium",
        }}
        with patch.object(env_config, "_sections", section), patch.object(image_api, "read_request", return_value=self.response({
            "b64_json": base64.b64encode(buffer.getvalue()).decode(),
        })) as read:
            image_api.generate_nebula("test", self.output)
        payload = json.loads(read.call_args.args[0].data)
        self.assertEqual((payload["model"], payload["size"], payload["quality"]), ("test-image-model", "160x90", "medium"))
        with Image.open(self.output) as image:
            self.assertEqual(image.size, (160, 90))

    def test_invalid_request_parameters_fail_before_request(self):
        for key, value in (("NEBULA_MODEL", ""), ("NEBULA_SIZE", "auto"), ("NEBULA_SIZE", "0x10"),
                           ("NEBULA_SIZE", "99999x99999"), ("NEBULA_QUALITY", "invalid")):
            with self.subTest(key=key, value=value), patch.dict(os.environ, {key: value}), patch.object(image_api, "read_request") as read:
                with self.assertRaises(ValueError):
                    image_api.generate_nebula("test", self.output)
                read.assert_not_called()

    def test_url_preferred_when_both_fields_exist(self):
        with patch.object(image_api, "read_request", side_effect=[
            self.response({"url": "https://cdn.example/image", "b64_json": "invalid"}), self.jpeg,
        ]):
            image_api.generate_nebula("test", self.output)
        self.assertTrue(self.output.exists())

    def test_invalid_responses(self):
        for response in (b'{}', b'[]', b'{"data": []}', self.response({}), b'not-json'):
            with self.subTest(response=response), patch.object(image_api, "read_request", return_value=response):
                with self.assertRaises(ValueError):
                    image_api.generate_nebula("test", self.output)
        self.assertFalse(self.output.exists())

    def test_invalid_image_rejected(self):
        with patch.object(image_api, "read_request", return_value=self.response({
            "b64_json": base64.b64encode(b"not-an-image").decode(),
        })):
            with self.assertRaises(OSError):
                image_api.generate_nebula("test", self.output)
        self.assertFalse(self.output.exists())

    def test_wrong_dimensions_rejected(self):
        buffer = io.BytesIO()
        Image.new("RGB", (16, 9)).save(buffer, format="PNG")
        with patch.object(image_api, "read_request", return_value=self.response({
            "b64_json": base64.b64encode(buffer.getvalue()).decode(),
        })):
            with self.assertRaisesRegex(ValueError, "16x9"):
                image_api.generate_nebula("test", self.output)
        self.assertFalse(self.output.exists())

    def test_missing_key_does_not_request(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(image_api, "read_request") as read:
            with self.assertRaisesRegex(ValueError, "NEBULA_API_KEY"):
                image_api.generate_nebula("test", self.output)
            read.assert_not_called()

    def test_download_failure_preserves_response_without_regeneration(self):
        with patch.object(image_api, "read_request", side_effect=[
            self.response({"url": "https://cdn.example/image"}), RuntimeError("failed"),
        ]) as read:
            with self.assertRaisesRegex(RuntimeError, "响应已保存"):
                image_api.generate_nebula("test", self.output)
        self.assertEqual(read.call_count, 2)
        self.assertTrue(self.output.with_suffix(".png.response.json").exists())

    def test_invalid_url_rejected(self):
        with patch.object(image_api, "read_request", return_value=self.response({"url": "file:///secret"})) as read:
            with self.assertRaises(ValueError):
                image_api.generate_nebula("test", self.output)
        self.assertEqual(read.call_count, 1)

    def test_backend_defaults_and_explicit_override(self):
        parser = argparse.ArgumentParser()
        for provider, expected in ((None, "2K"), ("nebula", "4K")):
            args = SimpleNamespace(provider=provider, resolution=None)
            image_api.resolve_options(parser, args)
            self.assertEqual(args.resolution, expected)
        with patch.dict(os.environ, {"ILLUSTRATOR_IMAGE_PROVIDER": "nebula"}):
            self.assertEqual(image_api.get_provider(), "nebula")
            self.assertEqual(image_api.get_provider("gemini"), "gemini")

    def test_unsupported_options_fail_before_request(self):
        for ratio, resolution in (("3:4", "4K"), ("16:9", "2K")):
            with self.subTest(ratio=ratio, resolution=resolution), patch.object(
                generate_single_image, "generate_nebula"
            ) as generate:
                result = generate_single_image.generate_image(
                    "test", "test", "style", str(self.output), ratio, resolution, provider="nebula",
                )
                self.assertIsNone(result)
                generate.assert_not_called()

    def test_single_and_batch_dispatch(self):
        with patch.object(generate_single_image, "generate_nebula", return_value=str(self.output)) as generate:
            result = generate_single_image.generate_image(
                "title", "body", "style", str(self.output), resolution="4K", is_cover=True, provider="nebula",
            )
            self.assertEqual(result, str(self.output))
            self.assertIn("封面", generate.call_args.args[0])
        with patch.object(generate_single_image, "generate_image", return_value="done") as generate:
            self.assertEqual(generate_illustrations.generate_illustration(
                "title", "body", "style", self.temp.name, 1, "4K", provider="nebula",
            ), "done")
            self.assertEqual(generate.call_args.kwargs["provider"], "nebula")
            self.assertTrue(generate.call_args.args[3].endswith("illustration-01.png"))

    def test_gemini_request_is_preserved(self):
        from google import genai

        client = unittest.mock.MagicMock()
        response = SimpleNamespace(parts=[SimpleNamespace(
            inline_data=object(), as_image=lambda: Image.new("RGB", (16, 9)),
        )])
        client.models.generate_content.return_value = response
        self.output.parent.mkdir(parents=True)
        with patch.dict(os.environ, {"GEMINI_API_KEY": "gemini-test"}), patch.object(
            genai, "Client", return_value=client
        ):
            result = generate_single_image.generate_image(
                "title", "body", "style", str(self.output), provider="gemini",
            )
        self.assertEqual(result, str(self.output))
        request = client.models.generate_content.call_args.kwargs
        self.assertEqual(request["model"], "gemini-3-pro-image-preview")
        self.assertEqual(request["config"].image_config.aspect_ratio, "16:9")
        self.assertEqual(request["config"].image_config.image_size, "2K")

    def test_native_gemini_group_model_key_and_batch_request(self):
        from google import genai

        client = unittest.mock.MagicMock()
        client.models.generate_content.return_value = SimpleNamespace(parts=[SimpleNamespace(
            inline_data=object(), as_image=lambda: Image.new("RGB", (16, 9)),
        )])
        section = {"gemini": {
            "GEMINI_API_KEY": "google-section-test", "GEMINI_MODEL": "gemini-3.1-flash-image",
            "ILLUSTRATOR_BATCH_RATIO": "3:4", "ILLUSTRATOR_RESOLUTION": "4K",
        }}
        with patch.object(env_config, "_sections", section), patch.object(genai, "Client", return_value=client) as factory:
            args = SimpleNamespace(provider="gemini", ratio=None, resolution=None)
            image_api.resolve_options(argparse.ArgumentParser(), args, batch=True)
            result = generate_illustrations.generate_illustration(
                "title", "body", "style", self.temp.name, 1, args.resolution,
                provider=args.provider, aspect_ratio=args.ratio,
            )
        self.assertTrue(Path(result).exists())
        factory.assert_called_once_with(api_key="google-section-test")
        request = client.models.generate_content.call_args.kwargs
        self.assertEqual(request["model"], "gemini-3.1-flash-image")
        self.assertEqual(request["config"].image_config.aspect_ratio, "3:4")
        self.assertEqual(request["config"].image_config.image_size, "4K")

    def test_timeout_does_not_resubmit_post(self):
        opener = SimpleNamespace(open=unittest.mock.Mock(side_effect=URLError(TimeoutError())))
        with patch.object(image_api, "build_opener", return_value=opener) as build:
            with self.assertRaisesRegex(RuntimeError, "任务状态未知"):
                image_api.read_request(Request(image_api.NEBULA_ENDPOINT, data=b'{}'), 1800, 100)
        self.assertEqual(build.call_count, 1)

    def test_socket_timeout_does_not_resubmit_post(self):
        opener = SimpleNamespace(open=unittest.mock.Mock(side_effect=TimeoutError()))
        with patch.object(image_api, "build_opener", return_value=opener) as build:
            with self.assertRaisesRegex(RuntimeError, "任务状态未知"):
                image_api.read_request(Request(image_api.NEBULA_ENDPOINT, data=b'{}'), 1800, 100)
        self.assertEqual(build.call_count, 1)

    def test_api_redirect_does_not_forward_key(self):
        with self.assertRaisesRegex(RuntimeError, "API 密钥"):
            image_api.NoApiRedirect().redirect_request(
                Request(image_api.NEBULA_ENDPOINT, data=b'{}'), None, 307, "redirect", {}, "https://other.example/",
            )

    def test_connection_refused_uses_proxy(self):
        first = SimpleNamespace(open=unittest.mock.Mock(side_effect=URLError(ConnectionRefusedError())))
        response = unittest.mock.MagicMock()
        response.__enter__.return_value.read.return_value = b'{}'
        second = SimpleNamespace(open=unittest.mock.Mock(return_value=response))
        with patch.object(image_api, "build_opener", side_effect=[first, second]) as build:
            result = image_api.read_request(Request(image_api.NEBULA_ENDPOINT, data=b'{}'), 1800, 100)
        self.assertEqual(result, b'{}')
        self.assertEqual(build.call_args.args[0].proxies["https"], image_api.PROXY)

    def test_http_error_is_sanitized(self):
        opener = SimpleNamespace(open=unittest.mock.Mock(side_effect=HTTPError(
            image_api.NEBULA_ENDPOINT, 401, "secret details", {}, None,
        )))
        with patch.object(image_api, "build_opener", return_value=opener):
            with self.assertRaisesRegex(RuntimeError, "HTTP 401") as caught:
                image_api.read_request(Request(image_api.NEBULA_ENDPOINT, data=b'{}'), 1800, 100)
        self.assertNotIn("secret details", str(caught.exception))

    def test_cli_rejects_2k_without_accessing_document(self):
        script = Path(__file__).resolve().parents[1] / "scripts/generate_illustrations.py"
        result = subprocess.run([
            sys.executable, "-X", "utf8", str(script), "missing.md", "--provider", "nebula", "--resolution", "2K",
        ], capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("仅支持", result.stderr)


if __name__ == "__main__":
    unittest.main()
