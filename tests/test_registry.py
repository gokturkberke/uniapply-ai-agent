"""Tests for the source registry loader and scoped queries."""

import json
from pathlib import Path

import pytest

from app.rag.metadata import SourceAuthority
from app.rag.registry import distinct_programmes, filter_sources, load_registry

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "registry_sample.json"
COMMITTED_MANIFEST = Path("data/registry/sources.json")


def test_fixture_manifest_loads_expected_count() -> None:
    sources = load_registry(FIXTURE_PATH)

    assert len(sources) == 4
    assert {s.source_id for s in sources} == {
        "alpha-ds-official",
        "alpha-ds-faq",
        "alpha-vpd-secondary",
        "beta-cs-official",
    }


def test_filter_by_university_isolates_institution() -> None:
    sources = load_registry(FIXTURE_PATH)

    alpha = filter_sources(sources, university_slug="uni-alpha")

    assert len(alpha) == 3
    # Core anti-blending guarantee: no other institution leaks through.
    assert all(s.university_slug == "uni-alpha" for s in alpha)
    assert all(s.university_slug != "uni-beta" for s in alpha)


def test_filter_by_unknown_university_returns_empty() -> None:
    sources = load_registry(FIXTURE_PATH)

    assert filter_sources(sources, university_slug="uni-unknown") == []


def test_filter_by_programme_and_authority() -> None:
    sources = load_registry(FIXTURE_PATH)

    secondary = filter_sources(sources, source_authority=SourceAuthority.secondary)
    assert [s.source_id for s in secondary] == ["alpha-vpd-secondary"]

    ds_primary = filter_sources(
        sources,
        university_slug="uni-alpha",
        programme_slug="msc-data-science",
        source_authority=SourceAuthority.primary,
    )
    assert {s.source_id for s in ds_primary} == {"alpha-ds-official", "alpha-ds-faq"}


def test_duplicate_source_id_raises(tmp_path: Path) -> None:
    entry = {
        "source_id": "dup-id",
        "title": "Duplicate",
        "university_slug": "uni-alpha",
        "programme_slug": "msc-data-science",
        "source_type": "official_page",
        "source_authority": "primary",
        "lang": "en",
        "url": "https://example.org/dup",
        "country_scope": ["all"],
    }
    manifest = tmp_path / "dup.json"
    manifest.write_text(json.dumps([entry, entry]), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate source_id"):
        load_registry(manifest)


def test_malformed_json_raises(tmp_path: Path) -> None:
    manifest = tmp_path / "broken.json"
    manifest.write_text("{not json", encoding="utf-8")

    with pytest.raises(ValueError, match="not valid JSON"):
        load_registry(manifest)


def test_non_list_payload_raises(tmp_path: Path) -> None:
    manifest = tmp_path / "object.json"
    manifest.write_text(json.dumps({"source_id": "x"}), encoding="utf-8")

    with pytest.raises(ValueError, match="JSON array"):
        load_registry(manifest)


def test_committed_manifest_holds_verified_cs_corpus() -> None:
    # The committed production manifest holds the verified Computer Science
    # mini-corpus: nine programme-scoped sources across five programmes. uni-assist
    # sources are attached only where the official page confirms uni-assist/VPD
    # (Paderborn, TUM); Konstanz/Stuttgart/Saarland are official-page-only.
    sources = load_registry(COMMITTED_MANIFEST)

    assert len(sources) == 9
    assert {s.source_id for s in sources} == {
        "konstanz-cis-official-programme-page",
        "paderborn-cs-official-programme-page",
        "uni-assist-vpd-paderborn-cs",
        "uni-assist-processing-time-paderborn-cs",
        "tum-informatics-official-programme-page",
        "uni-assist-vpd-tum-informatics",
        "uni-assist-processing-time-tum-informatics",
        "stuttgart-cs-official-programme-page",
        "saarland-cs-official-programme-page",
    }


def test_distinct_programmes_from_committed_manifest() -> None:
    # Five distinct programmes, sorted by (university_slug, programme_slug); the
    # nine sources (some sharing a programme) collapse to one entry per programme.
    programmes = distinct_programmes(load_registry(COMMITTED_MANIFEST))

    assert [(p.university_slug, p.programme_slug) for p in programmes] == [
        ("paderborn-university", "msc-computer-science"),
        ("saarland-university", "msc-computer-science"),
        ("technical-university-of-munich", "msc-informatics"),
        ("university-of-konstanz", "msc-computer-and-information-science"),
        ("university-of-stuttgart", "msc-computer-science"),
    ]
    konstanz = next(
        p for p in programmes if p.university_slug == "university-of-konstanz"
    )
    # Title from the primary source, trailing parenthetical stripped.
    assert konstanz.title == "University of Konstanz - M.Sc. Computer and Information Science"


def test_distinct_programmes_prefers_primary_and_excludes_none(tmp_path: Path) -> None:
    def src(source_id: str, title: str, programme_slug: str | None, authority: str) -> dict:
        return {
            "source_id": source_id,
            "title": title,
            "university_slug": "uni-alpha",
            "programme_slug": programme_slug,
            "source_type": "official_page",
            "source_authority": authority,
            "lang": "en",
            "url": f"https://example.org/{source_id}",
            "country_scope": ["all"],
        }

    manifest = tmp_path / "m.json"
    manifest.write_text(
        json.dumps(
            [
                src("a-secondary", "uni-assist - Plan your application (VPD)", "msc-x", "secondary"),
                src("a-primary", "Uni Alpha - M.Sc. X (programme page)", "msc-x", "primary"),
                src("a-none", "Uni Alpha - general info (overview)", None, "primary"),
            ]
        ),
        encoding="utf-8",
    )

    programmes = distinct_programmes(load_registry(manifest))

    # The programme_slug=None source is excluded; one programme remains.
    assert len(programmes) == 1
    assert programmes[0].programme_slug == "msc-x"
    # Primary source title chosen over the secondary, trailing parenthetical stripped.
    assert programmes[0].title == "Uni Alpha - M.Sc. X"
