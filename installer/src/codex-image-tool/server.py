#!/usr/bin/env python3

import base64
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile
from urllib.error import HTTPError
from urllib.request import Request, urlopen

TOOL_NAME = "generate_image"


def env(name, fallback=""):
    return str(os.environ.get(name, fallback)).strip()


def fail(message):
    raise RuntimeError(message)


def endpoint():
    base = env("ROUTER_IMAGE_BASE_URL")
    if not base.startswith(("http://", "https://")):
        fail("ROUTER_IMAGE_BASE_URL is not configured")
    return base.rstrip("/") + "/images/generations"


def api_key():
    name = env("ROUTER_IMAGE_API_KEY_ENV")
    key = env(name) if name else ""
    if not key:
        fail(f"{name or 'API key environment variable'} is not available to the image tool")
    return key


def output_settings(args):
    image_format = str(args.get("output_format") or "png").strip().lower()
    if image_format not in ("png", "jpeg", "webp"):
        fail("output_format must be png, jpeg, or webp")
    home = Path(env("CODEX_HOME", str(Path.home() / ".codex")))
    output = home / "generated_images" / "endpoint-image-tool" / f"{secrets.token_hex(8)}.{image_format}"
    return image_format, output


def generate(args):
    prompt = str(args.get("prompt") or "").strip()
    if not prompt:
        fail("prompt is required")
    image_format, output = output_settings(args)
    payload = {
        "model": env("ROUTER_IMAGE_MODEL", "gpt-image-2"),
        "prompt": prompt,
        "n": 1,
        "size": str(args.get("size") or "1024x1024"),
        "quality": str(args.get("quality") or "auto"),
        "output_format": image_format,
    }
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = Request(endpoint(), data=body, method="POST", headers={
        "Accept": "application/json",
        "Authorization": "Bearer " + api_key(),
        "Content-Type": "application/json",
        "User-Agent": "codex-endpoint-image-tool/1.0",
    })
    try:
        with urlopen(request, timeout=900) as response:
            response_body = response.read(64 * 1024 * 1024 + 1)
            if len(response_body) > 64 * 1024 * 1024:
                fail("image response exceeded 64 MiB")
    except HTTPError as error:
        try:
            detail = json.loads(error.read().decode("utf-8")).get("error", {}).get("message")
        except Exception:
            detail = None
        fail(detail or f"image API request failed with HTTP {error.code}")
    try:
        parsed = json.loads(response_body.decode("utf-8"))
        item = parsed["data"][0]
        encoded = item["b64_json"]
        image_bytes = base64.b64decode(encoded, validate=True)
    except Exception:
        fail("image API response did not contain valid b64_json")
    if not image_bytes:
        fail("image API returned an empty image")
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix="." + output.name + ".", suffix=".tmp", dir=output.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(image_bytes)
        os.replace(temporary, output)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    mime = "image/jpeg" if image_format == "jpeg" else "image/" + image_format
    brand = env("ROUTER_IMAGE_BRAND", "the configured endpoint")
    return {
        "content": [
            {"type": "text", "text": f"Generated with {brand} {payload['model']} and saved to {output}"},
            {"type": "image", "data": encoded, "mimeType": mime},
        ],
        "structuredContent": {
            "path": str(output), "model": payload["model"], "size": payload["size"],
            "quality": payload["quality"], "format": image_format, "bytes": len(image_bytes),
            "revised_prompt": str(item.get("revised_prompt") or ""),
        },
    }


TOOL = {
    "name": TOOL_NAME,
    "title": "Generate image",
    "description": "Generate one raster image with the configured gpt-image-2 endpoint, save it under CODEX_HOME/generated_images/endpoint-image-tool, and return a preview.",
    "inputSchema": {
        "type": "object", "additionalProperties": False, "required": ["prompt"],
        "properties": {
            "prompt": {"type": "string", "minLength": 1, "description": "Detailed image prompt."},
            "size": {"type": "string", "default": "1024x1024"},
            "quality": {"type": "string", "enum": ["auto", "low", "medium", "high"], "default": "auto"},
            "output_format": {"type": "string", "enum": ["png", "jpeg", "webp"], "default": "png"},
        },
    },
    "annotations": {"title": "Generate image", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": True},
}


def handle(message):
    method = message.get("method", "")
    if method.startswith("notifications/"):
        return None
    request_id = message.get("id")
    try:
        if method == "initialize":
            result = {"protocolVersion": message.get("params", {}).get("protocolVersion", "2025-06-18"), "capabilities": {"tools": {"listChanged": False}}, "serverInfo": {"name": "endpoint-image-generation", "version": "1.0.0"}}
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": [TOOL]}
        elif method == "tools/call":
            params = message.get("params", {})
            if params.get("name") != TOOL_NAME:
                fail("unknown tool: " + str(params.get("name", "")))
            result = generate(params.get("arguments") or {})
        else:
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "method not found: " + method}}
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    except Exception as error:
        if method == "tools/call":
            return {"jsonrpc": "2.0", "id": request_id, "result": {"isError": True, "content": [{"type": "text", "text": str(error)}]}}
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32603, "message": str(error)}}


for line in sys.stdin:
    try:
        request_message = json.loads(line)
    except Exception:
        continue
    response_message = handle(request_message)
    if response_message is not None:
        sys.stdout.write(json.dumps(response_message, separators=(",", ":")) + "\n")
        sys.stdout.flush()
