import os
import csv
import glob

output_csv = "vayu_dataset.csv"
nemo_dirs = [
    "data/Nemo/dataset/single-class/sc/val_images/val_images",
    "data/Nemo/dataset/single-class/sc/train_images/train_images"
]
test_img_dir = "test_images"

# [image_path, is_smoke, is_dust, is_fire, has_plume]
rows = []
header = ["image_path", "is_smoke", "is_dust", "is_fire", "has_plume"]

print("Processing NEMO (Smoke) dataset...")
for nemo_dir in nemo_dirs:
    if os.path.exists(nemo_dir):
        for filename in os.listdir(nemo_dir):
            if filename.endswith(".jpg") or filename.endswith(".png"):
                path = os.path.join(nemo_dir, filename)
                rows.append([path, 1, 0, 0, 1])

print("Processing local test images for generic examples...")
if os.path.exists(test_img_dir):
    for filename in os.listdir(test_img_dir):
        path = os.path.join(test_img_dir, filename)
        if "smoke" in filename:
            rows.append([path, 1, 0, 0, 1])
        elif "dust" in filename:
            rows.append([path, 0, 1, 0, 0])
        elif "burning" in filename or "biomass" in filename:
            rows.append([path, 1, 0, 1, 1])
        elif "clean" in filename:
            rows.append([path, 0, 0, 0, 0])
        else:
            rows.append([path, 0, 0, 0, 0])

print(f"Total images collected: {len(rows)}")

with open(output_csv, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(header)
    writer.writerows(rows)

print(f"Generated {output_csv}")
