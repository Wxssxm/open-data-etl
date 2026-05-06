"""Tests for the download module."""

from __future__ import annotations

from pathlib import Path

import httpx
import respx

from dvf_etl.download.dvf import build_url, download_dvf

BASE = "https://files.data.gouv.fr/geo-dvf/latest/csv"


def test_build_url() -> None:
    assert build_url(BASE, 2023, "75") == f"{BASE}/2023/departements/75.csv.gz"


@respx.mock
def test_download_writes_file(tmp_path: Path) -> None:
    url = build_url(BASE, 2023, "75")
    payload = b"FAKE GZIP CONTENT" * 100
    respx.get(url).mock(return_value=httpx.Response(200, content=payload))

    dest = download_dvf(BASE, 2023, "75", tmp_path)

    assert dest.exists()
    assert dest.read_bytes() == payload


@respx.mock
def test_download_idempotent(tmp_path: Path) -> None:
    url = build_url(BASE, 2023, "75")
    route = respx.get(url).mock(return_value=httpx.Response(200, content=b"x" * 50))

    download_dvf(BASE, 2023, "75", tmp_path)
    download_dvf(BASE, 2023, "75", tmp_path)
    assert route.call_count == 1  # second call skipped


@respx.mock
def test_download_retries_on_500(tmp_path: Path) -> None:
    url = build_url(BASE, 2023, "75")
    route = respx.get(url).mock(
        side_effect=[httpx.Response(500), httpx.Response(200, content=b"hello")]
    )

    download_dvf(BASE, 2023, "75", tmp_path)
    assert route.call_count == 2
