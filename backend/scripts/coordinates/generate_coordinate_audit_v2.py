import csv
import json
from pathlib import Path

def generate_audit_v2():
    scraped_file = Path("scratch/cpcb_scraped_coords.json")
    metadata_file = Path("data/processed/delhi_ncr/ncr_station_metadata.csv")
    output_md = Path("reports/coordinates/ncr_coordinate_audit_v2.md")

    scraped_data = {}
    if scraped_file.exists():
        with open(scraped_file, 'r', encoding='utf-8') as f:
            scraped_data = json.load(f)

    with open(metadata_file, 'r', encoding='utf-8') as f:
        reader = list(csv.DictReader(f))

    verified_count = 0
    unverified_count = 0

    report_lines = [
        "# NCR Station Coordinate Audit Report V2",
        "",
        "## Summary",
        f"- **Expected Stations**: {len(reader)}",
        "## Detailed Station Status",
        "",
        "| Station ID | Name | City | Status | Source / Notes | URL |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |"
    ]

    for row in reader:
        st_id = row['station_id']
        if st_id in scraped_data:
            data = scraped_data[st_id]
            row['latitude'] = data['latitude']
            row['longitude'] = data['longitude']
            status = "VERIFIED_OFFICIAL"
            notes = f"Doc: {data.get('source_document', '')} (Page {data.get('source_page', '')})"
            url = data.get('source_url', '')
            verified_count += 1
        else:
            status = "UNVERIFIED"
            notes = "No official document found."
            url = ""
            unverified_count += 1

        report_lines.append(f"| {st_id} | {row['station_name']} | {row['city']} | {status} | {notes} | {url} |")

    report_lines.insert(4, f"- **Verified (Official)**: {verified_count}")
    report_lines.insert(5, f"- **Unverified**: {unverified_count}")

    # Save CSV
    if verified_count > 0:
        fieldnames = reader[0].keys()
        with open(metadata_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(reader)

    # Save MD
    output_md.parent.mkdir(parents=True, exist_ok=True)
    with open(output_md, 'w', encoding='utf-8') as f:
        f.write("\n".join(report_lines))

    print(f"Generated Audit V2. Verified: {verified_count}, Unverified: {unverified_count}")

if __name__ == '__main__':
    generate_audit_v2()
