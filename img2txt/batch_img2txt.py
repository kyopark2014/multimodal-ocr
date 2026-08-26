#!/usr/bin/env python3
"""
배치 이미지→Markdown: Bedrock(LLM) 파이프라인으로 폴더 내 이미지를 처리합니다.
    python img2txt/batch_img2txt.py "<folder_with_images>"
"""
from __future__ import annotations

import argparse
import base64
import logging
import re
import sys
import traceback
from io import BytesIO
from pathlib import Path
from typing import Optional

import boto3
from botocore.config import Config
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage
from PIL import Image

logging.basicConfig(
    level=logging.INFO,
    format="%(filename)s:%(lineno)d | %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("batch-img2text")

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff", ".tif"}

LLM_PROMPT = (
    "LANGUAGE (mandatory, highest priority):\n"
    "- Detect the primary language of the readable text on the page.\n"
    "- Write the ENTIRE Markdown output in that same language only "
    "(body, headings, lists, captions, figure/table/diagram descriptions, "
    "layout notes, and empty-page remarks).\n"
    "- If the page text is English, the whole output MUST be English. "
    "Do NOT translate into Korean. Do NOT use Korean labels such as "
    "'시각적 요소 설명', '표지', or Korean empty-page messages.\n"
    "- If the page text is Korean, keep the whole output in Korean.\n"
    "- Never mix languages. Never paraphrase into another language.\n\n"
    "Convert the page to Markdown with headings (#/##), lists, emphasis, and "
    "code blocks as appropriate. Exclude top-of-page headers and bottom footers "
    "(e.g. running titles, page numbers).\n\n"
    "If the page has figures, tables, photos, screenshots, or diagrams, describe "
    "what they show and how they relate to the body — in the same language as the "
    "page text."
)

_bedrock_region = "us-west-2"
_model_id = "us.anthropic.claude-opus-4-6-v1"
_model_type = "claude"


def _get_chat() -> ChatBedrock:
    stop_sequence = "\n\nHuman:" if _model_type == "claude" else ""
    max_tokens = 16384 if "claude-4" in _model_id else 8192

    boto3_bedrock = boto3.client(
        service_name="bedrock-runtime",
        region_name=_bedrock_region,
        config=Config(
            retries={"max_attempts": 30},
            read_timeout=300,
        ),
    )

    parameters = {
        "max_tokens": max_tokens,
        "temperature": 0.1,
        "top_k": 250,
        "stop_sequences": [stop_sequence],
    }

    return ChatBedrock(
        model_id=_model_id,
        client=boto3_bedrock,
        model_kwargs=parameters,
        region_name=_bedrock_region,
    )


def _prepare_image_base64(
    image_content: bytes,
    max_size: int = 5 * 1024 * 1024,
    max_pixels: int = 2000000,
) -> str:
    img = Image.open(BytesIO(image_content))
    width, height = img.size
    logger.info("Image size: %sx%s, pixels: %s", width, height, width * height)

    is_resized = False
    while width * height > max_pixels:
        width = int(width / 2)
        height = int(height / 2)
        is_resized = True
        logger.info("Resized to %sx%s", width, height)

    if is_resized:
        img = img.resize((width, height))

    max_attempts = 5
    for attempt in range(max_attempts):
        buffer = BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        img_bytes = buffer.getvalue()
        img_base64 = base64.b64encode(img_bytes).decode("utf-8")
        base64_size = len(img_base64.encode("utf-8"))
        logger.info("Attempt %s: base64_size = %s bytes", attempt + 1, base64_size)

        if base64_size <= max_size:
            return img_base64

        width = int(width * 0.8)
        height = int(height * 0.8)
        img = img.resize((width, height))
        logger.info("Resizing to %sx%s due to size limit", width, height)

    raise ValueError("이미지 크기가 너무 큽니다. 5MB 이하의 이미지를 사용해주세요.")


def _extract_text_with_llm(img_base64: str, prompt: Optional[str] = None) -> str:
    query = prompt or "텍스트를 추출해서 markdown 포맷으로 변환하세요. 원문의 언어를 그대로 유지하고 번역하지 마세요. <result> tag를 붙여주세요."

    multimodal = _get_chat()
    messages = [
        HumanMessage(
            content=[
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{img_base64}"},
                },
                {"type": "text", "text": query},
            ]
        )
    ]

    extracted_text = ""
    for attempt in range(5):
        logger.info("LLM attempt: %s", attempt)
        try:
            result = multimodal.invoke(messages)
            extracted_text = result.content
            break
        except Exception:
            logger.warning("LLM error: %s", traceback.format_exc())

    if len(extracted_text) < 10:
        extracted_text = "텍스트를 추출하지 못하였습니다."

    return extracted_text


def _parse_result(text: str) -> str:
    if text.find("<result>") != -1:
        return text[text.find("<result>") + 8 : text.find("</result>")]
    return text


def natural_key(path: Path):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", path.name)]


def list_image_files(folder: Path) -> list[Path]:
    out = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS]
    out.sort(key=natural_key)
    return out


def extract_one(image_path: Path) -> str:
    with open(image_path, "rb") as f:
        raw = f.read()
    b64 = _prepare_image_base64(raw)
    raw_text = _extract_text_with_llm(b64, LLM_PROMPT)
    return _parse_result(raw_text).strip()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="폴더 내 이미지를 LLM으로 Markdown 변환 후 폴더명.md로 저장"
    )
    parser.add_argument("folder", type=Path, help="이미지가 들어 있는 폴더 경로")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="출력 .md 경로 (기본: 폴더 안의 폴더이름.md)",
    )
    args = parser.parse_args()

    folder = args.folder.expanduser().resolve()
    if not folder.is_dir():
        print(f"Error: 폴더가 아닙니다: {folder}", file=sys.stderr)
        return 1

    images = list_image_files(folder)
    if not images:
        print(f"Error: 이미지 파일이 없습니다: {folder}", file=sys.stderr)
        return 1

    out_path = args.output.expanduser().resolve() if args.output else folder / f"{folder.name}.md"

    parts: list[str] = []
    for i, img in enumerate(images, start=1):
        print(f"[{i}/{len(images)}] {img.name}", file=sys.stderr)
        try:
            body = extract_one(img)
        except Exception as e:
            body = f"> (추출 오류: {e})"
        parts.append(f"## 파일: {img.name}\n\n{body}\n")

    text = "\n".join(parts).rstrip() + "\n"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
