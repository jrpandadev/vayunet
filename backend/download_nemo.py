import urllib.request
import zipfile
import os

def download_and_extract(url, zip_path, extract_to):
    print(f"Downloading {zip_path}...")
    if not os.path.exists(zip_path):
        try:
            urllib.request.urlretrieve(url, zip_path)
            print("Download complete.")
            print("Extracting...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
            print("Extraction complete.")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print(f"Already downloaded {zip_path}.")

val_url = "https://nevada.box.com/shared/static/5yzf7ks1taz3667er8iq7kqe7ooh3x6w.zip"
train_url = "https://nevada.box.com/shared/static/bu87x2vm0cqbireftlpacoytbi6jc4k6.zip"

download_and_extract(val_url, "val_images.zip", "data/Nemo/dataset/single-class/sc/val_images")
download_and_extract(train_url, "train_images.zip", "data/Nemo/dataset/single-class/sc/train_images")
