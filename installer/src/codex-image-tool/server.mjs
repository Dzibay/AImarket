#!/usr/bin/env node

import fs from "node:fs";
import http from "node:http";
import https from "node:https";
import os from "node:os";
import path from "node:path";
import readline from "node:readline";
import crypto from "node:crypto";

const serverInfo = { name: "endpoint-image-generation", version: "1.0.0" };
const toolName = "generate_image";

function env(name, fallback = "") {
  return String(process.env[name] ?? fallback).trim();
}

function imageEndpoint() {
  const base = env("ROUTER_IMAGE_BASE_URL");
  if (!/^https?:\/\//i.test(base)) throw new Error("ROUTER_IMAGE_BASE_URL is not configured");
  return `${base.replace(/\/+$/, "")}/images/generations`;
}

function apiKey() {
  const keyName = env("ROUTER_IMAGE_API_KEY_ENV");
  const key = keyName ? env(keyName) : "";
  if (!key) throw new Error(`${keyName || "API key environment variable"} is not available to the image tool`);
  return key;
}

function defaultOutputPath(format) {
  const codexHome = env("CODEX_HOME", path.join(os.homedir(), ".codex"));
  const suffix = `${new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14)}-${crypto.randomBytes(4).toString("hex")}`;
  return path.join(codexHome, "generated_images", "endpoint-image-tool", `${suffix}.${format}`);
}

function normalizeOutput(args) {
  const format = String(args.output_format ?? "png").trim().toLowerCase();
  if (!["png", "jpeg", "webp"].includes(format)) throw new Error("output_format must be png, jpeg, or webp");
  const outputPath = path.resolve(defaultOutputPath(format));
  return { format, outputPath };
}

function requestImage(payload) {
  return new Promise((resolve, reject) => {
    const url = new URL(imageEndpoint());
    const body = Buffer.from(JSON.stringify(payload));
    const transport = url.protocol === "https:" ? https : http;
    const request = transport.request(url, {
      method: "POST",
      headers: {
        accept: "application/json",
        authorization: `Bearer ${apiKey()}`,
        "content-type": "application/json",
        "content-length": String(body.length),
        "user-agent": "codex-endpoint-image-tool/1.0",
      },
      timeout: 15 * 60 * 1000,
    }, (response) => {
      const chunks = [];
      let size = 0;
      response.on("data", (chunk) => {
        size += chunk.length;
        if (size > 64 * 1024 * 1024) {
          response.destroy(new Error("image response exceeded 64 MiB"));
          return;
        }
        chunks.push(Buffer.from(chunk));
      });
      response.on("end", () => {
        const text = Buffer.concat(chunks).toString("utf8");
        let parsed;
        try { parsed = JSON.parse(text); } catch { reject(new Error(`image API returned invalid JSON (HTTP ${response.statusCode ?? 0})`)); return; }
        if ((response.statusCode ?? 500) < 200 || (response.statusCode ?? 500) >= 300) {
          reject(new Error(parsed?.error?.message || `image API request failed with HTTP ${response.statusCode ?? 0}`));
          return;
        }
        resolve(parsed);
      });
    });
    request.on("timeout", () => request.destroy(new Error("image API request timed out")));
    request.on("error", reject);
    request.end(body);
  });
}

function atomicWrite(outputPath, bytes) {
  const directory = path.dirname(outputPath);
  fs.mkdirSync(directory, { recursive: true });
  const temporary = path.join(directory, `.${path.basename(outputPath)}.${process.pid}.${crypto.randomBytes(4).toString("hex")}.tmp`);
  try {
    fs.writeFileSync(temporary, bytes, { flag: "wx" });
    fs.renameSync(temporary, outputPath);
  } finally {
    try { fs.unlinkSync(temporary); } catch {}
  }
}

async function generateImage(args) {
  const prompt = String(args.prompt ?? "").trim();
  if (!prompt) throw new Error("prompt is required");
  const { format, outputPath } = normalizeOutput(args);
  const payload = {
    model: env("ROUTER_IMAGE_MODEL", "gpt-image-2"),
    prompt,
    n: 1,
    size: String(args.size ?? "1024x1024"),
    quality: String(args.quality ?? "auto"),
    output_format: format,
  };
  const response = await requestImage(payload);
  const item = Array.isArray(response?.data) ? response.data[0] : null;
  if (!item?.b64_json) throw new Error("image API response did not contain b64_json");
  let bytes;
  try { bytes = Buffer.from(item.b64_json, "base64"); } catch { throw new Error("image API returned invalid base64 image data"); }
  if (!bytes.length) throw new Error("image API returned an empty image");
  atomicWrite(outputPath, bytes);
  const mimeType = format === "jpeg" ? "image/jpeg" : `image/${format}`;
  const brand = env("ROUTER_IMAGE_BRAND", "the configured endpoint");
  return {
    content: [
      { type: "text", text: `Generated with ${brand} ${payload.model} and saved to ${outputPath}` },
      { type: "image", data: item.b64_json, mimeType },
    ],
    structuredContent: {
      path: outputPath,
      model: payload.model,
      size: payload.size,
      quality: payload.quality,
      format,
      bytes: bytes.length,
      revised_prompt: String(item.revised_prompt ?? ""),
    },
  };
}

const tool = {
  name: toolName,
  title: "Generate image",
  description: "Generate one raster image with the configured gpt-image-2 endpoint, save it under CODEX_HOME/generated_images/endpoint-image-tool, and return a preview.",
  inputSchema: {
    type: "object",
    additionalProperties: false,
    required: ["prompt"],
    properties: {
      prompt: { type: "string", minLength: 1, description: "Detailed image prompt." },
      size: { type: "string", default: "1024x1024", description: "Image size such as 1024x1024, 1536x1024, 1024x1536, 2048x2048, or 3840x2160." },
      quality: { type: "string", enum: ["auto", "low", "medium", "high"], default: "auto" },
      output_format: { type: "string", enum: ["png", "jpeg", "webp"], default: "png" },
    },
  },
  annotations: { title: "Generate image", readOnlyHint: false, destructiveHint: false, idempotentHint: false, openWorldHint: true },
};

async function handle(message) {
  if (!message || message.jsonrpc !== "2.0" || !message.method) return null;
  if (message.method === "notifications/initialized" || message.method.startsWith("notifications/")) return null;
  const id = message.id;
  try {
    let result;
    switch (message.method) {
      case "initialize":
        result = { protocolVersion: message.params?.protocolVersion || "2025-06-18", capabilities: { tools: { listChanged: false } }, serverInfo };
        break;
      case "ping": result = {}; break;
      case "tools/list": result = { tools: [tool] }; break;
      case "tools/call":
        if (message.params?.name !== toolName) throw new Error(`unknown tool: ${message.params?.name ?? ""}`);
        result = await generateImage(message.params?.arguments ?? {});
        break;
      default:
        return { jsonrpc: "2.0", id, error: { code: -32601, message: `method not found: ${message.method}` } };
    }
    return { jsonrpc: "2.0", id, result };
  } catch (error) {
    if (message.method === "tools/call") {
      return { jsonrpc: "2.0", id, result: { isError: true, content: [{ type: "text", text: error instanceof Error ? error.message : String(error) }] } };
    }
    return { jsonrpc: "2.0", id, error: { code: -32603, message: error instanceof Error ? error.message : String(error) } };
  }
}

const input = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
for await (const line of input) {
  if (!line.trim()) continue;
  let message;
  try { message = JSON.parse(line); } catch { continue; }
  const response = await handle(message);
  if (response) process.stdout.write(`${JSON.stringify(response)}\n`);
}
