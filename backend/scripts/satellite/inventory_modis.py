import os
import re
import datetime
from pathlib import Path
import pandas as pd

RAW_MAIAC_DIR = Path("backend/data/raw/satellite/modis_maiac")
OUTPUT_CSV = RAW_MAIAC_DIR / "inventory.csv"

def parse_granule_date(filename):
    match = re.search(r"MCD19A2\.A(\d{4})(\d{3})\.h24v06", filename)
    if not match:
        return None
    year = int(match.group(1))
    doy = int(match.group(2))
    dt = datetime.datetime(year, 1, 1) + datetime.timedelta(days=doy - 1)
    return dt.strftime("%Y-%m-%d")

def generate_inventory():
    import netCDF4

    hdf_files = sorted(list(RAW_MAIAC_DIR.glob("*.hdf")))
    print(f"Found {len(hdf_files)} HDF files.")

    records = []
    seen = set()

    for idx, fpath in enumerate(hdf_files):
        date_str = parse_granule_date(fpath.name)

        is_dup = fpath.name in seen
        seen.add(fpath.name)

        is_valid = fpath.stat().st_size > 10240

        orbit_times = []
        if is_valid:
            try:
                ds = netCDF4.Dataset(str(fpath), mode="r")
                if "Orbit_time_stamp" in ds.ncattrs():
                    attr = ds.getncattr("Orbit_time_stamp")
                    if isinstance(attr, str):
                        orbit_times = [x.strip() for x in attr.split() if x.strip()]
                ds.close()
            except Exception as e:
                is_valid = False

        # We store the orbit times as a comma-separated string for the inventory
        orbit_times_str = ",".join(orbit_times)

        records.append({
            "filename": fpath.name,
            "acquisition_date": date_str,
            "orbit_time_stamps": orbit_times_str,
            "tile": "h24v06",
            "product": "MCD19A2",
            "is_valid": is_valid,
            "is_duplicate": is_dup,
            "size_bytes": fpath.stat().st_size
        })

        if (idx + 1) % 100 == 0:
            print(f"Processed {idx + 1}/{len(hdf_files)} granules...")

    df = pd.DataFrame(records)
    df.to_csv(OUTPUT_CSV, index=False)

    print(f"Total Granules: {len(df)}")
    print(f"Valid Granules (>10KB): {df['is_valid'].sum()}")
    print(f"Duplicate Filenames: {df['is_duplicate'].sum()}")
    print(f"Min Date: {df['acquisition_date'].min()}")
    print(f"Max Date: {df['acquisition_date'].max()}")
    print(f"Inventory saved to {OUTPUT_CSV}")

if __name__ == "__main__":
    generate_inventory()
