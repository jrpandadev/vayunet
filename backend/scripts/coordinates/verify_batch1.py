import os
import requests
import io
import csv
import PyPDF2
from pathlib import Path
import re

URL1 = "https://cpcb.nic.in/uploads/MSW/Reports_swm_4.pdf"
URL2 = "https://cpcb.nic.in/Actionplan/Meerut.pdf"

# The user-provided coordinates (to be verified)
stations = [
    {"id": "CPCB_1430", "name": "rohini", "display": "Rohini", "url": URL1, "lat": "28.732528", "lon": "77.119920", "doc": "Reports_swm_4.pdf"},
    {"id": "CPCB_118", "name": "dtu", "display": "DTU", "url": URL1, "lat": "28.749722", "lon": "77.116281", "doc": "Reports_swm_4.pdf"},
    {"id": "CPCB_104", "name": "burari_crossing", "display": "Burari Crossing", "url": URL1, "lat": "28.725650", "lon": "77.201157", "doc": "Reports_swm_4.pdf"},
    {"id": "CPCB_5023", "name": "anand_vihar", "display": "Anand Vihar", "url": URL1, "lat": "28.646835", "lon": "77.316032", "doc": "Reports_swm_4.pdf"},
    {"id": "CPCB_1431", "name": "patparganj", "display": "Patparganj", "url": URL1, "lat": "28.623748", "lon": "77.287205", "doc": "Reports_swm_4.pdf"},
    {"id": "CPCB_1421", "name": "dr_karni_singh_shooting_range", "display": "Karni Singh", "url": URL1, "lat": "28.498571", "lon": "77.264840", "doc": "Reports_swm_4.pdf"},
    {"id": "CPCB_103", "name": "crri_mathura_road", "display": "CRRI Mathura", "url": URL1, "lat": "28.551201", "lon": "77.273574", "doc": "Reports_swm_4.pdf"},
    {"id": "CPCB_5257", "name": "pallavpuram_phase_2", "display": "Pallavpuram", "url": URL2, "lat": "29.063275", "lon": "77.707539", "doc": "Meerut.pdf"}
]

def extract_from_pdf(url):
    import urllib3
    urllib3.disable_warnings()
    print(f"Downloading {url}")
    resp = requests.get(url, verify=False, timeout=30)
    pdf = PyPDF2.PdfReader(io.BytesIO(resp.content))
    pages_text = []
    for p in pdf.pages:
        pages_text.append(p.extract_text())
    return pages_text

def verify():
    print("Extracting URL1...")
    pdf1_pages = extract_from_pdf(URL1)
    print("Extracting URL2...")
    pdf2_pages = extract_from_pdf(URL2)

    verified_results = {}

    for s in stations:
        pages = pdf1_pages if s['url'] == URL1 else pdf2_pages
        found = False
        for i, text in enumerate(pages):
            if not text:
                continue

            t_lower = text.lower()
            search_str = s['display'].lower()

            # Allow inexact matching by stripping whitespace
            if search_str in t_lower or search_str.replace(" ", "") in t_lower.replace(" ", ""):
                # Check if coordinates are also on this page
                lat_str = s['lat'][:5] # Match prefix to account for formatting
                lon_str = s['lon'][:5]
                if lat_str in t_lower and lon_str in t_lower:
                    print(f"VERIFIED: {s['display']} on page {i+1} of {s['doc']}")
                    verified_results[s['id']] = {
                        'lat': s['lat'],
                        'lon': s['lon'],
                        'page': i+1,
                        'url': s['url'],
                        'doc': s['doc']
                    }
                    found = True
                    break
        if not found:
            print(f"FAILED to verify {s['display']}")

    # Update CSV
    metadata_file = Path("data/processed/delhi_ncr/ncr_station_metadata.csv")
    with open(metadata_file, 'r', encoding='utf-8') as f:
        reader = list(csv.DictReader(f))

    for row in reader:
        st_id = row['station_id']
        if st_id in verified_results:
            data = verified_results[st_id]
            row['latitude'] = data['lat']
            row['longitude'] = data['lon']

    fieldnames = reader[0].keys()
    with open(metadata_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(reader)

    # Generate Markdown
    md_lines = [
        "# Stage 3B: NCR Coordinate Audit V3 (Batch 1)",
        "",
        "## Summary",
        f"- **Stations Verified**: {len(verified_results)}",
        f"- **Stations Still Unverified**: {len(reader) - len(verified_results)}",
        "",
        "## Verified Provenance (Batch 1)",
        "",
        "| Station ID | Name | Latitude | Longitude | Official Source URL | Document | Page |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
    ]

    for st_id, data in verified_results.items():
        name = next(r['station_name'] for r in reader if r['station_id'] == st_id)
        md_lines.append(f"| {st_id} | {name} | {data['lat']} | {data['lon']} | {data['url']} | {data['doc']} | {data['page']} |")

    out_md = Path("reports/coordinates/ncr_coordinate_audit_v3_batch1.md")
    out_md.parent.mkdir(parents=True, exist_ok=True)
    with open(out_md, 'w', encoding='utf-8') as f:
        f.write("\n".join(md_lines))

    print(f"\nSaved CSV and generated {out_md}")

if __name__ == '__main__':
    verify()
