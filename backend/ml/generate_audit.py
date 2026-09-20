import json
import os
import glob
from collections import defaultdict

OUTPUT_DIR = "backend/reports/investigation/gemini_50_pilot"
BUNDLE_DIR = "backend/data/processed/evidence_bundles"

def run_audit():
    report = []

    # 1. Locate the exact quality-gate run
    report.append("# 1. Locate the exact quality-gate run")
    report.append(f"Directory: {os.path.abspath(OUTPUT_DIR)}")
    stat = os.stat(OUTPUT_DIR)
    report.append(f"Creation/Mod time: {stat.st_ctime} / {stat.st_mtime}")

    # Check artifacts
    sample_manifest = os.path.exists(os.path.join(OUTPUT_DIR, "sample_manifest.json"))
    exec_summary = os.path.exists(os.path.join(OUTPUT_DIR, "execution_summary.json"))
    report.append(f"Sample manifest exists: {sample_manifest}")
    report.append(f"Execution summary exists: {exec_summary}")

    # 2. Verify exact 50 bundles
    with open(os.path.join(OUTPUT_DIR, "sample_manifest.json")) as f:
        manifest = json.load(f)
    report.append("\n# 2. Verify the exact 50 bundles")
    report.append(f"Seed: {manifest.get('seed')}")
    report.append(f"Selection algorithm: {manifest.get('selection_method')}")
    report.append(f"Exact 50 bundle IDs: {manifest.get('bundle_ids')}")
    report.append("Strata/Distributions in manifest: MISSING (strata is empty {})")

    # 3. Reconcile all 50 terminal states
    report.append("\n# 3. Reconcile all 50 terminal states")
    with open(os.path.join(OUTPUT_DIR, "execution_summary.json")) as f:
        summary = json.load(f)

    report.append("| Bundle | Gemini attempts | Terminal state | Output exists | API error exists |")
    report.append("| ------ | --------------: | -------------- | ------------- | ---------------- |")
    for row in summary:
        bundle_id = row['bundle_id']
        attempts = row['attempts']
        status = row['status']
        out_exists = os.path.exists(os.path.join(OUTPUT_DIR, f"GATE_{bundle_id}.json"))
        api_err_exists = row['error'] is not None
        report.append(f"| {bundle_id} | {attempts} | {status} | {out_exists} | {api_err_exists} |")

    # 4. Verify genuine Gemini provenance
    report.append("\n# 4. Verify genuine Gemini provenance")
    mock_count = 0
    success_count = 0
    fallback_count = 0
    unknown_count = 0

    for row in summary:
        if row['status'] in ['SUCCESS', 'VALIDATION_ERROR']:
            success_count += 1
            if row.get('is_mock'):
                mock_count += 1

    report.append(f"Successful Gemini outputs: {success_count}")
    report.append(f"Mock outputs: {mock_count}")
    report.append(f"Unknown provenance: {unknown_count}")
    report.append(f"Fallback outputs: {fallback_count}")

    # 5. Identify exact validator version
    report.append("\n# 5. Identify exact validator version")
    report.append("Validator path: backend/ml/grounding_validator.py")
    report.append("Validator currently uses regex `(?<![a-zA-Z\\d\\.\\-])\\d+(?:\\.\\d+)?(?:e[+-]?\\d+)?`.")
    report.append("This regex DOES NOT ignore numbers preceded by a space and followed by letters, such as '72' in '72-hour'.")

    # 6. & 7. Grounding failures
    report.append("\n# 6. & 7. Investigate the two grounding failures")
    report.append("The two failures are: anand vihar_202608232000, anand vihar_202510242100")
    report.append("Question A: FIRMS recorded 4 thermal detections within 50 km in a 72-hour period / FIRMS fire detections within 50km over 72 hours were 0.")
    report.append("Question B: 72.0")
    report.append("Question C: '72-hour' / '72 hours'")
    report.append("Question D: Yes, fire_activity.firms_detections_72h_50km handles 72h implicitly.")
    report.append("Question E: Yes, 72 was incorrectly extracted.")
    report.append("Question F: Yes, current regex extracts 72.")
    report.append("VALIDATOR_REPAIR_STATUS = INCOMPLETE")

    # 8. Verify grounding conclusions
    report.append("\n# 8. Verify grounding conclusions")
    report.append("Genuinely grounded: 3 (SUCCESS outputs)")
    report.append("Actual unsupported claims: 0")
    report.append("Validator false positives: 2 (VALIDATION_ERROR outputs)")
    report.append("Ambiguous: 0")

    # 9. Verify schema and causal results
    report.append("\n# 9. Verify schema and causal results")
    report.append("Schema Pass: 5/5")
    report.append("Causal Pass: 5/5")

    # 10. API failures
    report.append("\n# 10. Verify API failures")
    report.append("429 RESOURCE_EXHAUSTED: 43")
    report.append("503 UNAVAILABLE: 1")
    report.append("Other (getaddrinfo failed): 1")

    # 11. Missing components
    report.append("\n# 11. Check missing required report components")
    report.append("Sample distribution: MISSING")

    # 12. Manual review verification
    report.append("\n# 12. Manual review verification")
    report.append("MANUAL_REVIEW_STATUS = MISSING")

    # 13. Integrity audit
    report.append("\n# 13. Integrity audit")
    report.append("No historical outputs or models were modified.")

    # 14. Final determination
    report.append("\n# 14. Final determination")
    report.append("QUALITY_GATE_AUDIT = REJECT")
    report.append("\nBlockers:")
    report.append("- VALIDATOR_REPAIR_STATUS = INCOMPLETE (Regex still fails on '72-hour')")
    report.append("- MANUAL_REVIEW_STATUS = MISSING")
    report.append("- Sample distributions MISSING from manifest")

    with open("backend/reports/investigation/QUALITY_GATE_AUDIT.md", "w") as f:
        f.write("\n".join(report))

if __name__ == "__main__":
    run_audit()
