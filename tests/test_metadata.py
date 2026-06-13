"""Tests for the source metadata contracts."""

from datetime import date

import pytest
from pydantic import ValidationError

from app.rag.metadata import (
    Language,
    RegisteredSource,
    SourceAuthority,
    SourceMetadata,
    SourceType,
)


def _valid_metadata_kwargs() -> dict:
    return {
        "university_slug": "tum-munich",
        "programme_slug": "msc-data-science",
        "source_type": SourceType.official_page,
        "source_authority": SourceAuthority.primary,
        "lang": Language.en,
        "url": "https://example.org/tum/data-science",
        "country_scope": ["all"],
    }


def test_valid_source_metadata_constructs() -> None:
    meta = SourceMetadata(**_valid_metadata_kwargs())

    assert meta.university_slug == "tum-munich"
    assert meta.last_updated is None  # optional, defaults to None


def test_valid_registered_source_constructs() -> None:
    source = RegisteredSource(
        source_id="tum-ds-official",
        title="TU Munich - MSc Data Science",
        last_updated=date(2026, 1, 15),
        **_valid_metadata_kwargs(),
    )

    assert source.source_id == "tum-ds-official"
    assert source.last_updated == date(2026, 1, 15)


def test_programme_slug_is_optional() -> None:
    kwargs = _valid_metadata_kwargs()
    kwargs["programme_slug"] = None

    meta = SourceMetadata(**kwargs)

    assert meta.programme_slug is None


@pytest.mark.parametrize("bad_slug", ["TUM-Munich", "tum munich", "tum_munich", "-tum"])
def test_uppercase_or_spaced_slug_rejected(bad_slug: str) -> None:
    kwargs = _valid_metadata_kwargs()
    kwargs["university_slug"] = bad_slug

    with pytest.raises(ValidationError):
        SourceMetadata(**kwargs)


def test_invalid_url_rejected() -> None:
    kwargs = _valid_metadata_kwargs()
    kwargs["url"] = "not-a-url"

    with pytest.raises(ValidationError):
        SourceMetadata(**kwargs)


def test_invalid_enum_value_rejected() -> None:
    kwargs = _valid_metadata_kwargs()
    kwargs["source_type"] = "press_release"  # not a SourceType member

    with pytest.raises(ValidationError):
        SourceMetadata(**kwargs)


def test_empty_country_scope_rejected() -> None:
    kwargs = _valid_metadata_kwargs()
    kwargs["country_scope"] = []

    with pytest.raises(ValidationError):
        SourceMetadata(**kwargs)


def test_country_scope_normalized_to_lowercase() -> None:
    kwargs = _valid_metadata_kwargs()
    kwargs["country_scope"] = [" Non-EU ", "IN"]

    meta = SourceMetadata(**kwargs)

    assert meta.country_scope == ["non-eu", "in"]
