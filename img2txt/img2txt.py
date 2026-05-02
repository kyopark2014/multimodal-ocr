#!/usr/bin/env python3
"""
단일 이미지 파일을 Markdown 텍스트로 변환합니다. `batch_img2txt`와 동일한 Bedrock 파이프라인을 사용합니다.

기본 저장 위치: 레포 루트의 artifacts/<이미지stem>.md

    python img2txt/img2txt.py path/to/page.png
    python img2txt/img2txt.py path/to/page.png -o custom/out.md
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import batch_img2txt as batch

_REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="이미지 파일 하나를 LLM으로 Markdown 텍스트로 변환합니다."
    )
    parser.add_argument("image", type=Path, help="입력 이미지 파일 경로")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="출력 .md 경로 (미지정 시 artifacts/<이미지파일명>.md)",
    )
    args = parser.parse_args()

    image_path = args.image.expanduser().resolve()
    if not image_path.is_file():
        print(f"Error: 파일이 없습니다: {image_path}", file=sys.stderr)
        return 1

    if image_path.suffix.lower() not in batch.IMAGE_EXTENSIONS:
        allowed = ", ".join(sorted(batch.IMAGE_EXTENSIONS))
        print(
            f"Error: 지원하지 않는 형식입니다 ({image_path.suffix}). 허용: {allowed}",
            file=sys.stderr,
        )
        return 1

    try:
        text = batch.extract_one(image_path)
    except Exception as e:
        print(f"Error: 추출 실패: {e}", file=sys.stderr)
        return 1

    if args.output:
        out_path = args.output.expanduser().resolve()
    else:
        out_path = (_REPO_ROOT / "artifacts" / f"{image_path.stem}.md").resolve()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text.rstrip() + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
