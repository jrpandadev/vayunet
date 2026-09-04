import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

TEST_DIR = Path(__file__).resolve().parent / "test_images"
TEST_DIR.mkdir(parents=True, exist_ok=True)

def generate_test_images():
    print(f"Generating test images in {TEST_DIR}...")
    
    # 1. Industrial Smoke Image
    img_smoke = Image.new("RGB", (400, 300), color=(100, 100, 105))
    draw = ImageDraw.Draw(img_smoke)
    draw.rectangle([150, 120, 250, 300], fill=(60, 60, 65))
    draw.ellipse([80, 20, 320, 160], fill=(30, 30, 30))  # Dark thick smoke plume
    draw.text((10, 10), "SAMPLE TEST: Industrial Smokestack with Heavy Plume", fill=(255, 255, 255))
    img_smoke.save(TEST_DIR / "smoke_industrial.jpg")

    # 2. Stubble / Biomass Burning Image
    img_biomass = Image.new("RGB", (400, 300), color=(160, 120, 60))
    draw = ImageDraw.Draw(img_biomass)
    draw.rectangle([0, 200, 400, 300], fill=(40, 20, 10))  # Charred field
    draw.ellipse([50, 80, 350, 220], fill=(220, 100, 20))  # Fire flame & orange smoke
    draw.text((10, 10), "SAMPLE TEST: Agricultural Stubble Burning Field", fill=(255, 255, 255))
    img_biomass.save(TEST_DIR / "biomass_stubble.jpg")

    # 3. Construction Dust Image
    img_dust = Image.new("RGB", (400, 300), color=(190, 175, 140))
    draw = ImageDraw.Draw(img_dust)
    draw.rectangle([50, 100, 150, 300], fill=(130, 120, 100))  # Construction scaffolding
    draw.ellipse([100, 50, 380, 250], fill=(210, 195, 160))  # Tan dust haze
    draw.text((10, 10), "SAMPLE TEST: Construction Site Dust Cloud", fill=(0, 0, 0))
    img_dust.save(TEST_DIR / "construction_dust.jpg")

    # 4. Unrelated Non-Pollution Image (Clean indoor / pet test for guardrail testing)
    img_clean = Image.new("RGB", (400, 300), color=(240, 248, 255))
    draw = ImageDraw.Draw(img_clean)
    draw.rectangle([50, 50, 350, 250], fill=(135, 206, 235))  # Clear blue sky window
    draw.ellipse([180, 180, 220, 220], fill=(255, 165, 0))   # Cat toy ball
    draw.text((10, 10), "SAMPLE TEST: Clean Indoor Room (No Pollution)", fill=(50, 50, 50))
    img_clean.save(TEST_DIR / "unrelated_clean_room.jpg")

    print("All 4 labeled sample test images generated successfully.")

if __name__ == "__main__":
    generate_test_images()
