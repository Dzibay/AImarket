---
name: "aimarket-imagegen"
description: "Generate raster images through aimarket gpt-image-2 in Codex custom-provider sessions. Use whenever the user asks Codex to create or generate a bitmap image, illustration, photo, texture, mockup, sprite, banner, cover, or other raster asset and the first-party image_gen tool is unavailable or aimarket should pay for the image."
---

# aimarket Image Generation

Use the `aimarket_image.generate_image` MCP tool. It uses `AIMARKET_API_KEY`; do not request or require `OPENAI_API_KEY`.

- The tool saves a unique file under `$CODEX_HOME/generated_images/endpoint-image-tool/` and returns a preview.
- For a project asset, copy the selected result into the workspace with an ordinary sandboxed filesystem command, then update consuming code when required.
- Default to `1024x1024` and `quality=auto`. Use another supported size only when the requested composition needs it.
- After generation, inspect the preview and report the saved path. For project assets, update consuming code when the request requires it.
- This tool generates new images. For edits of an existing image, explain that this aimarket tool does not yet support edits instead of silently regenerating the source.
