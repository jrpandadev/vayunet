import re
from typing import Dict, List, Any

# Expanded causal phrases to look for in the entire report
EXTENDED_CAUSAL_PHRASES = [
    "proves", "proved", "confirms", "established causality",
    "direct proof", "solely responsible", "is the reason",
    "directly led to"
]

class GroundingValidator:
    """
    Validates Investigator outputs against their source Evidence Bundle.
    Returns (is_valid, list_of_errors).
    """

    @classmethod
    def validate(cls, report_data: Dict[str, Any], bundle_data: Dict[str, Any]) -> tuple[bool, List[str]]:
        errors = []

        # 1. Missing-value hallucination (NWP)
        nwp_data = bundle_data.get("nwp", {})
        nwp_missing = not any([
            nwp_data.get("forecast_6h"),
            nwp_data.get("forecast_24h"),
            nwp_data.get("forecast_72h")
        ])

        narrative = report_data.get("synthesis_narrative", "").lower()
        supporting_evidence = []
        for eval in report_data.get("evaluated_hypotheses", []):
            supporting_evidence.extend(eval.get("supporting_evidence", []))
            supporting_evidence.extend(eval.get("contrasting_evidence", []))

        all_text = narrative + " " + " ".join(supporting_evidence).lower()

        if nwp_missing:
            if "forecast" in all_text and ("pm2.5" in all_text or "pm25" in all_text) and bool(re.search(r'\d+', all_text)):
                # Be careful not to block generic talk of missing forecast, but block numerical claims
                if "forecast" in all_text and any(word in all_text for word in ["predicted", "expected", "modeled"]):
                    errors.append("Hallucination: NWP forecast mentioned numerically despite being null in bundle.")

        # 2. Unsupported source claims (FIRMS)
        fire_activity = bundle_data.get("fire_activity")
        firms_missing = True
        if fire_activity and isinstance(fire_activity, dict):
            # If it has the required key, it's not missing.
            if "firms_detections_72h_50km" in fire_activity:
                firms_missing = False

        if firms_missing:
            if "firms" in all_text or "viirs" in all_text or "active fire" in all_text:
                errors.append("Hallucination: FIRMS/VIIRS active fires mentioned despite being null/empty in bundle.")

        # 3. Causal Overreach
        for phrase in EXTENDED_CAUSAL_PHRASES:
            if phrase in all_text:
                errors.append(f"Causal Overreach: Found forbidden causal phrase '{phrase}'.")

        # 4. Context-Aware Numerical Claims Validation
        # Extract numbers from bundle (flatten simple dicts)
        bundle_numbers = []
        def extract_bundle_numbers(d):
            if isinstance(d, dict):
                for v in d.values():
                    extract_bundle_numbers(v)
            elif isinstance(d, list):
                for v in d:
                    extract_bundle_numbers(v)
            elif isinstance(d, (int, float)):
                bundle_numbers.append(float(d))

        extract_bundle_numbers(bundle_data)

        # Extract numbers with context from text
        # Regex to extract numbers not preceded by letters/digits/punctuation (avoids PM2.5, NO2), supports scientific notation
        number_matches = list(re.finditer(r'(?<![a-zA-Z\d\.\-])\-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?', all_text))

        for match in number_matches:
            val_str = match.group()
            val = float(val_str)

            start_idx = match.start()
            end_idx = match.end()

            context_before = all_text[max(0, start_idx-30):start_idx].lower()
            context_after = all_text[end_idx:min(len(all_text), end_idx+30)].lower()

            # Contextual Skip 1: Dates and Times
            # If it's part of a time (e.g. 20:00, 13:00)
            if re.search(r'^\s*:\s*\d\d', context_after) or re.search(r'\d\d\s*:\s*$', context_before):
                continue
            # If it's part of a date (e.g. 2026-08-23 or 2026/08/23)
            if re.search(r'^\s*[-\/]\s*\d\d', context_after) or re.search(r'\d\d\s*[-\/]\s*$', context_before):
                continue
            # If preceded by a month name
            if any(month in context_before[-15:] for month in ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december", "jan ", "feb ", "mar ", "apr ", "jun ", "jul ", "aug ", "sep ", "oct ", "nov ", "dec "]):
                continue
            if 2000 <= val <= 2100:  # Ignore years
                continue

            # Contextual Skip 2: Window/Duration and Distance Qualifiers
            # Skips numbers followed by -hour, hours, h, km which are used for contextual windows,
            # while leaving other measurements (like m/s, degrees, ug/m3) intact for validation.
            if re.search(r'^(?:-hour|\s+hours?|\s*h\b|\s*km\b)', context_after):
                continue

            # If we reached here, it's considered an independent measurement claim.
            is_grounded = any(abs(val - bn) < 1.0 for bn in bundle_numbers)
            if not is_grounded:
                errors.append(f"Unsupported numerical claim: {val} not found in bundle.")

        return len(errors) == 0, errors
