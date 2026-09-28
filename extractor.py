from __future__ import annotations

import argparse
import io
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image, UnidentifiedImageError

from preprocess import preprocess, fix_exif_orientation
from schema import PanExtraction

logger = logging.getLogger(__name__)

PROMPT = """
The image is a photo of a PAN card and may be rotated, blurry, dark or partial.
Extract only what is actually visible. If a field is unreadable, return null.
NEVER guess or invent characters.
Report confidence (0-1) reflecting how legible the document was, list image_issues and unreadable_fields.
Dates must be DD/MM/YYYY. PAN number must be uppercase with no spaces.
"""


def _load_gemini_settings() -> tuple[str, str]:
    load_dotenv()
    model = os.getenv("GEMINI_MODEL")
    api_key = os.getenv("GEMINI_API_KEY")
    if not model or not api_key:
        raise RuntimeError("GEMINI_MODEL and GEMINI_API_KEY must be set in the environment.")
    return model, api_key


def _prepare_image_for_model(image_path: str | Path, steps: set[str]) -> tuple[bytes, list[str]]:
    image = Image.open(image_path)
    image = fix_exif_orientation(image)
    image, steps_applied = preprocess(image, steps)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=95)
    return buffer.getvalue(), steps_applied


def _response_to_extraction(response: Any) -> PanExtraction:
    if hasattr(response, "parsed") and response.parsed is not None:
        parsed = response.parsed
        if isinstance(parsed, PanExtraction):
            return parsed
        if isinstance(parsed, dict):
            return PanExtraction.model_validate(parsed)

    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return PanExtraction.model_validate_json(text)

    raise ValueError("Gemini returned a response without a parseable JSON payload.")


def extract(image_path: str | Path, steps: frozenset[str] = frozenset()) -> dict[str, Any]:
    """Extract PAN fields from an image using Gemini and return structured metadata."""
    started = time.perf_counter()
    model_name: str | None = None
    raw_response: Any = None
    extraction: PanExtraction | None = None
    error: str | None = None
    steps_applied: list[str] = []

    try:
        model_name, api_key = _load_gemini_settings()
        image_bytes, steps_applied = _prepare_image_for_model(image_path, set(steps))
        client = genai.Client(api_key=api_key)

        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[
                        types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                        PROMPT,
                    ],
                    config=types.GenerateContentConfig(
                        temperature=0,
                        response_mime_type="application/json",
                        response_schema=PanExtraction,
                    ),
                )
                raw_response = response
                extraction = _response_to_extraction(response)
                break
            except Exception as exc:  # pragma: no cover - API behavior varies by SDK version
                logger.warning("Gemini extraction attempt %s failed: %s", attempt + 1, exc)
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)

    except (FileNotFoundError, UnidentifiedImageError, OSError, ValueError, TypeError, RuntimeError) as exc:
        error = f"{type(exc).__name__}: {exc}"
        logger.error("PAN extraction failed for %s: %s", image_path, exc)
    except Exception as exc:  # pragma: no cover - defensive for SDK-specific errors
        error = f"{type(exc).__name__}: {exc}"
        logger.exception("Unexpected extraction failure for %s", image_path)

    latency = time.perf_counter() - started
    return {
        "extraction": extraction,
        "raw_response": raw_response,
        "latency_s": round(latency, 3),
        "steps_applied": steps_applied,
        "error": error,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract PAN card fields from an image using Gemini.")
    parser.add_argument("image_path", type=str, help="Path to the PAN card image.")
    parser.add_argument(
        "--steps",
        nargs="+",
        default=[],
        help="Optional preprocessing steps: exif rotate brightness. Example: --steps rotate brightness",
    )
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = _parse_args()
    result = extract(args.image_path, frozenset(args.steps))
    print(json.dumps({
        "extraction": result["extraction"].model_dump() if result["extraction"] else None,
        "raw_response": getattr(result["raw_response"], "text", None) or result["raw_response"],
        "latency_s": result["latency_s"],
        "steps_applied": result["steps_applied"],
        "error": result["error"],
    }, indent=2, default=str))
    return 0 if result["error"] is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
