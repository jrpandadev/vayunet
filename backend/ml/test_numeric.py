import re

def validate_numeric_claims(all_text, bundle_data):
    errors = []

    # 1. Flatten all numeric values from bundle
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

    # 2. Extract numbers with context
    number_matches = list(re.finditer(r'(?<![a-zA-Z\d\.\-])\-?\d+(?:\.\d+)?', all_text))

    for match in number_matches:
        val_str = match.group()
        val = float(val_str)

        start_idx = match.start()
        end_idx = match.end()

        context_before = all_text[max(0, start_idx-30):start_idx].lower()
        context_after = all_text[end_idx:min(len(all_text), end_idx+30)].lower()

        # Date/Time checks
        if re.search(r'^\s*:\s*\d\d', context_after) or re.search(r'\d\d\s*:\s*$', context_before):
            continue
        if any(month in context_before[-15:] for month in ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december", "jan ", "feb ", "mar ", "apr ", "jun ", "jul ", "aug ", "sep ", "oct ", "nov ", "dec "]):
            continue

        # Units/Contextual limits
        if re.search(r'^\s*(km|hours|h|m|kg|km2|km\^2)\b', context_after):
            continue

        if 2000 <= val <= 2100:
            continue

        is_grounded = any(abs(val - bn) < 1.0 for bn in bundle_numbers)
        if not is_grounded:
            errors.append(f"Unsupported numerical claim: {val} not found in bundle.")

    return errors

all_text = "pm2.5 peaked at 287.6ug/m3 on january 25 at 20:00 with 3 firms detections within 50km."
bundle = {"peak_pm25": 143.2, "fire_activity": {"firms_detections_72h_50km": 3}}
print(validate_numeric_claims(all_text, bundle))

all_text2 = "pm2.5 peaked at 143.2ug/m3 on jan 25 at 20:00 with 3 firms detections within 50km."
print(validate_numeric_claims(all_text2, bundle))
