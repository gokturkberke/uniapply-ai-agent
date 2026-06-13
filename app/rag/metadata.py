"""Canonical metadata contracts for registered admission sources.

These models are the single source of truth for source-level metadata and are
reused by ingestion, indexing, and retrieval. Slugs are validated as lowercase
kebab-case so that university/programme scoping (the rule that prevents blending
requirements across institutions) is enforced mechanically, not by convention.
"""

import re
from datetime import date
from enum import Enum

from pydantic import BaseModel, HttpUrl, field_validator

_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _validate_slug(value: str, field_name: str) -> str:
    if not _SLUG_PATTERN.fullmatch(value):
        raise ValueError(
            f"{field_name} must be lowercase kebab-case "
            f"(e.g. 'tum-munich'); got {value!r}"
        )
    return value


class SourceType(str, Enum):
    official_page = "official_page"
    faq = "faq"
    pdf_guide = "pdf_guide"
    deadline_schedule = "deadline_schedule"
    vpd_info = "vpd_info"


class SourceAuthority(str, Enum):
    primary = "primary"  # official university pages: final authority
    secondary = "secondary"  # uni-assist (procedural), DAAD (orientation)


class Language(str, Enum):
    de = "de"
    en = "en"


class SourceMetadata(BaseModel):
    """Source-level metadata attached to every registered source.

    Chunk-level fields (chunk_id, page, parent_id) are intentionally absent;
    they are added when the chunking/indexing phase lands.
    """

    university_slug: str
    programme_slug: str | None = None
    source_type: SourceType
    source_authority: SourceAuthority
    lang: Language
    url: HttpUrl
    country_scope: list[str]
    last_updated: date | None = None

    @field_validator("university_slug")
    @classmethod
    def _check_university_slug(cls, value: str) -> str:
        return _validate_slug(value, "university_slug")

    @field_validator("programme_slug")
    @classmethod
    def _check_programme_slug(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_slug(value, "programme_slug")

    @field_validator("country_scope")
    @classmethod
    def _check_country_scope(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError(
                "country_scope must contain at least one token (e.g. ['all'])"
            )
        normalized: list[str] = []
        for token in value:
            token_normalized = token.strip().lower()
            if not token_normalized:
                raise ValueError("country_scope tokens must be non-empty")
            normalized.append(token_normalized)
        return normalized


class RegisteredSource(SourceMetadata):
    """A source registered in the curated registry manifest."""

    source_id: str
    title: str
    local_path: str | None = None

    @field_validator("source_id")
    @classmethod
    def _check_source_id(cls, value: str) -> str:
        return _validate_slug(value, "source_id")
