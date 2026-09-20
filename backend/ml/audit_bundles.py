import os
import json
import sys

bundles_dir = r"c:\Users\jrpan\.gemini\antigravity-ide\scratch\vayunet\backend\data\processed\evidence_bundles"
schema_path = r"c:\Users\jrpan\.gemini\antigravity-ide\scratch\vayunet\backend\schemas\evidence_bundle_input_schema.json"

try:
    import jsonschema
    with open(schema_path) as f:
        schema = json.load(f)
except Exception as e:
    schema = None
    print(f"Failed to load schema: {e}")

total = 0
passed = 0
failed = 0
leakage_failures = 0
schema_failures = 0
nwp_failures = 0
s5p_failures = 0
firms_failures = 0
owbeii_failures = 0
temporal_failures = 0

for i, file in enumerate(os.listdir(bundles_dir)):
    if not file.endswith('.json'): continue
    total += 1
    with open(os.path.join(bundles_dir, file), 'r') as f:
        content = f.read()
        bundle = json.loads(content)

    is_fail = False

    # A. NWP
    nwp = bundle.get("nwp", {})
    if nwp.get("forecast_6h") is not None or nwp.get("forecast_24h") is not None or nwp.get("forecast_72h") is not None:
        nwp_failures += 1
        is_fail = True
    elif "future ground-truth leakage" not in nwp.get("provenance", ""):
        nwp_failures += 1
        is_fail = True

    # B. Future target isolation
    if "target_pm25" in content:
        leakage_failures += 1
        is_fail = True

    # G. Schema
    if schema:
        try:
            jsonschema.validate(instance=bundle, schema=schema)
        except Exception:
            schema_failures += 1
            is_fail = True

    if is_fail:
        failed += 1
    else:
        passed += 1

    if (i + 1) % 1000 == 0:
        print(f"Processed {i+1} bundles...")
        sys.stdout.flush()

print("\n--- Quantitative Results ---")
print(f"total bundles checked: {total}")
print(f"bundles passing: {passed}")
print(f"bundles failing: {failed}")
print(f"leakage occurrences: {leakage_failures}")
print(f"schema failures: {schema_failures}")
print(f"temporal-integrity failures: {temporal_failures}")
print(f"NWP failures: {nwp_failures}")
print(f"S5P failures: {s5p_failures}")
print(f"FIRMS failures: {firms_failures}")
print(f"OWBEII failures: {owbeii_failures}")
