"""Download a DVF CSV from data.gouv.fr.

The geo-dvf endpoint publishes per-year CSVs broken down by departement at
`{base}/{year}/departements/{departement}.csv.gz`. We stream the gzipped
response straight to disk to handle multi-GB files without buffering.
"""

from __future__ import annotations

from pathlib import Path

import httpx
from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


def build_url(base_url: str, year: int, departement: str) -> str:
    return f"{base_url.rstrip('/')}/{year}/departements/{departement}.csv.gz"


@retry(
    retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    stop=stop_after_attempt(4),
    reraise=True,
)
def _stream_to_disk(url: str, dest: Path, timeout: int = 300) -> int:
    tmp = dest.with_suffix(dest.suffix + ".part")
    bytes_written = 0
    with httpx.stream("GET", url, timeout=timeout, follow_redirects=True) as response:
        response.raise_for_status()
        with tmp.open("wb") as f:
            for chunk in response.iter_bytes(chunk_size=1 << 20):
                f.write(chunk)
                bytes_written += len(chunk)
    tmp.replace(dest)
    return bytes_written


def download_dvf(
    base_url: str, year: int, departement: str, dest_dir: Path, *, timeout: int = 300
) -> Path:
    """Download one (year, departement) DVF CSV.gz. Returns the local path.

    Idempotent: if the file already exists with size > 0, the download is skipped.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"dvf_{year}_dep{departement}.csv.gz"
    if dest.exists() and dest.stat().st_size > 0:
        logger.info("Skipping {} (already exists, {:.1f} MB)", dest.name, dest.stat().st_size / 1e6)
        return dest

    url = build_url(base_url, year, departement)
    logger.info("Downloading {}", url)
    bytes_written = _stream_to_disk(url, dest)
    logger.success("Downloaded {} ({:.1f} MB)", dest.name, bytes_written / 1e6)
    return dest
