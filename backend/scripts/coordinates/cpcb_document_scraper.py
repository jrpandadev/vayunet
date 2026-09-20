import csv
import json
import os
import re
import requests
import io
import time
from pathlib import Path
from googlesearch import search
import PyPDF2

def scrape_cpcb_documents():
    metadata_path = Path("data/processed/delhi_ncr/ncr_station_metadata.csv")
    output_path = Path("scratch/cpcb_scraped_coords.json")

    with open(metadata_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        stations = list(reader)

    results = {}

    # Very basic regex for coordinates
    lat_lon_pattern = re.compile(r'(\d{2}\.\d{3,6})[^\d]*(\d{2}\.\d{3,6})')

    for st in stations:
        # Check only unverified
        # The user wants all 45 stations checked, but let's check only UNVERIFIED
        name = st['station_name'].replace('_', ' ')
        query = f'"{name}" "latitude" "longitude" site:cpcb.nic.in filetype:pdf'
        print(f"Searching for: {name}...")

        found = False
        try:
            for url in search(query, num_results=2, sleep_interval=2):
                if not url.endswith('.pdf'):
                    continue

                print(f"  Downloading {url}...")
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    reader_pdf = PyPDF2.PdfReader(io.BytesIO(resp.content))
                    for i, page in enumerate(reader_pdf.pages):
                        text = page.extract_text()
                        if text and name.lower() in text.lower():
                            matches = lat_lon_pattern.findall(text)
                            if matches:
                                lat, lon = matches[0]
                                results[st['station_id']] = {
                                    'latitude': lat,
                                    'longitude': lon,
                                    'source_url': url,
                                    'source_document': url.split('/')[-1],
                                    'source_page': i+1
                                }
                                print(f"    Found coords: {lat}, {lon}")
                                found = True
                                break
                if found:
                    break
        except Exception as e:
            print(f"  Error: {e}")

        time.sleep(2)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4)

    print(f"Scraped {len(results)} stations.")

if __name__ == '__main__':
    scrape_cpcb_documents()
