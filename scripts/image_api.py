"""Nebula image2-4k、nanobanana 请求与图片保存。"""

import base64
import io
import json
import os
import re
import socket
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from PIL import Image
from env_config import get_provider_config


NEBULA_ENDPOINT = "https://img-api.apinebula.ai/v1/images/generations"
PROXY = "http://127.0.0.1:81"
MAX_IMAGE_BYTES = 50 * 1024 * 1024


class NoApiRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError("生图接口返回重定向，已停止以避免转发 API 密钥")


def get_provider(provider=None):
    provider = provider or os.environ.get("ILLUSTRATOR_IMAGE_PROVIDER", "gemini")
    if provider not in ("gemini", "nebula", "nanobanana"):
        raise ValueError("生图后端必须为 gemini、nebula 或 nanobanana")
    return provider


def validate_options(provider, aspect_ratio, resolution):
    if aspect_ratio not in ("16:9", "3:4") or resolution not in ("1K", "2K", "4K"):
        raise ValueError("不支持的图片比例或分辨率")
    if provider == "gemini" and resolution == "1K":
        raise ValueError("现有 Gemini 后端仅支持 2K、4K；1K 请使用 nanobanana")
    if provider == "nebula" and (aspect_ratio != "16:9" or resolution != "4K"):
        raise ValueError("Nebula image2-4k 仅支持 --ratio 16:9 --resolution 4K")


def add_provider_argument(parser):
    parser.add_argument(
        "--provider", choices=["gemini", "nebula", "nanobanana"],
        help="生图后端，默认读取 ILLUSTRATOR_IMAGE_PROVIDER，未配置时为 gemini",
    )


def resolve_options(parser, args, aspect_ratio=None, batch=False):
    ratio_key = "ILLUSTRATOR_BATCH_RATIO" if batch else "ILLUSTRATOR_SINGLE_RATIO"
    try:
        args.provider = get_provider(args.provider)
        config = get_provider_config(args.provider)
        args.ratio = aspect_ratio or getattr(args, "ratio", None) or config.get(ratio_key) or "16:9"
        args.resolution = args.resolution or config.get("ILLUSTRATOR_RESOLUTION") or (
            "4K" if args.provider == "nebula" else "2K"
        )
        validate_options(args.provider, args.ratio, args.resolution)
    except ValueError as exc:
        parser.error(f"{exc}；请检查 --ratio、--resolution 或 .env 中的 {ratio_key}、ILLUSTRATOR_RESOLUTION")


def read_request(request, timeout, limit):
    """仅在明确拒绝或连接尚未建立时用代理重试，避免重复计费。"""
    def read(opener):
        with opener.open(request, timeout=timeout) as response:
            content = response.read(limit + 1)
        if len(content) > limit:
            raise ValueError("接口响应超过大小限制")
        return content

    handlers = [NoApiRedirect()] if request.get_method() == "POST" else []
    try:
        return read(build_opener(*handlers))
    except HTTPError as exc:
        if exc.code != 403:
            raise RuntimeError(f"HTTP {exc.code}；请检查令牌分组和接口权限") from None
    except URLError as exc:
        # 超时或连接中断可能发生在服务器受理任务后，不能自动重发 POST。
        if request.get_method() == "POST" and not isinstance(
            exc.reason, (ConnectionRefusedError, socket.gaierror)
        ):
            raise RuntimeError("生图连接失败或超时，任务状态未知；请核实后再重试") from None
    except TimeoutError:
        if request.get_method() == "POST":
            raise RuntimeError("生图请求超时，任务状态未知；请核实后再重试") from None
    try:
        return read(build_opener(ProxyHandler({"http": PROXY, "https": PROXY}), *handlers))
    except HTTPError as exc:
        raise RuntimeError(f"代理请求返回 HTTP {exc.code}") from None
    except URLError:
        raise RuntimeError("代理连接失败；请检查 http://127.0.0.1:81") from None


