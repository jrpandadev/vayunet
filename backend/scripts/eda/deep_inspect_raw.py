import pandas as pd
from pathlib import Path
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
import json

BASE_DIR = Path(__file__).resolve().parent.parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"

def inspect_file(filename, skiprows, delim=r'\s+'):
    path = RAW_DIR / filename
    print(f"\n{'='*50}\nInspecting {filename}\n{'='*50}")

    # print raw header
    with open(path, "r", encoding="utf-16le" if "HCL" in filename else "utf-8", errors="replace") as f:
        head = [next(f).strip() for _ in range(10)]
        print("HEADER START:")
        for h in head: print(h.encode("utf-8", errors="replace").decode("utf-8"))
        print("HEADER END")

    try:
        if "HCL" in filename:
            df = pd.read_csv(path, sep='\t', skiprows=skiprows, encoding="utf-16le")
        else:
            df = pd.read_csv(path, sep='\t', skiprows=skiprows)

        print(f"\nRows: {len(df)}")
        print(f"Columns: {len(df.columns)}")
        print(f"Column Names: {list(df.columns)}")
        print("\nData Types:")
        print(df.dtypes)
        print("\nMissing Values:")
        print(df.isna().sum())

        print("\nValue Ranges:")
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                print(f"{col}: {df[col].min()} to {df[col].max()}")

        print("\nDuplicate Records:")
        print(df.duplicated().sum())

        print("\nFirst 3 rows:")
        print(df.head(3))

        print("\nLast 3 rows:")
        print(df.tail(3))

    except Exception as e:
        print(f"Failed to parse pandas dataframe: {e}")

if __name__ == "__main__":
    inspect_file("HCL.txt", skiprows=9)
    inspect_file("Wasteburned.txt", skiprows=0)
