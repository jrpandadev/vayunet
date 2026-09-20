#!/usr/bin/env python3
"""
VayuNet — MODIS MAIAC MCD19A2 V061 downloader.

Downloads MODIS/Terra+Aqua Land Aerosol Optical Depth Daily L2G Global 1km SIN Grid V061
granules intersecting the Delhi-NCR AOI.

Source: NASA Earthdata CMR
Collection: MCD19A2
Version: 061
Coverage: 2022-01-01 through 2026-08-31
NCR bounding box: West = 76.0 South = 27.0 East = 78.5 North = 29.5

The script:
1. Queries NASA CMR.
2. Uses temporal + bounding-box filtering.
3. Paginates using CMR Search-After.
4. Collects unique GET DATA URLs.
5. Downloads files with bounded concurrency.
6. Skips existing files.
7. Retries failed downloads.
8. Writes a manifest.
9. Does NOT modify or extract the HDF data.
10. Does NOT delete existing files.

Authentication:
NASA Earthdata Login is required for downloading protected Earthdata files.
Set one of:
  EARTHDATA_USERNAME
  EARTHDATA_PASSWORD
as environment variables, or configure ~/.netrc.
Recommended: Use ~/.netrc rather than putting credentials directly in this file.
"""

from __future__ import annotations

import argparse
import csv
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from tqdm import tqdm
from urllib3.util.retry import Retry
from dotenv import load_dotenv

# ---------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------
CMR_BASE_URL = "https://cmr.earthdata.nasa.gov"
CMR_URL = f"{CMR_BASE_URL}/search/granules.umm_json"
SHORT_NAME = "MCD19A2"
VERSION = "061"
START_DATE = "2022-01-01T00:00:00Z"
END_DATE = "2026-08-31T23:59:59Z"
TEMPORAL = f"{START_DATE},{END_DATE}"

# Delhi-NCR bounding box:
# west, south, east, north
BBOX = "76.0,27.0,78.5,29.5"

DOWNLOAD_DIR = Path("data/raw/satellite/modis_maiac")
MANIFEST_PATH = DOWNLOAD_DIR / "_mcd19a2_manifest.csv"

PAGE_SIZE = 200
MAX_WORKERS = 5
REQUEST_TIMEOUT = 120
MAX_RETRIES = 3
DOWNLOAD_CHUNK_SIZE = 1024 * 1024  # 1 MiB


# ---------------------------------------------------------------------
# AUTHENTICATION
# ---------------------------------------------------------------------
load_dotenv()


class EarthdataSession(requests.Session):
    AUTH_HOST = 'urs.earthdata.nasa.gov'

    def __init__(self, username, password):
        super().__init__()
        self.earthdata_auth = (username, password)

    def rebuild_auth(self, prepared_request, response):
        headers = prepared_request.headers
        url = prepared_request.url
        if 'Authorization' in headers:
            original_parsed = urlparse(response.request.url)
            redirect_parsed = urlparse(url)
            if (original_parsed.hostname != redirect_parsed.hostname) and redirect_parsed.hostname != self.AUTH_HOST:
                del headers['Authorization']
        return


