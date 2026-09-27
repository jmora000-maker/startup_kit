"""Pydantic models for PDF page and document metadata validation."""

import math
from typing import Any, List
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PDFPageMetadata(BaseModel):
    """Schema for individual PDF page section metadata."""
    model_config = ConfigDict(extra="allow")

    page_number: int = Field(..., ge=1, strict=True, description="1-based page sequence number")
    rect: List[float] = Field(..., min_length=4, max_length=4, description="Bounding box [x0, y0, x1, y1]")

    @field_validator("rect", mode="before")
    @classmethod
    def validate_rect_elements(cls, v: Any) -> List[float]:
        if not isinstance(v, (list, tuple)):
            raise ValueError(f"rect must be a list or tuple of 4 numbers, got {type(v).__name__}")
        if len(v) != 4:
            raise ValueError(f"rect must contain exactly 4 coordinates, got {len(v)}")

        normalized: List[float] = []
        for i, coord in enumerate(v):
            # In Python, bool is a subclass of int (isinstance(True, int) is True). Reject bools explicitly.
            if isinstance(coord, bool) or not isinstance(coord, (int, float)):
                raise ValueError(f"rect coordinate at index {i} must be a finite number, got {type(coord).__name__}")
            if not math.isfinite(coord):
                raise ValueError(f"rect coordinate at index {i} must be finite (got {coord})")
            normalized.append(float(coord))
        return normalized

    @model_validator(mode="after")
    def validate_coordinate_bounds(self) -> "PDFPageMetadata":
        x0, y0, x1, y1 = self.rect
        if x1 < x0:
            raise ValueError(f"Invalid bounding box: x1 ({x1}) must be greater than or equal to x0 ({x0})")
        if y1 < y0:
            raise ValueError(f"Invalid bounding box: y1 ({y1}) must be greater than or equal to y0 ({y0})")
        return self


class PDFDocumentMetadata(BaseModel):
    """Schema for document-level PDF metadata."""
    model_config = ConfigDict(extra="allow")

    total_pages: int = Field(..., ge=0, strict=True, description="Total number of pages in document")
    title: str = Field(default="", description="Document title")
    author: str = Field(default="", description="Document author")
    subject: str = Field(default="", description="Document subject")

    @field_validator("title", "author", "subject", mode="before")
    @classmethod
    def normalize_string_or_none(cls, v: Any) -> str:
        if v is None:
            return ""
        if not isinstance(v, str):
            raise ValueError(f"Expected string or None, got {type(v).__name__}")
        return v
