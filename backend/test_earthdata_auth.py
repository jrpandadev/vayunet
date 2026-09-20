import os
import requests
from urllib.parse import urlparse
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()
username = os.environ.get("EARTHDATA_USERNAME")
password = os.environ.get("EARTHDATA_PASSWORD")

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

def main():
    if not username or not password:
        print("ERROR: EARTHDATA_USERNAME and EARTHDATA_PASSWORD missing in environment.")
        return

    session = EarthdataSession(username, password)

    url = "https://cmr.earthdata.nasa.gov/search/granules.umm_json"
    params = {
        "short_name": "MCD19A2",
        "version": "061",
        "page_size": 1,
        "temporal": "2022-01-01T00:00:00Z,2026-08-31T23:59:59Z",
        "bounding_box": "76.0,27.0,78.5,29.5",
    }
    headers = {"Accept": "application/json"}

    print("Querying CMR...")
    response = session.get(url, params=params, headers=headers)
    response.raise_for_status()
    data = response.json()
    items = data.get("items", [])
    if not items:
        print("No items found.")
        return

    item = items[0]
    download_url = None
    umm = item.get("umm", {})
    for related_url in umm.get("RelatedUrls", []):
        if related_url.get("Type") == "GET DATA":
            u = related_url.get("URL")
            if u:
                download_url = u
                break

    if not download_url:
        print("No GET DATA URL found.")
        return

    print(f"Testing download for URL: {download_url}")

    filename = os.path.basename(urlparse(download_url).path)
    out_dir = Path("data/raw/satellite/modis_maiac")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename

    try:
        resp = session.get(download_url, stream=True, auth=session.earthdata_auth)
        if resp.status_code != 200:
            print(f"FAILED: HTTP {resp.status_code}")
            print(f"Host: {urlparse(resp.url).hostname}")
            return

        with open(out_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024*1024):
                if chunk:
                    f.write(chunk)

        size = out_path.stat().st_size
        print(f"Downloaded {size} bytes.")

        # Verify
        if size == 0:
            print("ERROR: Zero-byte file.")
            return

        with open(out_path, "rb") as f:
            header = f.read(500)
            if b"<!DOCTYPE html>" in header.lower() or b"<html" in header.lower():
                print("ERROR: Downloaded an HTML file (likely login page). Authentication failed.")
                return
            if not filename.startswith("MCD19A2") or "061" not in filename:
                 print("ERROR: Filename is not MCD19A2 V061.")
                 return

        print("NASA Earthdata single-file authentication test: PASS")

    finally:
        if out_path.exists():
            out_path.unlink()
            print("Cleaned up test file.")

if __name__ == "__main__":
    main()