# ---------------------------------------------------------------------
# HTTP SESSION
# ---------------------------------------------------------------------
def create_session() -> requests.Session:
    """
    Create a requests session with automatic retry handling and Earthdata authentication.
    """
    username = os.environ.get("EARTHDATA_USERNAME")
    password = os.environ.get("EARTHDATA_PASSWORD")
    if username and password:
        session = EarthdataSession(username, password)
    else:
        session = requests.Session()

    retry = Retry(
        total=MAX_RETRIES,
        connect=MAX_RETRIES,
        read=MAX_RETRIES,
        status=MAX_RETRIES,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(
        max_retries=retry,
        pool_connections=MAX_WORKERS,
        pool_maxsize=MAX_WORKERS,
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    session.headers.update(
        {
            "User-Agent": "VayuNet-MCD19A2-Downloader/1.0",
            "Accept": "application/json",
        }
    )

    return session


# ---------------------------------------------------------------------
# CMR QUERY
# ---------------------------------------------------------------------
def query_cmr(
    session: requests.Session,
    search_after: Optional[str] = None,
):
    """
    Query CMR granules using temporal and spatial filters.
    """
    url = f"{CMR_BASE_URL}/search/granules.umm_json"
    params = {
        "short_name": SHORT_NAME,
        "version": VERSION,
        "page_size": PAGE_SIZE,
        "temporal": f"{START_DATE},{END_DATE}",
        "bounding_box": BBOX,
    }

    headers = {
        "Accept": "application/json",
    }
    if search_after:
        headers["CMR-Search-After"] = search_after

    response = session.get(
        url,
        params=params,
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response, response.json()


# ---------------------------------------------------------------------
# EXTRACT DOWNLOAD URL
# ---------------------------------------------------------------------
def extract_download_urls(item: dict) -> list[str]:
    """
    Extract GET DATA URLs from a CMR UMM-G granule.
    """
    urls: list[str] = []
    umm = item.get("umm", {})
    for related_url in umm.get("RelatedUrls", []):
        if related_url.get("Type") == "GET DATA":
            url = related_url.get("URL")
            if url:
                urls.append(url)
    return urls


# ---------------------------------------------------------------------
# COLLECT GRANULES
# ---------------------------------------------------------------------
def collect_granules(
    session: requests.Session,
):
    """
    Collect all unique download URLs from CMR.
    Returns (urls, all_granule_ids, temporal_ranges)
    """
    search_after = None
    urls: list[str] = []
    seen_urls: set[str] = set()
    granule_count = 0
    page_count = 0

    granule_ids = []
    temporal_ranges = []

    print()
    print("=" * 72)
    print("VayuNet MODIS MAIAC MCD19A2 V061")
    print("=" * 72)
    print(f"Temporal : {START_DATE} -> {END_DATE}")
    print(f"NCR AOI  : {BBOX}")
    print()

    while True:
        page_count += 1
        print(f"Querying CMR page {page_count}...")
        response, data = query_cmr(
            session,
            search_after,
        )

        items = data.get("items", [])
        if not items:
            break

        for item in items:
            granule_count += 1
            meta = item.get("meta", {})
            umm = item.get("umm", {})

            granule_ids.append(meta.get("native-id", "unknown"))

            temporal = umm.get("TemporalExtent", {}).get("RangeDateTime", {})
            t_start = temporal.get("BeginningDateTime")
            t_end = temporal.get("EndingDateTime")
            if t_start and t_end:
                temporal_ranges.append((t_start, t_end))

            for url in extract_download_urls(item):
                if url not in seen_urls:
                    seen_urls.add(url)
                    urls.append(url)

        search_after = response.headers.get("CMR-Search-After")
        if not search_after:
            break

    print()
    print(f"CMR granules discovered : {granule_count:,}")
    print(f"Unique download URLs    : {len(urls):,}")

    return urls, granule_ids, temporal_ranges


# ---------------------------------------------------------------------
# FILE NAME
# ---------------------------------------------------------------------
def filename_from_url(url: str) -> str:
    """
    Safely extract the filename from a download URL.
    """
    path = urlparse(url).path
    filename = os.path.basename(path)
    if not filename:
        raise ValueError(f"Could not determine filename from URL: {url}")
    return filename


# ---------------------------------------------------------------------
# DOWNLOAD ONE FILE
# ---------------------------------------------------------------------
def download_file(
    url: str,
):
    """
    Download one granule.
    Returns: (status, filename, message)
    """
    filename = filename_from_url(url)
    output_path = DOWNLOAD_DIR / filename

    if output_path.exists() and output_path.stat().st_size > 0:
        return (
            "skipped",
            filename,
            "already exists",
        )

    temporary_path = output_path.with_suffix(
        output_path.suffix + ".part"
    )

    session = create_session()

    try:
        # Determine auth
        auth = getattr(session, "earthdata_auth", None)
        with session.get(
            url,
            stream=True,
            timeout=REQUEST_TIMEOUT,
            auth=auth,
        ) as response:
            if response.status_code == 401:
                return ("failed", filename, "401 Unauthorized - Check Earthdata credentials")
            response.raise_for_status()

            with open(temporary_path, "wb") as f:
                for chunk in response.iter_content(
                    chunk_size=DOWNLOAD_CHUNK_SIZE
                ):
                    if chunk:
                        f.write(chunk)

        # Only expose the completed file after successful download.
        temporary_path.replace(output_path)
        return (
            "success",
            filename,
            "downloaded",
        )

    except Exception as exc:
        try:
            if temporary_path.exists():
                temporary_path.unlink()
        except Exception:
            pass
        return (
            "failed",
            filename,
            str(exc),
        )


# ---------------------------------------------------------------------
# MANIFEST
# ---------------------------------------------------------------------
def write_manifest(rows: list[dict]) -> None:
    """
    Write download manifest.
    """
    DOWNLOAD_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    fields = [
        "filename",
        "url",
        "status",
        "message",
        "size_bytes",
    ]

    with open(
        MANIFEST_PATH,
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


# ---------------------------------------------------------------------
# DOWNLOAD ALL
# ---------------------------------------------------------------------
def download_all(
    urls: list[str],
) -> None:
    DOWNLOAD_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    results: list[dict] = []
    downloaded = 0
    skipped = 0
    failed = 0

    print()
    print("=" * 72)
    print("DOWNLOADING")
    print("=" * 72)
    print(f"Workers : {MAX_WORKERS}")
    print(f"Files   : {len(urls):,}")
    print()

    with tqdm(
        total=len(urls),
        desc="Downloads",
        unit="file",
    ) as progress:
        with ThreadPoolExecutor(
            max_workers=MAX_WORKERS
        ) as executor:
            future_to_url = {
                executor.submit(
                    download_file,
                    url,
                ): url
                for url in urls
            }

            for future in as_completed(
                future_to_url
            ):
                url = future_to_url[future]
                try:
                    status, filename, message = future.result()
                except Exception as exc:
                    status = "failed"
                    filename = filename_from_url(url)
                    message = str(exc)

                output_path = DOWNLOAD_DIR / filename
                size_bytes = (
                    output_path.stat().st_size
                    if output_path.exists()
                    else 0
                )

                results.append(
                    {
                        "filename": filename,
                        "url": url,
                        "status": status,
                        "message": message,
                        "size_bytes": size_bytes,
                    }
                )

                if status == "success":
                    downloaded += 1
                elif status == "skipped":
                    skipped += 1
                else:
                    failed += 1
                    print(
                        f"\nFAILED: {filename}\n"
                        f"        {message}"
                    )

                progress.update(1)

    write_manifest(results)

    print()
    print("=" * 72)
    print("DOWNLOAD SUMMARY")
    print("=" * 72)
    print(f"Downloaded : {downloaded:,}")
    print(f"Skipped    : {skipped:,}")
    print(f"Failed     : {failed:,}")
    print(f"Manifest   : {MANIFEST_PATH}")
    print(f"Directory  : {DOWNLOAD_DIR}")
    print("=" * 72)


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Download MODIS MAIAC MCD19A2 V061.")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry-run query without downloading files.")
    parser.add_argument("--download", action="store_true", help="Proceed with downloading files after the query.")
    args = parser.parse_args()

    # Check for authentication
    if args.download:
        if not os.environ.get("EARTHDATA_USERNAME") and not os.environ.get("EARTHDATA_PASSWORD"):
            if not Path(Path.home() / ".netrc").exists() and not Path(Path.home() / "_netrc").exists():
                print("WARNING: Earthdata authentication not found in environment variables (EARTHDATA_USERNAME, EARTHDATA_PASSWORD) or ~/.netrc file.")
                print("Downloads will likely fail with 401 Unauthorized.")
                print("Please configure Earthdata Login credentials before running with --download.")

    DOWNLOAD_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    session = create_session()
    urls, granule_ids, temporal_ranges = collect_granules(session)

    if not urls:
        print()
        print("No granules found.")
        return

    print()
    print("=" * 72)
    print("DRY RUN REPORT")
    print("=" * 72)
    print(f"Number of matching granules: {len(granule_ids)}")
    if granule_ids:
        print(f"First few granule IDs:")
        for gid in granule_ids[:3]:
            print(f"  {gid}")
        print(f"Last few granule IDs:")
        for gid in granule_ids[-3:]:
            print(f"  {gid}")

    if temporal_ranges:
        print(f"Date range represented:")
        print(f"  Earliest: {min(t[0] for t in temporal_ranges)}")
        print(f"  Latest:   {max(t[1] for t in temporal_ranges)}")

    print(f"Approximate number of files to download: {len(urls)}")
    print(f"Bounding-box filter applied: {BBOX}")
    print("=" * 72)

    if args.dry_run or not args.download:
        print("\nDry-run complete. Run with --download to acquire files.")
        return

    download_all(urls)

    print()
    print("SUCCESS: MCD19A2 acquisition finished.")
    print()
    print("IMPORTANT:")
    print("The script only downloads raw granules.")
    print("It does NOT extract AOD.")
    print("It does NOT modify existing VayuNet datasets.")


if __name__ == "__main__":
    main()
