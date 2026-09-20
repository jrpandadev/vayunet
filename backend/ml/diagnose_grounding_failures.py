import json
from pathlib import Path
import re

def analyze_failures():
    backend_root = Path(__file__).resolve().parent.parent
    pilot_dir = backend_root / "reports/investigation/gemini_pilot"
    bundle_dir = backend_root / "data/processed/evidence_bundles"

    files = list(pilot_dir.glob("*.json"))

    matrix = []

    EXTENDED_CAUSAL_PHRASES = [
        "proves", "proved", "confirms", "established causality",
        "direct proof", "solely responsible", "is the reason",
        "directly led to"
    ]

    for f in files:
        bundle_id = f.name.replace("PILOT_", "").replace(".json", "")
        with open(f, "r", encoding="utf-8") as file:
            pilot_data = json.load(file)

        bundle_path = bundle_dir / f"{bundle_id}.json"
        with open(bundle_path, "r", encoding="utf-8") as file:
            bundle_data = json.load(file)

        report_data = pilot_data.get("investigation_report", {})

        # Re-run diagnostic validation
        narrative = report_data.get("synthesis_narrative", "").lower()
        supporting_evidence = []
        for eval in report_data.get("evaluated_hypotheses", []):
            supporting_evidence.extend(eval.get("supporting_evidence", []))
            supporting_evidence.extend(eval.get("contrasting_evidence", []))

        all_text_lower = narrative + " " + " ".join(supporting_evidence).lower()

        firms_data = bundle_data.get("firms_viirs")
        firms_missing = firms_data is None or len(firms_data) == 0

        failures = []
        if firms_missing:
            for term in ["firms", "viirs", "active fire"]:
                if term in all_text_lower:
                    # extract context
                    idx = all_text_lower.find(term)
                    context = all_text_lower[max(0, idx-50):min(len(all_text_lower), idx+50)]
                    failures.append({
                        "type": "HALLUCINATED_FIRMS_EVENT",
                        "claim": f"'{term}' found in context: '{context}'",
                        "evidence": "firms_viirs is missing or empty in bundle",
                        "validator_rule": "2. Unsupported source claims (FIRMS)"
                    })
                    break

        for phrase in EXTENDED_CAUSAL_PHRASES:
            if phrase in all_text_lower:
                idx = all_text_lower.find(phrase)
                context = all_text_lower[max(0, idx-50):min(len(all_text_lower), idx+50)]
                failures.append({
                    "type": "CAUSAL_OVERREACH",
                    "claim": f"'{phrase}' found in context: '{context}'",
                    "evidence": "Causal phrase found.",
                    "validator_rule": "3. Causal Overreach"
                })

        found_numbers = re.findall(r'\b\d+(?:\.\d+)?\b', all_text_lower)
        found_floats = [float(n) for n in found_numbers if float(n) > 10.0]

        def extract_bundle_numbers(d, acc):
            if isinstance(d, dict):
                for v in d.values():
                    extract_bundle_numbers(v, acc)
            elif isinstance(d, list):
                for v in d:
                    extract_bundle_numbers(v, acc)
            elif isinstance(d, (int, float)):
                if d > 10.0:
                    acc.append(float(d))

        bundle_numbers = []
        extract_bundle_numbers(bundle_data, bundle_numbers)

        for fn in set(found_floats):
            is_grounded = any(abs(fn - bn) < 1.0 for bn in bundle_numbers)
            if not is_grounded:
                if 2000 <= fn <= 2100:
                    continue
                if fn in [24.0, 48.0, 72.0, 12.0]:
                    continue
                failures.append({
                    "type": "UNSUPPORTED_NUMERIC_VALUE",
                    "claim": str(fn),
                    "evidence": "Number not found in bundle values.",
                    "validator_rule": "4. Numerical Claims Validation"
                })

        matrix.append({
            "bundle": bundle_id,
            "failures": failures
        })

    for m in matrix:
        print(f"\nBundle: {m['bundle']}")
        for fail in m["failures"]:
            print(f"  - {fail['type']}: Claim={fail['claim']} | Evidence={fail['evidence']} | Rule={fail['validator_rule']}")

if __name__ == "__main__":
    analyze_failures()
