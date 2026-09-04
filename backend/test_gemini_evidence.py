import json
from services.gemini_evidence import extract_evidence

test_cases = [
    {
        "name": "Case 1: Industrial Smoke",
        "desc": "Heavy black smoke rising from factory chimney near Okhla Phase 2.",
        "image": "test_images/smoke_industrial.jpg"
    },
    {
        "name": "Case 2: Agricultural Stubble Burning",
        "desc": "Large field on fire after harvesting, thick orange flames and smoke spreading across bypass.",
        "image": "test_images/biomass_stubble.jpg"
    },
    {
        "name": "Case 3: Construction Dust Site",
        "desc": "Building demolition creating massive dust clouds without water sprinkling.",
        "image": "test_images/construction_dust.jpg"
    },
    {
        "name": "Case 4: Guardrail Test (Unrelated / Clean Image)",
        "desc": "Citizen reports severe emergency smoke, but image is a clean room.",
        "image": "test_images/unrelated_clean_room.jpg"
    },
    {
        "name": "Case 5: Text-Only (No Photo)",
        "desc": "Smell of burning rubber in Anand Vihar area.",
        "image": None
    }
]

def run_tests():
    print("=" * 65)
    print("VAYUNET GEMINI MULTIMODAL EVIDENCE EXTRACTION TEST SUITE")
    print("=" * 65)

    for tc in test_cases:
        print(f"\n--- {tc['name']} ---")
        print(f"Citizen text : {tc['desc']}")
        print(f"Image path   : {tc['image']}")
        
        result = extract_evidence(description=tc["desc"], image_path=tc["image"])
        gemini = result["gemini_output"]
        
        print("\nExtracted Evidence:")
        print(f"  • Event Type          : {gemini['event_type']}")
        print(f"  • Severity            : {gemini['severity']}")
        print(f"  • Confidence          : {gemini['confidence']}")
        print(f"  • Needs Human Review  : {gemini['needs_human_review']}")
        print(f"  • Summary Description : {gemini['description']}")

    print("\n" + "=" * 65)
    print("ALL TEST CASES EXECUTED.")
    print("=" * 65)

if __name__ == "__main__":
    run_tests()
