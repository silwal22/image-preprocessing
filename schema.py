from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


class PanFields(BaseModel):
    """Normalized PAN card fields as extracted from the document.

    The schema intentionally avoids Pydantic extra-forbid settings because Gemini's
    response_schema rejects unsupported JSON Schema keys like additionalProperties.
    """

    model_config = ConfigDict()

    full_name: str | None = None
    father_name: str | None = None
    pan_number: str | None = None
    date_of_birth: str | None = None

    @field_validator("full_name", "father_name", "pan_number", "date_of_birth", mode="before")
    @classmethod
    def clean_optional_strings(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip()
        return value

    @property
    def pan_format_valid(self) -> bool:
        if self.pan_number is None:
            return False
        normalized = self.pan_number.strip().upper().replace(" ", "")
        return bool(PAN_PATTERN.match(normalized))


class PanExtraction(PanFields):
    """Structured response expected from the multimodal extractor."""

    model_config = ConfigDict()

    confidence: float
    image_issues: list[str] = []
    unreadable_fields: list[str] = []

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        if not 0.0 <= float(value) <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return float(value)

    @field_validator("image_issues", "unreadable_fields", mode="before")
    @classmethod
    def ensure_list_fields(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return [str(value).strip()] if str(value).strip() else []

    @model_validator(mode="after")
    def validate_pan_number_shape(self) -> "PanExtraction":
        if isinstance(self.pan_number, str):
            upper = self.pan_number.strip().upper()
            if upper and not PAN_PATTERN.match(upper.replace(" ", "")):
                self.pan_number = self.pan_number
        return self

    @property
    def pan_format_valid(self) -> bool:
        if self.pan_number is None:
            return False
        normalized = self.pan_number.strip().upper().replace(" ", "")
        return bool(PAN_PATTERN.match(normalized))