def generate_nanobanana(prompt, output_path, aspect_ratio="16:9", resolution="2K"):
    """使用 Gemini 原生格式生图，不持久化含完整 Base64 的响应。"""
    validate_options("nanobanana", aspect_ratio, resolution)
    config = get_provider_config("nanobanana")
    api_key = config.get("NEBULA_NANOBANANA_API_KEY")
    if not api_key:
        raise ValueError("请设置 NEBULA_NANOBANANA_API_KEY，令牌必须属于 nanobanana 分组")
    model = config.get("NEBULA_NANOBANANA_MODEL", "gemini-3.1-flash-image")
    base_url = (config.get("NEBULA_NANOBANANA_BASE_URL") or "https://img-api.apinebula.ai").rstrip("/")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", model):
        raise ValueError("NEBULA_NANOBANANA_MODEL 必须为有效模型名称")
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "imageConfig": {"aspectRatio": aspect_ratio, "imageSize": resolution},
        },
    }
    request = Request(
        f"{base_url}/v1beta/models/{model}:generateContent",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    response = json.loads(read_request(request, timeout=1800, limit=80 * 1024 * 1024))
    if not isinstance(response, dict):
        raise ValueError("nanobanana 响应必须为 JSON 对象")
    candidates = response.get("candidates")
    if not isinstance(candidates, list) or not candidates or not isinstance(candidates[0], dict):
        raise ValueError("nanobanana 未返回图片候选；请检查模型可用性、额度或内容限制")
    content = candidates[0].get("content")
    parts = content.get("parts") if isinstance(content, dict) else None
    if not isinstance(parts, list):
        raise ValueError("nanobanana 响应缺少 content.parts 图片数据")
    for part in parts:
        if not isinstance(part, dict) or part.get("thought"):
            continue
        inline = part.get("inlineData")
        if not isinstance(inline, dict) or not str(inline.get("mimeType", "")).startswith("image/"):
            continue
        encoded = inline.get("data")
        if not isinstance(encoded, str) or not encoded:
            raise ValueError("nanobanana 图片 Base64 数据为空或格式错误")
        if len(encoded) > 4 * ((MAX_IMAGE_BYTES + 2) // 3):
            raise ValueError("图片超过 50 MiB 限制")
        image_bytes = base64.b64decode(encoded, validate=True)
        if len(image_bytes) > MAX_IMAGE_BYTES:
            raise ValueError("图片超过 50 MiB 限制")
        output_path = Path(output_path)
        with Image.open(io.BytesIO(image_bytes)) as image:
            image.load()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            image.save(output_path)
        return str(output_path)
    raise ValueError("nanobanana 未返回 inlineData 图片；请检查模型或内容限制")


def generate_nebula(prompt, output_path):
    config = get_provider_config("nebula")
    api_key = config.get("NEBULA_API_KEY")
    if not api_key:
        raise ValueError("请设置 NEBULA_API_KEY，令牌必须属于 image2-4k 分组")
    model = config.get("NEBULA_MODEL", "gpt-image-2-4k")
    size = config.get("NEBULA_SIZE", "3840x2160")
    quality = config.get("NEBULA_QUALITY", "high")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", model):
        raise ValueError("NEBULA_MODEL 必须为有效模型名称")
    if not re.fullmatch(r"[1-9][0-9]{0,4}x[1-9][0-9]{0,4}", size):
        raise ValueError("NEBULA_SIZE 必须为宽x高格式，例如 3840x2160")
    expected_size = tuple(int(value) for value in size.split("x"))
    if max(expected_size) > 16384 or expected_size[0] * expected_size[1] > 64 * 1024 * 1024:
        raise ValueError("NEBULA_SIZE 超过本地图片处理上限")
    if quality not in ("auto", "low", "medium", "high"):
        raise ValueError("NEBULA_QUALITY 必须为 auto、low、medium 或 high")
    payload = {
        "model": model, "prompt": prompt,
        "size": size, "quality": quality, "response_format": "url",
    }
    request = Request(
        config.get("NEBULA_ENDPOINT") or NEBULA_ENDPOINT,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    response = json.loads(read_request(request, timeout=1800, limit=80 * 1024 * 1024))
    if not isinstance(response, dict):
        raise ValueError("Nebula 响应必须为 JSON 对象")
    data = response.get("data")
    if not isinstance(data, list) or not data or not isinstance(data[0], dict):
        raise ValueError("Nebula 响应缺少 data[0] 图片数据")

    # 下载失败时可以复用响应，避免重新提交收费的生图任务。
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    response_path = output_path.with_suffix(output_path.suffix + ".response.json")
    response_path.write_text(json.dumps(response, ensure_ascii=False), encoding="utf-8")
    item = data[0]
    if item.get("url"):
        if urlsplit(item["url"]).scheme not in ("http", "https"):
            raise ValueError("图片 URL 必须使用 HTTP 或 HTTPS")
        # CDN 下载单独创建请求，不能携带 API 密钥。
        download = Request(item["url"], headers={"User-Agent": "Document-Illustrator/1.0"})
        try:
            image_bytes = read_request(download, timeout=180, limit=MAX_IMAGE_BYTES)
        except Exception as exc:
            raise RuntimeError(f"图片下载失败；响应已保存到 {response_path}，请勿直接重新生图") from exc
    elif item.get("b64_json"):
        image_bytes = base64.b64decode(item["b64_json"], validate=True)
        if len(image_bytes) > MAX_IMAGE_BYTES:
            raise ValueError("图片超过 50 MiB 限制")
    else:
        raise ValueError("Nebula 响应缺少 url 或 b64_json")

    with Image.open(io.BytesIO(image_bytes)) as image:
        image.load()
        if image.size != expected_size:
            raise ValueError(f"Nebula 实际图片尺寸为 {image.width}x{image.height}，预期 {size}")
        # 服务端可能返回 JPEG；按本地扩展名编码，避免把 JPEG 字节命名为 PNG。
        image.save(output_path)
    return str(output_path)
